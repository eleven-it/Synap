"""Armado previo de cajas de una preparación VB6, sin afectar stock ni remitos."""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from uuid import UUID

import MySQLdb.cursors

from core.mysql_pool import get_connection, mysql_cursor


class PreparacionError(ValueError):
    """Dato o transición inválida que puede mostrarse al operador."""


PENDIENTE = """(CASE
    WHEN IFNULL(sp.cantidad_pendiente,0) > 0 THEN sp.cantidad_pendiente
    WHEN UCASE(TRIM(IFNULL(sp.remitido_facturado,''))) <> 'SI' THEN IFNULL(sp.Cantidad,0)
    ELSE 0 END)"""

LINEAS_SQL = f"""
SELECT cp.CodigoMovimiento AS pedido, cp.NroComprobante AS nro_pedido,
       cp.Codigo AS id_cliente, IFNULL(c.nombre_cliente,'') AS cliente,
       cda.id_cliente_domicilio,
       IFNULL(cd.Calle,IFNULL(cda.Fentrega,'')) AS destino,
       sp.id_stock, sp.IDArt AS id_articulo, {PENDIENTE} AS pendiente,
       IFNULL(a.NombreArticulo,'') AS articulo,
       IFNULL(a.id_manual,'') AS codigo_manual,
       IFNULL(a.NroCodBarra,'') AS barra_interna,
       IFNULL(a.NroCodBarraF,'') AS barra_fabrica,
       IFNULL(a.nro_cod_barra_display,'') AS barra_display,
       IFNULL(a.nro_cod_barra_bulto,'') AS barra_bulto,
       IFNULL(a.lote,'No') AS lote, IFNULL(a.serie,'No') AS serie,
       IFNULL((SELECT MAX(NULLIF(ap.cantidad_unidad_display,0))
               FROM articulo_prov ap WHERE ap.IDArt=a.IDArt
                 AND IFNULL(ap.anulado,'No')='No'),1) AS unidades_display,
       IFNULL((SELECT MAX(NULLIF(ap.cantidad_display_bulto,0))
               FROM articulo_prov ap WHERE ap.IDArt=a.IDArt
                 AND IFNULL(ap.anulado,'No')='No'),1) AS displays_bulto
FROM ped_prep p
JOIN comp_ped cp ON cp.CodigoMovimiento = p.ped_numeracion
JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
JOIN articulo a ON a.IDArt = sp.IDArt
LEFT JOIN cliente c ON c.Codigo = cp.Codigo
LEFT JOIN cliente_datos_adicionales cda ON cda.id_datos_adicionales = (
  SELECT MAX(x.id_datos_adicionales) FROM cliente_datos_adicionales x
  WHERE x.CodigoMovimiento = cp.CodigoMovimiento
    AND IFNULL(x.id_cliente,0) = IFNULL(cp.Codigo,0))
LEFT JOIN cliente_domicilio cd ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
  AND IFNULL(cd.anulado,'No') = 'No'
WHERE p.CodigoMovimiento_prep = %s
  AND IFNULL(p.Anulado,'No') = 'No'
  AND IFNULL(cp.Anulado,'No') = 'No'
  AND IFNULL(sp.Anulado,'No') = 'No'
  AND cp.Estado IN ('Pendiente','En preparacion','En preparación',
                    'Preparado','Parcial','Facturado')
  AND {PENDIENTE} > 0
ORDER BY c.nombre_cliente, destino, cp.NroComprobante, a.NombreArticulo, sp.id_stock
"""

CODIGOS_DE_LA_PREPARACION_SQL = f"""
SELECT sp.IDArt AS id_articulo, IFNULL(a.id_manual,'') AS codigo_manual,
       IFNULL(a.NroCodBarra,'') AS barra_interna,
       IFNULL(a.NroCodBarraF,'') AS barra_fabrica,
       IFNULL(a.nro_cod_barra_display,'') AS barra_display,
       IFNULL(a.nro_cod_barra_bulto,'') AS barra_bulto,
       {PENDIENTE} AS pendiente,
       UCASE(TRIM(IFNULL(sp.remitido_facturado,''))) AS remitido_facturado
FROM ped_prep p
JOIN comp_ped cp ON cp.CodigoMovimiento = p.ped_numeracion
JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
JOIN articulo a ON a.IDArt = sp.IDArt
WHERE p.CodigoMovimiento_prep = %s
  AND IFNULL(p.Anulado,'No') = 'No'
  AND IFNULL(cp.Anulado,'No') = 'No'
  AND IFNULL(sp.Anulado,'No') = 'No'
  AND cp.Estado IN ('Pendiente','En preparacion','En preparación',
                    'Preparado','Parcial','Facturado')
"""


def _num(value) -> int:
    return int(Decimal(str(value or 0)))


def _dec(value) -> Decimal:
    return Decimal(str(value or 0))


def _compatible(caja, linea) -> bool:
    """Mismo criterio de CajaCompatibleConItemPrep en VB6."""
    if _num(caja.get("codigo_movimiento_ped_origen")) == _num(linea.get("pedido")):
        return True
    if _num(caja["id_cliente"]) != _num(linea["id_cliente"]):
        return False
    caja_id = _num(caja.get("id_cliente_domicilio"))
    linea_id = _num(linea.get("id_cliente_domicilio"))
    if caja_id and linea_id:
        return caja_id == linea_id
    caja_texto = " ".join(str(caja.get("destino_entrega") or "").upper().split())
    linea_texto = " ".join(str(linea.get("destino") or "").upper().split())
    return bool(caja_texto) and caja_texto == linea_texto


@contextmanager
def _tx(base_empresa):
    with get_connection(base_empresa) as conn:
        conn.begin()
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def _lineas(cursor, codigo_prep):
    cursor.execute(LINEAS_SQL, [codigo_prep])
    return cursor.fetchall()


def _cajas(cursor, codigo_prep):
    cursor.execute(
        """SELECT c.*, (SELECT COUNT(*) FROM synap_prep_caja_lectura l
            WHERE l.id_caja=c.id_caja AND l.anulada=0) AS lecturas_activas,
            (SELECT COUNT(*) FROM synap_prep_caja_lectura l
            WHERE l.id_caja=c.id_caja) AS lecturas_totales
           FROM synap_prep_caja c WHERE c.codigo_movimiento_prep=%s
           ORDER BY c.numero_caja""",
        [codigo_prep],
    )
    return cursor.fetchall()


def _contenido_cajas(cursor, codigo_prep):
    cursor.execute(
        """SELECT l.id_caja, l.id_articulo, l.codigo_movimiento_ped,
                  l.codigo_leido, l.tipo_lectura,
                  MAX(IFNULL(a.NombreArticulo,'')) AS articulo,
                  MAX(IFNULL(cp.NroComprobante,'')) AS nro_pedido,
                  SUM(l.cantidad_unidades) AS cantidad_unidades,
                  COUNT(*) AS lecturas
           FROM synap_prep_caja_lectura l
           JOIN synap_prep_caja c ON c.id_caja=l.id_caja
           LEFT JOIN articulo a ON a.IDArt=l.id_articulo
           LEFT JOIN comp_ped cp ON cp.CodigoMovimiento=l.codigo_movimiento_ped
           WHERE c.codigo_movimiento_prep=%s AND l.anulada=0
           GROUP BY l.id_caja,l.id_articulo,l.codigo_movimiento_ped,
                    l.codigo_leido,l.tipo_lectura
           ORDER BY l.id_caja,articulo,l.codigo_leido""",
        [codigo_prep],
    )
    return cursor.fetchall()


def _lecturas(cursor, codigo_prep):
    cursor.execute(
        """SELECT l.*, c.numero_caja FROM synap_prep_caja_lectura l
        JOIN synap_prep_caja c ON c.id_caja=l.id_caja
        WHERE c.codigo_movimiento_prep=%s AND l.anulada=0
        ORDER BY l.id_lectura DESC LIMIT 30""",
        [codigo_prep],
    )
    return cursor.fetchall()


def _consumos(cursor, codigo_prep):
    cursor.execute(
        """SELECT l.codigo_movimiento_ped, l.id_articulo,
                  SUM(l.cantidad_unidades) AS cantidad
           FROM synap_prep_caja_lectura l
           JOIN synap_prep_caja c ON c.id_caja=l.id_caja
           WHERE c.codigo_movimiento_prep=%s AND c.estado IN ('Abierta','Cerrada')
             AND l.anulada=0
           GROUP BY l.codigo_movimiento_ped,l.id_articulo""",
        [codigo_prep],
    )
    return {(_num(r["codigo_movimiento_ped"]), _num(r["id_articulo"])):
            _dec(r["cantidad"]) for r in cursor.fetchall()}


def listar_preparaciones(base_empresa, termino=""):
    termino = str(termino or "").strip()[:60]
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute(
            """SELECT p.CodigoMovimiento_prep AS codigo, MAX(p.NroComprobante) AS numero,
                      MAX(p.fecha) AS fecha, COUNT(DISTINCT p.ped_numeracion) AS pedidos
               FROM ped_prep p JOIN comp_ped cp ON cp.CodigoMovimiento=p.ped_numeracion
               WHERE IFNULL(p.Anulado,'No')='No' AND IFNULL(cp.Anulado,'No')='No'
                 AND (%s='' OR CAST(p.CodigoMovimiento_prep AS CHAR) LIKE %s
                      OR p.NroComprobante LIKE %s)
               GROUP BY p.CodigoMovimiento_prep
               ORDER BY MAX(p.fecha) DESC, p.CodigoMovimiento_prep DESC LIMIT 60""",
            [termino, f"%{termino}%", f"%{termino}%"],
        )
        return cursor.fetchall()


def estado_preparacion(base_empresa, codigo_prep):
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        lineas = _lineas(cursor, codigo_prep)
        cajas = _cajas(cursor, codigo_prep)
        contenido = _contenido_cajas(cursor, codigo_prep)
        lecturas = _lecturas(cursor, codigo_prep)
        consumido = _consumos(cursor, codigo_prep)
    por_caja = {}
    for item in contenido:
        por_caja.setdefault(_num(item["id_caja"]), []).append(item)
    for caja in cajas:
        caja["contenido"] = por_caja.get(_num(caja["id_caja"]), [])
    agrupadas = {}
    for linea in lineas:
        clave = (_num(linea["pedido"]), _num(linea["id_articulo"]))
        if clave not in agrupadas:
            agrupadas[clave] = dict(linea)
            agrupadas[clave]["pendiente"] = Decimal(0)
        agrupadas[clave]["pendiente"] += _dec(linea["pendiente"])
    articulos = []
    for clave, linea in agrupadas.items():
        linea["en_cajas"] = consumido.get(clave, Decimal(0))
        linea["faltante"] = max(Decimal(0), linea["pendiente"] - linea["en_cajas"])
        articulos.append(linea)
    return {"codigo": codigo_prep, "articulos": articulos, "cajas": cajas, "lecturas": lecturas}


def _bloquear_preparacion(cursor, codigo_prep):
    cursor.execute(
        "INSERT IGNORE INTO synap_prep_caja_secuencia (codigo_movimiento_prep) VALUES (%s)",
        [codigo_prep],
    )
    cursor.execute(
        "SELECT proximo_numero FROM synap_prep_caja_secuencia "
        "WHERE codigo_movimiento_prep=%s FOR UPDATE",
        [codigo_prep],
    )
    return cursor.fetchone()["proximo_numero"]


def abrir_caja(base_empresa, codigo_prep, pedido, id_usuario):
    with _tx(base_empresa) as cursor:
        numero = _bloquear_preparacion(cursor, codigo_prep)
        lineas = _lineas(cursor, codigo_prep)
        origen = next((r for r in lineas if _num(r["pedido"]) == pedido), None)
        if origen is None:
            raise PreparacionError("El pedido no tiene artículos pendientes en esta preparación.")
        cursor.execute(
            """INSERT INTO synap_prep_caja
               (codigo_movimiento_prep,numero_caja,codigo_movimiento_ped_origen,
                id_cliente,id_cliente_domicilio,destino_entrega,estado,id_usuario_apertura)
               VALUES (%s,%s,%s,%s,%s,%s,'Abierta',%s)""",
            [codigo_prep, numero, pedido, _num(origen["id_cliente"]),
             _num(origen.get("id_cliente_domicilio")) or None,
             origen.get("destino") or "", id_usuario],
        )
        id_caja = cursor.lastrowid
        cursor.execute(
            "UPDATE synap_prep_caja_secuencia SET proximo_numero=%s "
            "WHERE codigo_movimiento_prep=%s", [numero + 1, codigo_prep],
        )
        return {"id_caja": id_caja, "numero_caja": numero}


def _cantidad_codigo(codigo, articulo, modo_lectura="unidad"):
    codigo = str(codigo).strip()
    if codigo.startswith("333"):
        if len(codigo) < 12 or not codigo[3:12].isdigit():
            raise PreparacionError("Código 333 inválido.")
        if _num(articulo["id_articulo"]) != int(codigo[3:8]):
            return None
        cantidad = Decimal(int(codigo[8:12]))
        tipo = "Etiqueta 333"
    else:
        if codigo in {str(_num(articulo["id_articulo"])),
                      str(articulo["codigo_manual"] or "").strip(),
                      str(articulo["barra_interna"] or "").strip(),
                      str(articulo["barra_fabrica"] or "").strip()}:
            clase = "Unidad"
        elif codigo == str(articulo["barra_display"] or "").strip():
            clase = "Display"
        elif codigo == str(articulo["barra_bulto"] or "").strip():
            clase = "Bulto"
        else:
            return None
        cantidad = Decimal(1)
        tipo = "Unidad"
        if clase == "Display":
            cantidad = _dec(articulo["unidades_display"]) or Decimal(1)
            tipo = "Display"
        elif clase == "Bulto":
            cantidad = (_dec(articulo["unidades_display"]) or Decimal(1)) * (
                _dec(articulo["displays_bulto"]) or Decimal(1))
            tipo = "Bulto"
        elif modo_lectura == "display" and str(articulo["lote"]).upper() != "SI" \
                and str(articulo["serie"]).upper() != "SI":
            cantidad = _dec(articulo["unidades_display"]) or Decimal(1)
            tipo = "Display por modo"
    if cantidad <= 0:
        raise PreparacionError("La cantidad leída debe ser mayor que cero.")
    if str(articulo["lote"]).upper() == "SI" or str(articulo["serie"]).upper() == "SI":
        if tipo != "Unidad":
            raise PreparacionError("Este artículo con lote o serie debe leerse por unidad.")
    return cantidad, tipo


def _coincide_codigo(codigo, articulo):
    if codigo.startswith("333"):
        return len(codigo) >= 12 and codigo[3:12].isdigit() and int(codigo[3:8]) == _num(articulo["id_articulo"])
    return codigo == str(_num(articulo["id_articulo"])) or any(
        codigo == str(articulo[k] or "").strip() for k in (
            "codigo_manual", "barra_interna", "barra_fabrica",
            "barra_display", "barra_bulto",
        ) if str(articulo[k] or "").strip()
    )


def _motivo_codigo_sin_pendiente(cursor, codigo_prep, codigo):
    """Distingue una línea ya remitida de un código ajeno a la preparación."""
    cursor.execute(CODIGOS_DE_LA_PREPARACION_SQL, [codigo_prep])
    lineas = [r for r in cursor.fetchall() if _coincide_codigo(codigo, r)]
    if not lineas:
        return None
    if all(_dec(r["pendiente"]) <= 0 for r in lineas):
        if all(r["remitido_facturado"] == "SI" for r in lineas):
            return ("El artículo pertenece a esta preparación, pero ya figura "
                    "remitido/facturado y no tiene unidades pendientes.")
        return "El artículo pertenece a esta preparación, pero no tiene unidades pendientes."
    return "El artículo pertenece a esta preparación, pero no está disponible para controlar."


def registrar_lectura(base_empresa, codigo_prep, id_caja, codigo, key, id_usuario,
                     modo_lectura="unidad"):
    codigo = str(codigo or "").strip()
    modo_lectura = str(modo_lectura or "").strip().lower()
    if modo_lectura not in ("unidad", "display"):
        raise PreparacionError("Elegí un modo de lectura válido: Unidad o Display.")
    if not codigo or len(codigo) > 128:
        raise PreparacionError("Escaneá un código de artículo válido.")
    if codigo.startswith("333") and (len(codigo) < 12 or not codigo[3:12].isdigit()):
        raise PreparacionError("Código 333 inválido.")
    try:
        key = str(UUID(str(key)))
    except (ValueError, AttributeError):
        raise PreparacionError("Identificador de lectura inválido.") from None
    with _tx(base_empresa) as cursor:
        _bloquear_preparacion(cursor, codigo_prep)
        cursor.execute(
            "SELECT * FROM synap_prep_caja_lectura WHERE idempotency_key=%s", [key]
        )
        previa = cursor.fetchone()
        if previa:
            if _num(previa["id_caja"]) != id_caja or previa["codigo_leido"] != codigo:
                raise PreparacionError("Esta lectura ya se utilizó para otra caja o código.")
            return {"id_lectura": previa["id_lectura"], "repetida": True}
        cursor.execute(
            "SELECT * FROM synap_prep_caja WHERE id_caja=%s "
            "AND codigo_movimiento_prep=%s FOR UPDATE", [id_caja, codigo_prep]
        )
        caja = cursor.fetchone()
        if not caja or caja["estado"] != "Abierta":
            raise PreparacionError("La caja no está abierta.")
        lineas = _lineas(cursor, codigo_prep)
        consumido = _consumos(cursor, codigo_prep)
        agrupadas = {}
        for linea in lineas:
            clave = (_num(linea["pedido"]), _num(linea["id_articulo"]))
            agrupadas.setdefault(clave, []).append(linea)
        coincidencias = [(clave, filas) for clave, filas in agrupadas.items()
                         if _coincide_codigo(codigo, filas[0])]
        compatibles = [(clave, filas) for clave, filas in coincidencias
                       if _compatible(caja, filas[0])]
        if not coincidencias:
            motivo = _motivo_codigo_sin_pendiente(cursor, codigo_prep, codigo)
            raise PreparacionError(motivo or "El producto no pertenece a la preparación.")
        if not compatibles:
            raise PreparacionError("El producto corresponde a otra sucursal o cliente.")
        if len({clave[1] for clave, _ in compatibles}) > 1:
            raise PreparacionError("El código identifica varios artículos. Corregí el código de barras.")
        for pedido_articulo, filas in compatibles:
            referencia = filas[0]
            lectura = _cantidad_codigo(codigo, referencia, modo_lectura)
            if lectura is None:
                continue
            cantidad, tipo = lectura
            pendiente = sum((_dec(r["pendiente"]) for r in filas), Decimal(0))
            if cantidad > pendiente - consumido.get(pedido_articulo, Decimal(0)):
                continue
            cursor.execute(
                """INSERT INTO synap_prep_caja_lectura
                   (id_caja,codigo_movimiento_ped,id_articulo,id_stock_pedido,
                    codigo_leido,tipo_lectura,cantidad_unidades,idempotency_key,id_usuario)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                [id_caja, pedido_articulo[0], pedido_articulo[1],
                 _num(referencia["id_stock"]), codigo, tipo, cantidad, key, id_usuario],
            )
            return {"id_lectura": cursor.lastrowid, "repetida": False,
                    "articulo": referencia["articulo"], "pedido": referencia["nro_pedido"],
                    "cantidad": cantidad}
        raise PreparacionError("La lectura supera la cantidad pendiente del pedido.")


def cambiar_caja(base_empresa, codigo_prep, id_caja, accion, id_usuario, id_lectura=None):
    with _tx(base_empresa) as cursor:
        _bloquear_preparacion(cursor, codigo_prep)
        cursor.execute(
            "SELECT * FROM synap_prep_caja WHERE id_caja=%s "
            "AND codigo_movimiento_prep=%s FOR UPDATE", [id_caja, codigo_prep]
        )
        caja = cursor.fetchone()
        if not caja:
            raise PreparacionError("La caja no pertenece a esta preparación.")
        if accion == "cerrar":
            if caja["estado"] != "Abierta":
                raise PreparacionError("La caja no está abierta.")
            cursor.execute(
                "UPDATE synap_prep_caja SET estado='Cerrada', "
                "id_usuario_cierre=%s, fecha_cierre=NOW() WHERE id_caja=%s",
                [id_usuario, id_caja],
            )
        elif accion == "reabrir":
            if caja["estado"] != "Cerrada" or caja["fecha_importacion"]:
                raise PreparacionError("La caja no puede reabrirse después de importarse.")
            cursor.execute(
                "UPDATE synap_prep_caja SET estado='Abierta', "
                "id_usuario_cierre=NULL, fecha_cierre=NULL WHERE id_caja=%s", [id_caja]
            )
        elif accion == "eliminar":
            if caja["estado"] not in ("Abierta", "Cerrada") or caja["fecha_importacion"]:
                raise PreparacionError("La caja importada no puede eliminarse.")
            cursor.execute(
                "SELECT COUNT(*) AS n FROM synap_prep_caja_lectura WHERE id_caja=%s",
                [id_caja],
            )
            if cursor.fetchone()["n"]:
                raise PreparacionError(
                    "La caja tiene lecturas en su historial, incluso si fueron anuladas. "
                    "Conservala para mantener la trazabilidad."
                )
            cursor.execute("DELETE FROM synap_prep_caja WHERE id_caja=%s", [id_caja])
        elif accion == "anular_lectura":
            if caja["estado"] != "Abierta":
                raise PreparacionError("Reabrí la caja antes de corregir lecturas.")
            cursor.execute(
                """UPDATE synap_prep_caja_lectura SET anulada=1,
                   id_usuario_anulacion=%s,fecha_anulacion=NOW()
                   WHERE id_lectura=%s AND id_caja=%s AND anulada=0""",
                [id_usuario, id_lectura, id_caja],
            )
            if cursor.rowcount != 1:
                raise PreparacionError("La lectura ya no está disponible.")
        else:
            raise PreparacionError("Acción desconocida.")
        return {"ok": True}
