"""Alcance territorial efectivo de las consultas del Command Center.

Una selección vacía en la URL significa todos los PV autorizados, no todos
los PV de la empresa. Un usuario sin asignaciones no hereda acceso global.
"""
from __future__ import annotations

from dataclasses import replace

from core.utils.administranet_types import to_int_or_none
from core.utils.permissions import user_has_full_access

from .base import DashboardFilters, legacy_cursor


class TerritoryAccessDenied(Exception):
    pass


def constrain_filters_to_user(
    user, filters: DashboardFilters, *, area_key: str
) -> DashboardFilters:
    """Interseca PV, sucursal o depósitos con las asignaciones del usuario."""
    if user_has_full_access(user):
        return filters

    id_usuario = to_int_or_none(getattr(user, "id_usuario", None))
    if not id_usuario:
        raise TerritoryAccessDenied("No se pudo verificar el alcance territorial del usuario.")

    if area_key not in {
        "resumen_general", "ventas", "inventario", "preparacion_pedidos",
        "compras", "financiero", "impositivo", "libros_contables", "gastos",
    }:
        raise TerritoryAccessDenied("Este tablero aún no tiene alcance territorial verificado.")

    with legacy_cursor(filters.base_empresa) as cursor:
        if area_key == "inventario":
            cursor.execute(
                "SELECT DISTINCT id_deposito FROM deposito_usr WHERE id_usuario = %s",
                [id_usuario],
            )
            deposits = tuple(sorted({int(row[0]) for row in cursor.fetchall() or [] if to_int_or_none(row[0])}))
            if filters.depositos_filtro:
                requested = set(filters.depositos_filtro)
                deposits = tuple(dep for dep in deposits if dep in requested)
            if not deposits:
                raise TerritoryAccessDenied("No hay depósitos autorizados en la selección.")
            return replace(filters, depositos_filtro=deposits)

        cursor.execute(
            """
            SELECT DISTINCT pu.id_pv, pv.id_sucursal
            FROM punto_venta_usr pu
            INNER JOIN punto_venta pv ON pv.id_punto_venta = pu.id_pv
            WHERE pu.id_usuario = %s
            """,
            [id_usuario],
        )
        rows = cursor.fetchall() or []

    allowed_pairs = {
        (int(pv), int(sucursal))
        for pv, sucursal in rows
        if to_int_or_none(pv) and to_int_or_none(sucursal)
    }
    if not allowed_pairs:
        raise TerritoryAccessDenied("No hay puntos de venta autorizados para este usuario.")

    requested_pv = set(filters.puntos_venta)
    requested_suc = set(filters.sucursales_filtro)
    selected_pairs = {
        (pv, suc)
        for pv, suc in allowed_pairs
        if (not requested_pv or pv in requested_pv)
        and (not requested_suc or suc in requested_suc)
    }
    if not selected_pairs:
        raise TerritoryAccessDenied("La selección territorial no está autorizada.")

    return replace(
        filters,
        puntos_venta=tuple(sorted({pv for pv, _ in selected_pairs})),
        sucursales_filtro=tuple(sorted({suc for _, suc in selected_pairs})),
    )


def list_filter_options(user, base_empresa: str, filter_type: str) -> list[dict]:
    """Opciones territoriales visibles para el usuario; no consulta indicadores."""
    full_access = user_has_full_access(user)
    id_usuario = to_int_or_none(getattr(user, "id_usuario", None))
    if not full_access and not id_usuario:
        return []

    with legacy_cursor(base_empresa) as cursor:
        if filter_type == "puntos_venta":
            sql = """
                SELECT DISTINCT pv.id_punto_venta, pv.nro_punto_venta, pv.id_sucursal
                FROM punto_venta pv
            """
            params: list[int] = []
            if not full_access:
                sql += " INNER JOIN punto_venta_usr pu ON pu.id_pv = pv.id_punto_venta AND pu.id_usuario = %s"
                params.append(id_usuario)
            sql += " WHERE COALESCE(pv.anulado, 'No') = 'No' ORDER BY pv.nro_punto_venta"
            cursor.execute(sql, params)
            return [
                {"id": int(pv), "value": int(pv), "label": f"PV {nro}", "sucursal_id": suc}
                for pv, nro, suc in cursor.fetchall() or []
            ]

        if filter_type == "sucursales":
            sql = """
                SELECT DISTINCT s.id_sucursal, s.nombre_sucursal
                FROM sucursales s
            """
            params = []
            if not full_access:
                sql += " INNER JOIN punto_venta pv ON pv.id_sucursal = s.id_sucursal"
                sql += " INNER JOIN punto_venta_usr pu ON pu.id_pv = pv.id_punto_venta AND pu.id_usuario = %s"
                params.append(id_usuario)
            sql += " WHERE COALESCE(s.anulado, 'No') = 'No' ORDER BY s.nombre_sucursal"
            cursor.execute(sql, params)
            return [
                {"id": int(suc), "value": int(suc), "label": str(nombre or f"Sucursal {suc}")}
                for suc, nombre in cursor.fetchall() or []
            ]

        if filter_type == "depositos":
            sql = """
                SELECT DISTINCT d.CodDeposito, d.NombreDeposito
                FROM deposito d
            """
            params = []
            if not full_access:
                sql += " INNER JOIN deposito_usr du ON du.id_deposito = d.CodDeposito AND du.id_usuario = %s"
                params.append(id_usuario)
            sql += " WHERE COALESCE(d.anulado, 'No') = 'No' ORDER BY d.NombreDeposito"
            cursor.execute(sql, params)
            return [
                {"id": int(dep), "value": int(dep), "label": str(nombre or f"Depósito {dep}")}
                for dep, nombre in cursor.fetchall() or []
            ]

    raise ValueError("Tipo de filtro desconocido.")
