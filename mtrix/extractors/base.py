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


def resolver_fechas_mysql(base_empresa: str, *, personalizada: bool, fecha_inicio, fecha_final, dias: int) -> tuple[str, str]:
    if personalizada and fecha_inicio and fecha_final:
        di = fecha_inicio.isoformat() if hasattr(fecha_inicio, "isoformat") else str(fecha_inicio)
        df = fecha_final.isoformat() if hasattr(fecha_final, "isoformat") else str(fecha_final)
        return di, df
    dias_n = max(int(dias or 5), 1)
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT DATE_FORMAT(CURDATE(), '%%Y-%%m-%%d') AS hoy")
        hoy = cursor.fetchone()["hoy"]
        cursor.execute(
            "SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL %s DAY), '%%Y-%%m-%%d') AS desde",
            (dias_n,),
        )
        desde = cursor.fetchone()["desde"]
    return desde, hoy


def obtener_cnpj_distribuidor(base_empresa: str) -> str:
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT CUIT FROM datosempresa LIMIT 1")
        row = cursor.fetchone() or {}
    return str_or_default(row.get("CUIT"), "").replace("-", "")


def obtener_razon_empresa(base_empresa: str) -> str:
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute("SELECT Nombre FROM datosempresa LIMIT 1")
        row = cursor.fetchone() or {}
    return str_or_default(row.get("Nombre"), "DISTRIBUIDOR") or "DISTRIBUIDOR"


def fetch_all(cursor, sql: str, params: Sequence[Any] | None = None) -> list[dict]:
    cursor.execute(sql, params or ())
    rows = cursor.fetchall() or []
    return [dict(r) for r in rows]
