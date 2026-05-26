"""
InvoiceService: determina tipo FA/FB, integra pyafipws (CAE/CAEA).
Factura siempre; electrónica cuando AFIP responde.
"""
import logging
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from self_checkout.db import mysql_cursor
from self_checkout.fe_config import get_fe_config, is_fe_configured, sanitize_for_log
from self_checkout.fe_sync import consultar_cae_comprobante
from self_checkout.services.padron_afip_service import consultar_condicion_fiscal
from self_checkout.services.empresa_fiscal_service import emisor_emite_solo_factura_c, emisor_es_responsable_inscripto

logger = logging.getLogger(__name__)

# AFIP: 3=0%, 4=10.5%, 5=21%, 6=27%
IVA_IDS = {0: 3, 10.5: 4, 21: 5, 27: 6}
# tipo_cbte AFIP: 1=FA, 6=FB, 11=FC (Factura C Monotributo/Exento)
TIPO_CBTE = {"FA": 1, "FB": 6, "FC": 11}
TIPO_DOC_CUIT = 80
TIPO_DOC_DNI = 96
# Consumidor final sin documento: DocTipo 99 (obligatorio si DocNro=0, error 10015)
TIPO_DOC_SIN_IDENTIFICAR = 99
# Condición IVA receptor (RG 5616, error 10246): 5 = Consumidor Final
CONDICION_IVA_CONSUMIDOR_FINAL = 5
CONDICION_IVA_RI = 1


class InvoiceService:
    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa

    def determinar_tipo_comprobante(self, id_cliente: int = 1, cuit: Optional[str] = None) -> str:
        """
        Determina FA, FB o FC según condición fiscal del emisor y del cliente (AFIP).
        - Si la empresa emisora es Monotributo/Exento (datosempresa.IDIva 2,3,4,6) → siempre FC.
        - Si la empresa es RI (1) o Sujeto no categorizado (7): según cliente → FA o FB.
        - Cliente consumidor final (sin CUIT válido) → FB. Con CUIT → padrón AFIP → FA si corresponde, sino FB.
        """
        if emisor_emite_solo_factura_c(self.base_empresa):
            return "FC"
        if not emisor_es_responsable_inscripto(self.base_empresa):
            return "FC"
        cuit_clean = (cuit or "").replace("-", "").replace(" ", "").strip()
        if id_cliente == 1 or len(cuit_clean) != 11 or not cuit_clean.isdigit():
            return "FB"
        tipo, _denom, err = consultar_condicion_fiscal(self.base_empresa, cuit_clean)
        if err:
            logger.warning("Padrón AFIP para FA/FB: %s → emitiendo FB", sanitize_for_log((err or {}).get("msg", "")))
            return "FB"
        return tipo if tipo in ("FA", "FB") else "FB"

    def _obtener_datos_factura(
        self,
        cart_id: int,
        codigo_movimiento: int,
        tipo_comprobante: str,
        nro_comprobante: str,
        id_punto_venta: int,
        total: Decimal,
        subtotal: Decimal,
        id_cliente: int = 1,
        cuit: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Arma el dict para pyafipws CrearFactura según tipo FA/FB/FC.
        Reglas AFIP: docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md
        - FC (tipo 11): ImpIVA=0, ImpTotal=ImpNeto+ImpTrib, no enviar IVA (10047, 10048, 10071).
        - Concepto 1: no enviar FchVtoPago (10049).
        """
        with mysql_cursor(self.base_empresa, dict_cursor=True) as c:
            c.execute(
                """
                SELECT id_articulo, cantidad, importe_total, importe_iva, alicuota_iva
                FROM self_checkout_cart_item WHERE cart_id = %s
                """,
                [cart_id],
            )
            items = c.fetchall()
        if not items:
            return None

        es_fc = tipo_comprobante == "FC"
        ivas: Dict[int, Dict] = {}
        imp_neto = Decimal("0")
        imp_iva = Decimal("0")
        for it in items:
            base = (it["importe_total"] or 0) - (it["importe_iva"] or 0)
            iva_val = it["importe_iva"] or 0
            imp_neto += Decimal(str(base))
            imp_iva += Decimal(str(iva_val))
            if not es_fc:
                alic = float(it.get("alicuota_iva") or 0)
                iva_id = IVA_IDS.get(alic, 5)
                if iva_id not in ivas:
                    ivas[iva_id] = {"iva_id": iva_id, "base_imp": 0, "importe": 0}
                ivas[iva_id]["base_imp"] += float(base)
                ivas[iva_id]["importe"] += float(iva_val)

        imp_trib = Decimal("0")
        if es_fc:
            # AFIP 10047, 10048, 10071: FC sin IVA; ImpTotal = ImpNeto + ImpTrib
            imp_iva = Decimal("0")
            imp_total = imp_neto + imp_trib
            imp_tot_conc = Decimal("0")
        else:
            imp_total = total
            imp_tot_conc = imp_total - imp_neto - imp_iva
            if imp_tot_conc < 0:
                imp_tot_conc = Decimal("0")

        nro_doc = "0"
        if cuit:
            nro_doc = str(cuit).replace("-", "").replace(" ", "")[:11]
        if not nro_doc or not nro_doc.isdigit():
            nro_doc = "0" if id_cliente == 1 else str(id_cliente)

        # AFIP 10015: si DocNro es 0, DocTipo debe ser 99 (sin identificar)
        if nro_doc == "0" or int(nro_doc or 0) == 0:
            tipo_doc = TIPO_DOC_SIN_IDENTIFICAR
            nro_doc = "0"
        elif len(nro_doc) == 11:
            tipo_doc = TIPO_DOC_CUIT
        else:
            tipo_doc = TIPO_DOC_DNI

        # Condición IVA receptor (RG 5616, error 10246): obligatorio. 5 = Consumidor Final.
        condicion_iva_receptor = (
            CONDICION_IVA_CONSUMIDOR_FINAL
            if (tipo_comprobante == "FB" or tipo_doc == TIPO_DOC_SIN_IDENTIFICAR)
            else CONDICION_IVA_RI
        )

        fecha = datetime.now().strftime("%Y%m%d")
        punto_vta = int(id_punto_venta)
        cbt_desde = int(nro_comprobante) if str(nro_comprobante).isdigit() else 1
        cbt_hasta = cbt_desde

        # AFIP 10049: FchVtoPago solo si Concepto 2 o 3; usamos Concepto 1 → no enviar
        datos = {
            "concepto": 1,
            "tipo_doc": tipo_doc,
            "nro_doc": nro_doc or "0",
            "tipo_cbte": TIPO_CBTE.get(tipo_comprobante, 6),
            "punto_vta": punto_vta,
            "cbt_desde": cbt_desde,
            "cbt_hasta": cbt_hasta,
            "imp_total": str(round(float(imp_total), 2)),
            "imp_tot_conc": str(round(float(imp_tot_conc), 2)),
            "imp_neto": str(round(float(imp_neto), 2)),
            "imp_iva": str(round(float(imp_iva), 2)),
            "imp_trib": str(round(float(imp_trib), 2)),
            "imp_op_ex": "0.00",
            "fecha_cbte": fecha,
            "fecha_venc_pago": None,
            "moneda_id": "PES",
            "moneda_ctz": "1.0000",
            "cbtes_asoc": [],
            "tributos": [],
            "iva": [] if es_fc else list(ivas.values()),
            "opcionales": [],
        }
        # RG 5616 (error 10246): Condición IVA receptor obligatoria.
        # pyafipws wsfev1.CrearFactura() espera exactamente condicion_iva_receptor_id (snake_case);
        # se serializa al SOAP como CondicionIVAReceptorId (reingart/pyafipws wsfev1.py).
        if condicion_iva_receptor is not None:
            datos["condicion_iva_receptor_id"] = condicion_iva_receptor
        return datos

    def emitir_fe(
        self,
        cart_id: int,
        id_cuentacliente: int,
        codigo_movimiento: int,
        tipo_comprobante: str,
        nro_comprobante: str,
        id_punto_venta: int,
        total: Decimal,
        subtotal: Decimal,
        id_cliente: int = 1,
        cuit: Optional[str] = None,
    ) -> Tuple[str, Optional[str], Optional[str], Optional[dict]]:
        """
        Intenta CAE. Si AFIP falla → CAEA pending.
        Returns: (estado, cae, vto_cae, error_detail)
        Estados: issued_cae | issued_caea_pending | failed
        """
        if not is_fe_configured(self.base_empresa):
            logger.warning("FE no configurado (cert/key/cuit). Marcando failed.")
            return "failed", None, None, {"msg": "AFIP no configurado"}

        datos = self._obtener_datos_factura(
            cart_id, codigo_movimiento, tipo_comprobante, nro_comprobante,
            id_punto_venta, total, subtotal, id_cliente, cuit,
        )
        if not datos:
            return "failed", None, None, {"msg": "Sin items para FE"}

        cfg = get_fe_config(self.base_empresa)
        from self_checkout.fe_config import validate_fe_certificates_readable

        ok_read, err_read = validate_fe_certificates_readable(cfg)
        if not ok_read:
            logger.warning("FE: certificado/clave no legible: %s", sanitize_for_log(err_read))
            return "failed", None, None, {"msg": err_read}
        try:
            from pyafipws.wsaa import WSAA
            from pyafipws.wsfev1 import WSFEv1
        except ImportError as e:
            logger.warning("pyafipws no disponible: %s", sanitize_for_log(str(e)))
            return "failed", None, None, {"msg": "pyafipws no instalado"}

        wsaa = WSAA()
        wsfev1 = WSFEv1()
        wsfev1.LanzarExcepciones = False

        try:
            ta = wsaa.Autenticar(
                "wsfe",
                cfg["cert"],
                cfg["key"],
                wsdl=cfg["wsaa_url"],
                cache=cfg["cache_dir"],
                debug=False,
            )
            if not ta:
                err = getattr(wsaa, "Excepcion", "WSAA error")
                logger.warning("FE WSAA falló: %s", sanitize_for_log(str(err)))
                return "failed", None, None, {"msg": str(err)}

            wsfev1.Cuit = cfg["cuit"]
            wsfev1.SetTicketAcceso(ta)
            ok = wsfev1.Conectar(cfg["cache_dir"], cfg["wsfe_url"])
            if not ok:
                return "failed", None, None, {"msg": "Conectar WSFEv1 falló"}

            wsfev1.CrearFactura(**datos)
            for iva in datos.get("iva", []):
                wsfev1.AgregarIva(**iva)

            wsfev1.CAESolicitar()

            if wsfev1.Resultado == "A" and wsfev1.CAE:
                return "issued_cae", str(wsfev1.CAE), str(wsfev1.Vencimiento or ""), None

            err_msg = wsfev1.ErrMsg or wsfev1.Obs or "AFIP rechazó"
            if _es_error_red(wsfev1):
                # Recuperar CAE por si ARCA autorizó pero la respuesta se perdió (corte de conexión).
                nro_int = int(nro_comprobante) if str(nro_comprobante).strip().isdigit() else None
                if nro_int is not None:
                    cae_rec, vto_rec, _ = consultar_cae_comprobante(
                        self.base_empresa, id_punto_venta, tipo_comprobante, nro_int
                    )
                    if cae_rec:
                        logger.info("CAE recuperado por FECompConsultar tras error de red: nro=%s", nro_comprobante)
                        return "issued_cae", cae_rec, vto_rec or "", None
                estado_caea, caea_val, vto, err_caea = self._intentar_caea(wsfev1, cfg, datos)
                if caea_val:
                    return estado_caea, str(caea_val), vto, err_caea

            return "failed", None, None, {"msg": sanitize_for_log(err_msg)}
        except Exception as e:
            logger.exception("FE exception")
            # Posible corte tras enviar CAESolicitar: intentar recuperar CAE por FECompConsultar.
            try:
                nro_int = int(nro_comprobante) if str(nro_comprobante).strip().isdigit() else None
                if nro_int is not None:
                    cae_rec, vto_rec, _ = consultar_cae_comprobante(
                        self.base_empresa, id_punto_venta, tipo_comprobante, nro_int
                    )
                    if cae_rec:
                        logger.info("CAE recuperado por FECompConsultar tras excepción: nro=%s", nro_comprobante)
                        return "issued_cae", cae_rec, vto_rec or "", None
            except Exception:
                pass
            return "failed", None, None, {"msg": sanitize_for_log(str(e))}

    def _intentar_caea(
        self, wsfev1, cfg: dict, datos: dict
    ) -> Tuple[str, Optional[str], Optional[str], Optional[dict]]:
        """
        Usa CAEA almacenado (renovación automática) o solicita a AFIP. Informa comprobante.
        Si informa OK → sent. Si falla informar → issued_caea_pending (reintento posterior).
        """
        caea = None
        try:
            hoy = datetime.now()
            periodo = hoy.strftime("%Y%m")
            orden = 1 if hoy.day <= 15 else 2  # quincena 1 = 1-15, quincena 2 = 16-fin
            # Preferir CAEA obtenido por renovación automática (request_caea_auto)
            try:
                from fe_afip.services.caea_service import get_caea_stored
                caea = get_caea_stored(self.base_empresa, periodo, orden)
            except Exception:
                caea = None
            if not caea:
                caea = wsfev1.CAEAConsultar(periodo, orden)
            if not caea:
                caea = wsfev1.CAEASolicitar(periodo, orden)
            if not caea:
                return "failed", None, None, {"msg": "No se pudo obtener CAEA"}

            datos["caea"] = str(caea)
            wsfev1.CrearFactura(**datos)
            for iva in datos.get("iva", []):
                wsfev1.AgregarIva(**iva)

            wsfev1.CAEARegInformativo()
            if wsfev1.Resultado == "A" or getattr(wsfev1, "CAEA", None):
                return "sent", str(caea), None, None
            return "issued_caea_pending", str(caea), None, {"msg": wsfev1.ErrMsg or "CAEARegInformativo falló"}
        except Exception as e:
            return "issued_caea_pending", str(caea) if caea else None, None, {"msg": sanitize_for_log(str(e))}

    def guardar_invoice(
        self,
        cart_id: int,
        codigo_movimiento: int,
        id_cuentacliente: int,
        nro_comprobante: str,
        tipo_comprobante: str,
        estado: str = "pendiente",
        cae: Optional[str] = None,
        vto_cae: Optional[str] = None,
        fe_regimen: Optional[str] = None,
        error_msg: Optional[str] = None,
        request_payload: Optional[str] = None,
        response_payload: Optional[str] = None,
    ) -> Optional[int]:
        """Guarda registro en self_checkout_invoice."""
        with mysql_cursor(self.base_empresa) as cursor:
            cursor.execute(
                """
                INSERT INTO self_checkout_invoice
                (cart_id, codigo_movimiento, id_cuentacliente, nro_comprobante, tipo_comprobante,
                 estado, cae, vto_cae, fe_regimen, error_msg, request_payload, response_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    cart_id, codigo_movimiento, id_cuentacliente, nro_comprobante, tipo_comprobante,
                    estado, cae, vto_cae, fe_regimen, error_msg, request_payload, response_payload,
                ],
            )
            return cursor.lastrowid

    def actualizar_invoice(
        self,
        invoice_id: int,
        estado: str,
        cae: Optional[str] = None,
        vto_cae: Optional[str] = None,
        fe_regimen: Optional[str] = None,
        error_msg: Optional[str] = None,
    ) -> bool:
        """Actualiza estado de invoice tras intento FE."""
        with mysql_cursor(self.base_empresa) as cursor:
            cursor.execute(
                """
                UPDATE self_checkout_invoice SET
                    estado = %s, cae = COALESCE(%s, cae), vto_cae = COALESCE(%s, vto_cae),
                    fe_regimen = COALESCE(%s, fe_regimen), error_msg = %s, updated_at = NOW()
                WHERE id = %s
                """,
                [estado, cae, vto_cae, fe_regimen, error_msg, invoice_id],
            )
            return cursor.rowcount > 0

    def actualizar_cuentacliente_fe(
        self,
        id_cuentacliente: int,
        estado_fe: str,
        cae: Optional[str] = None,
        vto_cae: Optional[str] = None,
        fe_regimen: Optional[str] = None,
    ) -> bool:
        """
        Actualiza cuentacliente con CAE/CAEA y flags FE (mismo proceso que administraNET).
        Solo actualiza cuando hay CAE o CAEA (issued_cae, sent, issued_caea_pending).
        fe_comp = 'Si' si tenemos CAE/CAEA; fe_transmitido = 'Si' solo si issued_cae o sent.
        """
        if estado_fe not in ("issued_cae", "sent", "issued_caea_pending"):
            return False
        fe_comp = "Si"  # tenemos comprobante electrónico (CAE o CAEA)
        fe_transmitido = "Si" if estado_fe in ("issued_cae", "sent") else "No"  # CAEA pendiente = aún no informado
        vto_sql = vto_cae if vto_cae else None
        try:
            with mysql_cursor(self.base_empresa) as cursor:
                cursor.execute(
                    """
                    UPDATE cuentacliente SET
                        fe_cae = COALESCE(%s, fe_cae),
                        fe_vto_cae = COALESCE(%s, fe_vto_cae),
                        fe_comp = %s,
                        fe_transmitido = %s,
                        fe_regimen_tipo = COALESCE(%s, fe_regimen_tipo)
                    WHERE id_cuentacliente = %s
                    """,
                    [cae, vto_sql, fe_comp, fe_transmitido, fe_regimen, id_cuentacliente],
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.warning("actualizar_cuentacliente_fe: %s (id_cc=%s)", e, id_cuentacliente)
            return False


def _es_error_red(wsfev1) -> bool:
    """Detecta si el error fue de red/AFIP caído vs rechazo de datos."""
    err = (wsfev1.ErrMsg or "").lower()
    excep = (getattr(wsfev1, "Excepcion", "") or "").lower()
    red = any(x in err + excep for x in ("timeout", "connection", "network", "socket", "error 5"))
    return red or wsfev1.Resultado not in ("A", "R")
