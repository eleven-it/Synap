from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.mysql_pool import get_connection
from core.utils.administranet_types import str_or_default, to_int_or_none


def _normalizar_cuit(cuit: str) -> str:
    return "".join(ch for ch in str(cuit or "") if ch.isdigit())


@dataclass(frozen=True)
class ProveedorLegacyDTO:
    codigo: int
    nombre: str
    cuit: str


def buscar_proveedor_por_cuit(base_empresa: str, cuit: str) -> ProveedorLegacyDTO | None:
    cuit_norm = _normalizar_cuit(cuit)
    if len(cuit_norm) != 11:
        return None
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Codigo, COALESCE(Nombre, ''), COALESCE(CUIT, '')
            FROM proveedor
            WHERE REPLACE(REPLACE(COALESCE(CUIT, ''), '-', ''), ' ', '') = %s
              AND COALESCE(estado, '') <> 'Anulado'
            LIMIT 1
            """,
            [cuit_norm],
        )
        row = cursor.fetchone()
        cursor.close()
    if not row:
        return None
    return ProveedorLegacyDTO(codigo=int(row[0]), nombre=str(row[1]), cuit=str(row[2]))


def _next_codigo_proveedor(cursor) -> int:
    cursor.execute("SELECT COALESCE(MAX(Codigo), 0) + 1 FROM proveedor")
    row = cursor.fetchone()
    return int(row[0] or 1)


def _id_iva_desde_tipo_factura(tipo_factura_sugerida: str | None) -> int | None:
    t = (tipo_factura_sugerida or "").strip().upper()
    if t == "FA":
        return 1
    if t == "FB":
        return 5
    if t == "FC":
        # Receptor monotributo / Factura C (coherente con tabla proveedor AdministraNET)
        return 6
    return None


def crear_proveedor_desde_borrador(
    *,
    base_empresa: str,
    cuit: str,
    razon_social: str,
    tipo_factura_sugerida: str | None = None,
) -> ProveedorLegacyDTO:
    cuit_norm = _normalizar_cuit(cuit)
    if len(cuit_norm) != 11:
        raise ValueError("CUIT inválido para alta de proveedor.")
    nombre = str_or_default(razon_social, default="PROVEEDOR SIN DENOMINACION")
    with get_connection(base_empresa) as conn:
        conn.autocommit(False)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT Codigo, COALESCE(Nombre, ''), COALESCE(CUIT, '')
            FROM proveedor
            WHERE REPLACE(REPLACE(COALESCE(CUIT, ''), '-', ''), ' ', '') = %s
              AND COALESCE(estado, '') <> 'Anulado'
            LIMIT 1
            """,
            [cuit_norm],
        )
        row = cursor.fetchone()
        existente = (
            ProveedorLegacyDTO(codigo=int(row[0]), nombre=str(row[1]), cuit=str(row[2]))
            if row
            else None
        )
        if existente:
            conn.rollback()
            cursor.close()
            return existente
        codigo = _next_codigo_proveedor(cursor)
        id_iva = to_int_or_none(_id_iva_desde_tipo_factura(tipo_factura_sugerida))
        cursor.execute(
            """
            INSERT INTO proveedor (
                Codigo, Nombre, CUIT, IDIva, Tipo, TipoViajante, estado, saldo, descuento, credito
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                codigo,
                nombre,
                cuit_norm,
                id_iva,
                "Mercaderias",
                "No",
                "Activo",
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
            ],
        )
        conn.commit()
        cursor.close()
    return ProveedorLegacyDTO(codigo=codigo, nombre=nombre, cuit=cuit_norm)
