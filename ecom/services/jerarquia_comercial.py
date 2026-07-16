"""
Jerarquía comercial Gerente → Supervisor → Vendedor (árbol 1 padre).

Tablas: ``ecom_org_gerente_supervisor``, ``ecom_org_supervisor_vendedor``.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none

from ecom.services.ecom_config_mysql import leer_valor_configuracion_ecom
from ecom.services.vendedor_operativo import (
    clave_config_vendedores_a_cargo,
    normalizar_lista_cod_viajantes,
)

logger = logging.getLogger(__name__)

RolJerarquia = Literal["gerente", "supervisor", "vendedor", "ninguno"]
_ACTIVO_SI = "Si"
_ACTIVO_NO = "No"
_CLAVE_CARTERA_PREFIX = "ecom_vendedores_a_cargo_"


def _ahora() -> datetime:
    return datetime.now()


def _si_activo(val: Any) -> bool:
    return str_or_default(val, _ACTIVO_NO).strip().lower() in ("si", "sí", "1", "true")


def _fetchall_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall() or []
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return list(rows)
    cols = [d[0] for d in (cursor.description or [])]
    return [dict(zip(cols, r)) for r in rows]


def rol_de(base_empresa: str, cod_viajante: int) -> RolJerarquia:
    """Determina el rol orgánico del viajante (prioridad: gerente > supervisor > vendedor)."""
    cv = to_int_or_none(cod_viajante)
    if cv is None or not (base_empresa or "").strip():
        return "ninguno"
    base = base_empresa.strip()
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT 1 FROM ecom_org_gerente_supervisor
                    WHERE cod_gerente = %s AND activo = %s LIMIT 1
                    """,
                    (cv, _ACTIVO_SI),
                )
                if cursor.fetchone():
                    return "gerente"
                cursor.execute(
                    """
                    SELECT 1 FROM ecom_org_gerente_supervisor
                    WHERE cod_supervisor = %s AND activo = %s
                    UNION
                    SELECT 1 FROM ecom_org_supervisor_vendedor
                    WHERE cod_supervisor = %s AND activo = %s
                    LIMIT 1
                    """,
                    (cv, _ACTIVO_SI, cv, _ACTIVO_SI),
                )
                if cursor.fetchone():
                    return "supervisor"
                cursor.execute(
                    """
                    SELECT 1 FROM ecom_org_supervisor_vendedor
                    WHERE cod_vendedor = %s AND activo = %s LIMIT 1
                    """,
                    (cv, _ACTIVO_SI),
                )
                if cursor.fetchone():
                    return "vendedor"
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("rol_de (%s, %s): %s", base, cv, exc)
    return "ninguno"


def _supervisores_de_gerente(cursor, cod_gerente: int) -> List[int]:
    cursor.execute(
        """
        SELECT cod_supervisor FROM ecom_org_gerente_supervisor
        WHERE cod_gerente = %s AND activo = %s
        """,
        (cod_gerente, _ACTIVO_SI),
    )
    out: List[int] = []
    for row in _fetchall_dict(cursor):
        n = to_int_or_none(row.get("cod_supervisor"))
        if n is not None:
            out.append(n)
    return out


def _vendedores_de_supervisor(cursor, cod_supervisor: int) -> List[int]:
    cursor.execute(
        """
        SELECT cod_vendedor FROM ecom_org_supervisor_vendedor
        WHERE cod_supervisor = %s AND activo = %s
        """,
        (cod_supervisor, _ACTIVO_SI),
    )
    out: List[int] = []
    for row in _fetchall_dict(cursor):
        n = to_int_or_none(row.get("cod_vendedor"))
        if n is not None:
            out.append(n)
    return out


def subarbol_de(
    base_empresa: str,
    cod_viajante: int,
    rol: Optional[RolJerarquia] = None,
) -> List[int]:
    """Devuelve el subárbol activo (incluye el nodo raíz)."""
    cv = to_int_or_none(cod_viajante)
    if cv is None or not (base_empresa or "").strip():
        return []
    rol_eff = rol if rol and rol != "ninguno" else rol_de(base_empresa, cv)
    if rol_eff == "ninguno":
        return [cv]
    base = base_empresa.strip()
    seen: set[int] = set()
    out: List[int] = []

    def _add(c: int) -> None:
        if c not in seen:
            seen.add(c)
            out.append(c)

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                _add(cv)
                if rol_eff == "vendedor":
                    return out
                if rol_eff == "supervisor":
                    for v in _vendedores_de_supervisor(cursor, cv):
                        _add(v)
                    return out
                # gerente
                for sup in _supervisores_de_gerente(cursor, cv):
                    _add(sup)
                    for v in _vendedores_de_supervisor(cursor, sup):
                        _add(v)
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("subarbol_de (%s, %s): %s", base, cv, exc)
        return [cv]
    return out


def _gerente_de_supervisor(cursor, cod_supervisor: int) -> Optional[int]:
    cursor.execute(
        """
        SELECT cod_gerente FROM ecom_org_gerente_supervisor
        WHERE cod_supervisor = %s AND activo = %s LIMIT 1
        """,
        (cod_supervisor, _ACTIVO_SI),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return to_int_or_none(row.get("cod_gerente"))
    return to_int_or_none(row[0])


def _supervisor_de_vendedor(cursor, cod_vendedor: int) -> Optional[int]:
    cursor.execute(
        """
        SELECT cod_supervisor FROM ecom_org_supervisor_vendedor
        WHERE cod_vendedor = %s AND activo = %s LIMIT 1
        """,
        (cod_vendedor, _ACTIVO_SI),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return to_int_or_none(row.get("cod_supervisor"))
    return to_int_or_none(row[0])


def _validar_sin_ciclo_gerente_supervisor(
    cursor,
    cod_gerente: int,
    cod_supervisor: int,
) -> Tuple[bool, str]:
    """Evita que el supervisor sea ancestro del gerente."""
    visitado: set[int] = set()
    actual: Optional[int] = cod_gerente
    while actual is not None and actual not in visitado:
        if actual == cod_supervisor:
            return False, "La vinculación crearía un ciclo en la jerarquía."
        visitado.add(actual)
        sup = _gerente_de_supervisor(cursor, actual)
        if sup is None:
            padre_v = _supervisor_de_vendedor(cursor, actual)
            actual = padre_v
        else:
            actual = sup
    return True, ""


def vincular_gerente_supervisor(
    base_empresa: str,
    cod_gerente: int,
    cod_supervisor: int,
) -> Tuple[bool, str]:
    """Crea o reactiva vínculo gerente→supervisor (1 padre por supervisor activo)."""
    g = to_int_or_none(cod_gerente)
    s = to_int_or_none(cod_supervisor)
    if g is None or s is None:
        return False, "Códigos de gerente y supervisor inválidos."
    if g == s:
        return False, "Gerente y supervisor no pueden ser el mismo código."
    base = (base_empresa or "").strip()
    if not base:
        return False, "Base de empresa inválida."
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                ok_ciclo, msg_ciclo = _validar_sin_ciclo_gerente_supervisor(cursor, g, s)
                if not ok_ciclo:
                    return False, msg_ciclo
                cursor.execute(
                    """
                    SELECT id, cod_gerente, activo FROM ecom_org_gerente_supervisor
                    WHERE cod_supervisor = %s LIMIT 1
                    """,
                    (s,),
                )
                row = cursor.fetchone()
                ahora = _ahora()
                if row:
                    if isinstance(row, dict):
                        rid = to_int_or_none(row.get("id"))
                        actual_g = to_int_or_none(row.get("cod_gerente"))
                        activo = row.get("activo")
                    else:
                        rid, actual_g, activo = row[0], row[1], row[2]
                    if _si_activo(activo) and actual_g == g:
                        return True, "Vínculo ya existente."
                    if _si_activo(activo) and actual_g != g:
                        return False, "El supervisor ya tiene un gerente activo asignado."
                    cursor.execute(
                        """
                        UPDATE ecom_org_gerente_supervisor
                        SET cod_gerente = %s, activo = %s, actualizado_en = %s
                        WHERE id = %s
                        """,
                        (g, _ACTIVO_SI, ahora, rid),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO ecom_org_gerente_supervisor
                            (cod_gerente, cod_supervisor, activo, creado_en, actualizado_en)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (g, s, _ACTIVO_SI, ahora, ahora),
                    )
                conn.commit()
                return True, "Vínculo gerente→supervisor guardado."
            finally:
                cursor.close()
    except Exception as exc:
        logger.exception("vincular_gerente_supervisor: %s", exc)
        return False, f"Error al guardar vínculo: {exc}"


def vincular_supervisor_vendedor(
    base_empresa: str,
    cod_supervisor: int,
    cod_vendedor: int,
) -> Tuple[bool, str]:
    """Crea o reactiva vínculo supervisor→vendedor (1 padre por vendedor activo)."""
    s = to_int_or_none(cod_supervisor)
    v = to_int_or_none(cod_vendedor)
    if s is None or v is None:
        return False, "Códigos de supervisor y vendedor inválidos."
    if s == v:
        return False, "Supervisor y vendedor no pueden ser el mismo código."
    base = (base_empresa or "").strip()
    if not base:
        return False, "Base de empresa inválida."
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT id, cod_supervisor, activo FROM ecom_org_supervisor_vendedor
                    WHERE cod_vendedor = %s LIMIT 1
                    """,
                    (v,),
                )
                row = cursor.fetchone()
                ahora = _ahora()
                if row:
                    if isinstance(row, dict):
                        rid = to_int_or_none(row.get("id"))
                        actual_s = to_int_or_none(row.get("cod_supervisor"))
                        activo = row.get("activo")
                    else:
                        rid, actual_s, activo = row[0], row[1], row[2]
                    if _si_activo(activo) and actual_s == s:
                        return True, "Vínculo ya existente."
                    if _si_activo(activo) and actual_s != s:
                        return False, "El vendedor ya tiene un supervisor activo asignado."
                    cursor.execute(
                        """
                        UPDATE ecom_org_supervisor_vendedor
                        SET cod_supervisor = %s, activo = %s, actualizado_en = %s
                        WHERE id = %s
                        """,
                        (s, _ACTIVO_SI, ahora, rid),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO ecom_org_supervisor_vendedor
                            (cod_supervisor, cod_vendedor, activo, creado_en, actualizado_en)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (s, v, _ACTIVO_SI, ahora, ahora),
                    )
                conn.commit()
                return True, "Vínculo supervisor→vendedor guardado."
            finally:
                cursor.close()
    except Exception as exc:
        logger.exception("vincular_supervisor_vendedor: %s", exc)
        return False, f"Error al guardar vínculo: {exc}"


def desactivar_vinculo_gerente_supervisor(
    base_empresa: str,
    cod_supervisor: int,
) -> Tuple[bool, str]:
    s = to_int_or_none(cod_supervisor)
    if s is None:
        return False, "Código de supervisor inválido."
    base = (base_empresa or "").strip()
    if not base:
        return False, "Base de empresa inválida."
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE ecom_org_gerente_supervisor
                    SET activo = %s, actualizado_en = %s
                    WHERE cod_supervisor = %s AND activo = %s
                    """,
                    (_ACTIVO_NO, _ahora(), s, _ACTIVO_SI),
                )
                conn.commit()
                if cursor.rowcount:
                    return True, "Vínculo gerente→supervisor desactivado."
                return False, "No se encontró vínculo activo para el supervisor."
            finally:
                cursor.close()
    except Exception as exc:
        logger.exception("desactivar_vinculo_gerente_supervisor: %s", exc)
        return False, f"Error al desactivar: {exc}"


def desactivar_vinculo_supervisor_vendedor(
    base_empresa: str,
    cod_vendedor: int,
) -> Tuple[bool, str]:
    v = to_int_or_none(cod_vendedor)
    if v is None:
        return False, "Código de vendedor inválido."
    base = (base_empresa or "").strip()
    if not base:
        return False, "Base de empresa inválida."
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE ecom_org_supervisor_vendedor
                    SET activo = %s, actualizado_en = %s
                    WHERE cod_vendedor = %s AND activo = %s
                    """,
                    (_ACTIVO_NO, _ahora(), v, _ACTIVO_SI),
                )
                conn.commit()
                if cursor.rowcount:
                    return True, "Vínculo supervisor→vendedor desactivado."
                return False, "No se encontró vínculo activo para el vendedor."
            finally:
                cursor.close()
    except Exception as exc:
        logger.exception("desactivar_vinculo_supervisor_vendedor: %s", exc)
        return False, f"Error al desactivar: {exc}"


def listar_arbol_jerarquia(base_empresa: str) -> Dict[str, Any]:
    """Estructura del árbol activo para ABM."""
    base = (base_empresa or "").strip()
    if not base:
        return {"gerentes": [], "vinculos_gs": [], "vinculos_sv": []}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT id, cod_gerente, cod_supervisor, activo
                    FROM ecom_org_gerente_supervisor
                    WHERE activo = %s
                    ORDER BY cod_gerente, cod_supervisor
                    """,
                    (_ACTIVO_SI,),
                )
                vinculos_gs = _fetchall_dict(cursor)
                cursor.execute(
                    """
                    SELECT id, cod_supervisor, cod_vendedor, activo
                    FROM ecom_org_supervisor_vendedor
                    WHERE activo = %s
                    ORDER BY cod_supervisor, cod_vendedor
                    """,
                    (_ACTIVO_SI,),
                )
                vinculos_sv = _fetchall_dict(cursor)
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("listar_arbol_jerarquia (%s): %s", base, exc)
        return {"gerentes": [], "vinculos_gs": [], "vinculos_sv": [], "error": str(exc)}

    gerentes_set: set[int] = set()
    supervisores_set: set[int] = set()
    for row in vinculos_gs:
        g = to_int_or_none(row.get("cod_gerente"))
        s = to_int_or_none(row.get("cod_supervisor"))
        if g is not None:
            gerentes_set.add(g)
        if s is not None:
            supervisores_set.add(s)
    for row in vinculos_sv:
        s = to_int_or_none(row.get("cod_supervisor"))
        if s is not None:
            supervisores_set.add(s)

    raices = gerentes_set | {s for s in supervisores_set if not any(
        to_int_or_none(r.get("cod_supervisor")) == s for r in vinculos_gs
    )}

    return {
        "gerentes": sorted(raices),
        "vinculos_gs": vinculos_gs,
        "vinculos_sv": vinculos_sv,
    }


def _listar_claves_carteras_json(cursor) -> List[Tuple[int, str]]:
    """Claves ``ecom_vendedores_a_cargo_<cod>`` en configuracion_ecom."""
    cursor.execute(
        """
        SELECT key_permiso, valor_permiso FROM configuracion_ecom
        WHERE key_permiso LIKE %s
        """,
        (f"{_CLAVE_CARTERA_PREFIX}%",),
    )
    out: List[Tuple[int, str]] = []
    patron = re.compile(rf"^{re.escape(_CLAVE_CARTERA_PREFIX)}(\d+)$")
    for row in _fetchall_dict(cursor):
        key = str(row.get("key_permiso") or "")
        m = patron.match(key)
        if not m:
            continue
        cod = to_int_or_none(m.group(1))
        if cod is not None:
            out.append((cod, str(row.get("valor_permiso") or "")))
    return out


def backfill_carteras_desde_config(
    base_empresa: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Migra carteras JSON ``ecom_vendedores_a_cargo_*`` a tablas org (idempotente).
    No borra claves legacy.
    """
    base = (base_empresa or "").strip()
    if not base:
        return {"ok": False, "error": "Base inválida.", "vinculos_sv": 0, "vinculos_gs": 0}
    stats = {"vinculos_sv": 0, "vinculos_gs": 0, "supervisores": 0}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                claves = _listar_claves_carteras_json(cursor)
                supervisores_procesados: set[int] = set()
                for cod_supervisor, raw in claves:
                    vendedores = normalizar_lista_cod_viajantes(raw)
                    vendedores = [v for v in vendedores if v != cod_supervisor]
                    if not vendedores:
                        continue
                    supervisores_procesados.add(cod_supervisor)
                    for cod_v in vendedores:
                        if dry_run:
                            stats["vinculos_sv"] += 1
                            continue
                        ok, _ = vincular_supervisor_vendedor(base, cod_supervisor, cod_v)
                        if ok:
                            stats["vinculos_sv"] += 1
                stats["supervisores"] = len(supervisores_procesados)
                # Supervisores sin gerente: raíz (no se crea vínculo GS automático)
                conn.commit()
            finally:
                cursor.close()
    except Exception as exc:
        logger.exception("backfill_carteras_desde_config: %s", exc)
        return {"ok": False, "error": str(exc), **stats}
    return {"ok": True, "message": "Backfill completado.", **stats}
