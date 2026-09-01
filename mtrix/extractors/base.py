"""Configuración de exportación y helpers SQL."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Sequence

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import str_or_default, to_int_or_none


@dataclass
class ExportConfig:
    base_empresa: str
    fecha_desde: str  # YYYY-MM-DD
    fecha_hasta: str
    proveedores: list[str]  # ["TODOS"] o códigos
    cnpj_fornecedor: str
    cnpj_distribuidor: str = ""
    razon_social_fornecedor: str = "DISTRIBUIDOR"
    pvnf: bool = False  # True = todos los PV (pvnf Si)
    multiplicador_cantidad: int = 1
    multiplicador_precio: int = 1
    fecha_archivo: str = ""  # YYYYMMDD

    def to_serializer_cfg(self) -> dict:
        return {
            "cnpj_fornecedor": self.cnpj_fornecedor,
            "cnpj_distribuidor": self.cnpj_distribuidor,
            "razon_social_fornecedor": self.razon_social_fornecedor,
            "fecha_archivo": self.fecha_archivo,
            "multiplicador_cantidad": self.multiplicador_cantidad,
            "multiplicador_precio": self.multiplicador_precio,
        }


def parse_proveedores(texto: str) -> list[str]:
    limpio = (texto or "").strip()
    if not limpio:
        return ["TODOS"]
    return [p.strip() for p in limpio.split(",") if p.strip()] or ["TODOS"]


def normalizar_codigos_prov(
    *,
    codigo_prov: str | None = None,
    codigos_prov: list[str] | None = None,
) -> list[str]:
    """Lista de códigos o ['TODOS']. `codigos_prov` gana si viene informada."""
    if codigos_prov:
        limpios = [str(c).strip() for c in codigos_prov if str(c).strip()]
        if limpios:
            return limpios
    if codigo_prov and str(codigo_prov).strip():
        return [str(codigo_prov).strip()]
    return ["TODOS"]


def sql_filtro_proveedor(codigos: list[str], *, alias: str = "articulo") -> tuple[str, list]:
    """Fragmento `alias.CodigoProveedor IN (...)` o vacío si es TODOS."""
    if not codigos or (len(codigos) == 1 and codigos[0] == "TODOS"):
        return "", []
    ints: list[int] = []
    for codigo in codigos:
        if codigo == "TODOS":
            continue
        numero = to_int_or_none(codigo)
        if numero is not None:
            ints.append(numero)
    if not ints:
        return "", []
    placeholders = ", ".join(["%s"] * len(ints))
    return f"{alias}.CodigoProveedor IN ({placeholders})", ints


def _fecha_iso(valor) -> str:
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor or "")[:10]


def calcular_rango_exportacion(
    *,
    hoy: str,
    last_vd_enviado_hasta=None,
    dias: int = 5,
    usar_personalizada: bool = False,
    fecha_inicio=None,
    fecha_final=None,
) -> tuple[str, str]:
    """Rango YYYY-MM-DD. Marca de agua con solape de 1 día; personalizada solo manual."""
    if usar_personalizada and fecha_inicio and fecha_final:
        return _fecha_iso(fecha_inicio), _fecha_iso(fecha_final)
    hoy_s = _fecha_iso(hoy)
    if last_vd_enviado_hasta:
        desde = _fecha_iso(last_vd_enviado_hasta)
        if desde > hoy_s:
            desde = hoy_s
        return desde, hoy_s
    dias_n = max(int(dias or 5), 1)
    inicio = date.fromisoformat(hoy_s) - timedelta(days=dias_n)
    return inicio.isoformat(), hoy_s


def resolver_fechas_mysql(
    base_empresa: str,
    *,
    personalizada: bool,
    fecha_inicio,
    fecha_final,
    dias: int,
    last_vd_enviado_hasta=None,
    usar_personalizada: bool | None = None,
) -> tuple[str, str]:
    usar = personalizada if usar_personalizada is None else usar_personalizada
    if usar and fecha_inicio and fecha_final:
        return calcular_rango_exportacion(
            hoy="",
            usar_personalizada=True,
            fecha_inicio=fecha_inicio,
            fecha_final=fecha_final,
        )
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT DATE_FORMAT(CURDATE(), '%%Y-%%m-%%d') AS hoy")
        hoy = cursor.fetchone()["hoy"]
    return calcular_rango_exportacion(
        hoy=hoy,
        last_vd_enviado_hasta=last_vd_enviado_hasta,
        dias=dias,
        usar_personalizada=False,
    )


def obtener_cuit_empresa(base_empresa: str) -> tuple[str, str]:
    """CUIT crudo (con guiones) y CUIT sin guiones para CSV."""
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT CUIT FROM datosempresa LIMIT 1")
        row = cursor.fetchone() or {}
    crudo = str_or_default(row.get("CUIT"), "")
    return crudo, crudo.replace("-", "")


def obtener_cnpj_distribuidor(base_empresa: str) -> str:
    _crudo, limpio = obtener_cuit_empresa(base_empresa)
    return limpio


def obtener_razon_empresa(base_empresa: str) -> str:
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT Nombre FROM datosempresa LIMIT 1")
        row = cursor.fetchone() or {}
    return str_or_default(row.get("Nombre"), "DISTRIBUIDOR") or "DISTRIBUIDOR"


def fetch_all(cursor, sql: str, params: Sequence[Any] | None = None) -> list[dict]:
    cursor.execute(sql, params or ())
    rows = cursor.fetchall() or []
    return [dict(r) for r in rows]


def ean_crudo_invalido(ean: Any) -> bool:
    texto = str(ean or "").strip()
    if texto == "" or texto.upper() == "NA":
        return True
    return texto.replace("0", "") == ""


def ids_articulos_con_venta(
    cfg: ExportConfig,
    *,
    codigo_prov: str = "TODOS",
    codigos_prov: list[str] | None = None,
) -> set[int]:
    sql = """
SELECT DISTINCT stock.IDArt
FROM cuentacliente
INNER JOIN stock ON (stock.CodigoMovimiento = cuentacliente.CodigoMovimiento)
LEFT JOIN articulo ON (articulo.IDArt = stock.IDArt)
LEFT JOIN punto_venta ON (punto_venta.id_punto_venta = cuentacliente.id_pv)
WHERE cuentacliente.Anulado = 'No'
  AND cuentacliente.TipoComprobante <> 'REC'
  AND cuentacliente.Fecha BETWEEN %s AND %s
  AND stock.IDArt IS NOT NULL
"""
    params: list = [cfg.fecha_desde, cfg.fecha_hasta]
    filtro, extra = sql_filtro_proveedor(
        normalizar_codigos_prov(codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    )
    if filtro:
        sql += f" AND {filtro}"
        params.extend(extra)
    if not cfg.pvnf:
        sql += " AND punto_venta.cont = 'Si'"
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        filas = fetch_all(cursor, sql, params)
    ids: set[int] = set()
    for fila in filas:
        numero = to_int_or_none(fila.get("IDArt") or fila.get("idart"))
        if numero is not None:
            ids.add(numero)
    return ids


def conservar_si_ean_o_venta(row: dict, vendidos: set[int]) -> bool:
    if not ean_crudo_invalido(row.get("EAN")):
        return True
    id_art = to_int_or_none(row.get("ID_ART") or row.get("id_articulo") or row.get("id_art"))
    return id_art is not None and id_art in vendidos
