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
    *,
    mover: bool = False,
    id_usuario_gerente: Optional[int] = None,
    id_usuario_supervisor: Optional[int] = None,
) -> Tuple[bool, str]:
    """Crea o reactiva vínculo gerente→supervisor (1 padre por supervisor activo).

    Si el supervisor ya tiene otro gerente activo y ``mover`` es False, falla.
    Con ``mover=True`` actualiza el padre (mueve de rama).
    """
    g = to_int_or_none(cod_gerente)
    s = to_int_or_none(cod_supervisor)
    id_g = to_int_or_none(id_usuario_gerente)
    id_s = to_int_or_none(id_usuario_supervisor)
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
                        if id_g is not None or id_s is not None:
                            cursor.execute(
                                """
                                UPDATE ecom_org_gerente_supervisor
                                SET id_usuario_gerente = COALESCE(%s, id_usuario_gerente),
                                    id_usuario_supervisor = COALESCE(%s, id_usuario_supervisor),
                                    actualizado_en = %s
                                WHERE id = %s
                                """,
                                (id_g, id_s, ahora, rid),
                            )
                            conn.commit()
                        return True, "Vínculo ya existente."
                    if _si_activo(activo) and actual_g != g and not mover:
                        return (
                            False,
                            "El supervisor ya tiene un gerente activo asignado.",
                        )
                    cursor.execute(
                        """
                        UPDATE ecom_org_gerente_supervisor
                        SET cod_gerente = %s,
                            id_usuario_gerente = COALESCE(%s, id_usuario_gerente),
                            id_usuario_supervisor = COALESCE(%s, id_usuario_supervisor),
                            activo = %s,
                            actualizado_en = %s
                        WHERE id = %s
                        """,
                        (g, id_g, id_s, _ACTIVO_SI, ahora, rid),
                    )
                    conn.commit()
                    if _si_activo(activo) and actual_g != g:
                        return True, "Supervisor movido al nuevo gerente."
                    return True, "Vínculo gerente→supervisor guardado."
                cursor.execute(
                    """
                    INSERT INTO ecom_org_gerente_supervisor
                        (cod_gerente, cod_supervisor, id_usuario_gerente, id_usuario_supervisor,
                         activo, creado_en, actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (g, s, id_g, id_s, _ACTIVO_SI, ahora, ahora),
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
    *,
    mover: bool = False,
    id_usuario_supervisor: Optional[int] = None,
) -> Tuple[bool, str]:
    """Crea o reactiva vínculo supervisor→vendedor (1 padre por vendedor activo).

    Si el vendedor ya tiene otro supervisor activo y ``mover`` es False, falla.
    Con ``mover=True`` actualiza el padre (mueve de rama).
    """
    s = to_int_or_none(cod_supervisor)
    v = to_int_or_none(cod_vendedor)
    id_s = to_int_or_none(id_usuario_supervisor)
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
                        if id_s is not None:
                            cursor.execute(
                                """
                                UPDATE ecom_org_supervisor_vendedor
                                SET id_usuario_supervisor = %s, actualizado_en = %s
                                WHERE id = %s
                                """,
                                (id_s, ahora, rid),
                            )
                            conn.commit()
                        return True, "Vínculo ya existente."
                    if _si_activo(activo) and actual_s != s and not mover:
                        return (
                            False,
                            "El vendedor ya tiene un supervisor activo asignado.",
                        )
                    cursor.execute(
                        """
                        UPDATE ecom_org_supervisor_vendedor
                        SET cod_supervisor = %s,
                            id_usuario_supervisor = COALESCE(%s, id_usuario_supervisor),
                            activo = %s,
                            actualizado_en = %s
                        WHERE id = %s
                        """,
                        (s, id_s, _ACTIVO_SI, ahora, rid),
                    )
                    conn.commit()
                    if _si_activo(activo) and actual_s != s:
                        return True, "Vendedor movido al nuevo supervisor."
                    return True, "Vínculo supervisor→vendedor guardado."
                cursor.execute(
                    """
                    INSERT INTO ecom_org_supervisor_vendedor
                        (cod_supervisor, cod_vendedor, id_usuario_supervisor, activo, creado_en,
                         actualizado_en)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (s, v, id_s, _ACTIVO_SI, ahora, ahora),
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
                    SELECT id, cod_gerente, cod_supervisor, id_usuario_gerente,
                           id_usuario_supervisor, activo
                    FROM ecom_org_gerente_supervisor
                    WHERE activo = %s
                    ORDER BY cod_gerente, cod_supervisor
                    """,
                    (_ACTIVO_SI,),
                )
                vinculos_gs = _fetchall_dict(cursor)
                cursor.execute(
                    """
                    SELECT id, cod_supervisor, cod_vendedor, id_usuario_supervisor, activo
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

    for row in vinculos_gs:
        row["id_usuario_gerente"] = to_int_or_none(row.get("id_usuario_gerente"))
        row["id_usuario_supervisor"] = to_int_or_none(row.get("id_usuario_supervisor"))
    for row in vinculos_sv:
        row["id_usuario_supervisor"] = to_int_or_none(row.get("id_usuario_supervisor"))

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

    codigos: set[int] = set(raices)
    for row in vinculos_gs:
        for k in ("cod_gerente", "cod_supervisor"):
            n = to_int_or_none(row.get(k))
            if n is not None:
                codigos.add(n)
    for row in vinculos_sv:
        for k in ("cod_supervisor", "cod_vendedor"):
            n = to_int_or_none(row.get(k))
            if n is not None:
                codigos.add(n)
    etiquetas = etiquetas_viajantes_usuarios(base, sorted(codigos))
    ids_usuarios = {
        id_usuario
        for row in vinculos_gs
        for id_usuario in (
            to_int_or_none(row.get("id_usuario_gerente")),
            to_int_or_none(row.get("id_usuario_supervisor")),
        )
        if id_usuario is not None
    }
    ids_usuarios.update(
        id_usuario
        for row in vinculos_sv
        for id_usuario in (to_int_or_none(row.get("id_usuario_supervisor")),)
        if id_usuario is not None
    )
    etiquetas_usuarios = etiquetas_usuarios_por_id(base, sorted(ids_usuarios))

    def _etiq(cod: Any, id_usuario: Any = None) -> str:
        usuario_id = to_int_or_none(id_usuario)
        if usuario_id is not None and etiquetas_usuarios.get(usuario_id):
            return etiquetas_usuarios[usuario_id]
        n = to_int_or_none(cod)
        if n is None:
            return "—"
        return etiquetas.get(n) or f"Viajante {n}"

    for row in vinculos_gs:
        row["etiqueta_gerente"] = _etiq(
            row.get("cod_gerente"), row.get("id_usuario_gerente")
        )
        row["etiqueta_supervisor"] = _etiq(
            row.get("cod_supervisor"), row.get("id_usuario_supervisor")
        )
        row["etiqueta"] = f"{row['etiqueta_gerente']} → {row['etiqueta_supervisor']}"
    for row in vinculos_sv:
        row["etiqueta_supervisor"] = _etiq(
            row.get("cod_supervisor"), row.get("id_usuario_supervisor")
        )
        row["etiqueta_vendedor"] = _etiq(row.get("cod_vendedor"))
        row["etiqueta"] = f"{row['etiqueta_supervisor']} → {row['etiqueta_vendedor']}"

    return {
        "gerentes": sorted(raices),
        "vinculos_gs": vinculos_gs,
        "vinculos_sv": vinculos_sv,
        "etiquetas": etiquetas,
    }


def etiquetas_usuarios_por_id(
    base_empresa: str,
    ids_usuarios: Sequence[int],
) -> Dict[int, str]:
    """Mapa ``usuarios.id_usuario`` a nombre y apellido para vínculos explícitos."""
    ids = [to_int_or_none(id_usuario) for id_usuario in ids_usuarios]
    ids = [id_usuario for id_usuario in ids if id_usuario is not None]
    if not ids or not (base_empresa or "").strip():
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"""
                    SELECT id_usuario, nombre_usuario, apellido_usuario
                    FROM usuarios
                    WHERE id_usuario IN ({placeholders})
                    """,
                    tuple(ids),
                )
                return {
                    id_usuario: etiqueta
                    for row in _fetchall_dict(cursor)
                    for id_usuario, etiqueta in [
                        (
                            to_int_or_none(row.get("id_usuario")),
                            _etiqueta_nombre_apellido(row),
                        )
                    ]
                    if id_usuario is not None and etiqueta
                }
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("etiquetas_usuarios_por_id (%s): %s", base_empresa, exc)
        return {}


def etiquetas_viajantes_usuarios(
    base_empresa: str,
    codigos: Sequence[int],
) -> Dict[int, str]:
    """Mapa CodViajante → etiqueta legible (nombre/apellido usuario o Nombre viajante)."""
    ids = [to_int_or_none(c) for c in codigos]
    ids = [i for i in ids if i is not None]
    if not ids or not (base_empresa or "").strip():
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    out: Dict[int, str] = {}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f"""
                    SELECT
                        u.CodViajante AS cod_viajante,
                        u.nombre_usuario,
                        u.apellido_usuario,
                        COALESCE(v.Nombre, '') AS nombre_viajante
                    FROM usuarios u
                    LEFT JOIN viajantes v ON v.CodViajante = u.CodViajante
                    WHERE u.CodViajante IN ({placeholders})
                      AND (u.baja_usuario IS NULL OR u.baja_usuario <> 'Si')
                    ORDER BY u.id_usuario
                    """,
                    tuple(ids),
                )
                for row in _fetchall_dict(cursor):
                    cv = to_int_or_none(row.get("cod_viajante"))
                    if cv is None or cv in out:
                        continue
                    out[cv] = _etiqueta_nombre_apellido(row) or str_or_default(
                        row.get("nombre_viajante"), ""
                    ).strip() or f"Viajante {cv}"
                faltan = [i for i in ids if i not in out]
                if faltan:
                    ph2 = ",".join(["%s"] * len(faltan))
                    cursor.execute(
                        f"""
                        SELECT CodViajante AS cod_viajante, COALESCE(Nombre, '') AS nombre_viajante
                        FROM viajantes WHERE CodViajante IN ({ph2})
                        """,
                        tuple(faltan),
                    )
                    for row in _fetchall_dict(cursor):
                        cv = to_int_or_none(row.get("cod_viajante"))
                        if cv is None or cv in out:
                            continue
                        nom = str_or_default(row.get("nombre_viajante"), "").strip()
                        out[cv] = nom or f"Viajante {cv}"
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("etiquetas_viajantes_usuarios (%s): %s", base_empresa, exc)
    return out


def _etiqueta_nombre_apellido(row: Dict[str, Any]) -> str:
    """Solo nombre y apellido (sin código de usuario ni vía.)."""
    return " ".join(
        p for p in (
            str_or_default(row.get("nombre_usuario"), "").strip(),
            str_or_default(row.get("apellido_usuario"), "").strip(),
        ) if p
    ).strip()


def _normalizar_puesto(nombre: str) -> str:
    """Normaliza nombre de puesto para comparar (minúsculas, sin acentos)."""
    import unicodedata

    raw = str_or_default(nombre, "").strip().lower()
    if not raw:
        return ""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", raw)
        if not unicodedata.combining(ch)
    )


# Puestos habilitados para Gerente / Supervisor comercial.
_PUESTOS_GERENTE_SUPERVISOR = frozenset({
    "supervisor",
    "administrador",
    "administracion",
    "ventas",
})


def _puesto_habilitado_gerente_supervisor(nombre_puesto: str) -> bool:
    return _normalizar_puesto(nombre_puesto) in _PUESTOS_GERENTE_SUPERVISOR


def buscar_usuarios_jerarquia(
    base_empresa: str,
    q: str = "",
    *,
    rol: str = "gerente",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Búsqueda predictiva para el ABM org.

    - ``rol`` gerente/supervisor: usuarios con puesto Supervisor, Administrador/
      Administración o Ventas y CodViajante > 0. Etiqueta = nombre + apellido.
    - ``rol`` vendedor: catálogo ``viajantes`` (no usuarios). Etiqueta = Nombre.
    """
    base = (base_empresa or "").strip()
    if not base:
        return []
    lim = max(1, min(to_int_or_none(limit) or 20, 50))
    term = (q or "").strip()
    rol_n = (rol or "gerente").strip().lower()
    if rol_n in ("vendedor", "vendedores", "viajante"):
        return _buscar_viajantes_jerarquia(base, term, lim)
    return _buscar_usuarios_gerente_supervisor(base, term, lim)


def _buscar_usuarios_gerente_supervisor(
    base: str,
    term: str,
    lim: int,
) -> List[Dict[str, Any]]:
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    SELECT
                        u.id_usuario,
                        u.cod_usuario,
                        u.nombre_usuario,
                        u.apellido_usuario,
                        u.CodViajante AS cod_viajante,
                        COALESCE(p.puesto, '') AS nombre_puesto,
                        COALESCE(v.Nombre, '') AS nombre_viajante
                    FROM usuarios u
                    LEFT JOIN puestos p ON p.idpuesto = u.id_puesto
                    LEFT JOIN viajantes v ON v.CodViajante = u.CodViajante
                    WHERE (u.baja_usuario IS NULL OR u.baja_usuario <> 'Si')
                      AND u.CodViajante IS NOT NULL
                      AND u.CodViajante > 0
                """
                params: List[Any] = []
                if term:
                    like = f"%{term}%"
                    sql += """
                      AND (
                        u.nombre_usuario LIKE %s
                        OR u.apellido_usuario LIKE %s
                        OR CONCAT(COALESCE(u.nombre_usuario,''), ' ', COALESCE(u.apellido_usuario,'')) LIKE %s
                        OR u.cod_usuario LIKE %s
                      )
                    """
                    params.extend([like, like, like, like])
                sql += " ORDER BY u.nombre_usuario, u.apellido_usuario LIMIT %s"
                params.append(max(lim * 5, 50))
                cursor.execute(sql, tuple(params))
                rows = _fetchall_dict(cursor)
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("_buscar_usuarios_gerente_supervisor (%s): %s", base, exc)
        return []

    out: List[Dict[str, Any]] = []
    seen_usuarios: set[int] = set()
    for row in rows:
        if not _puesto_habilitado_gerente_supervisor(str(row.get("nombre_puesto") or "")):
            continue
        cv = to_int_or_none(row.get("cod_viajante"))
        id_usuario = to_int_or_none(row.get("id_usuario"))
        if cv is None or id_usuario is None or id_usuario in seen_usuarios:
            continue
        seen_usuarios.add(id_usuario)
        etiqueta = _etiqueta_nombre_apellido(row)
        if not etiqueta:
            continue
        out.append(
            {
                "id_usuario": to_int_or_none(row.get("id_usuario")),
                "cod_usuario": str_or_default(row.get("cod_usuario"), "").strip(),
                "nombre_usuario": str_or_default(row.get("nombre_usuario"), "").strip(),
                "apellido_usuario": str_or_default(row.get("apellido_usuario"), "").strip(),
                "cod_viajante": cv,
                "nombre_puesto": str_or_default(row.get("nombre_puesto"), "").strip(),
                "nombre_viajante": str_or_default(row.get("nombre_viajante"), "").strip(),
                "etiqueta": etiqueta,
                "text": etiqueta,
            }
        )
        if len(out) >= lim:
            break
    return out


def _nombre_viajante_inutil(nombre: str) -> bool:
    """True si el Nombre del viajante es vacío, ``-Ninguno-`` o solo guiones/placeholders."""
    limpio = str_or_default(nombre, "").strip().lower()
    if not limpio:
        return True
    if limpio in ("-ninguno-", "ninguno", "(ninguno)", "sin nombre", "n/a", "na"):
        return True
    # Solo guiones, puntos, espacios u otros separadores sin contenido útil.
    if not re.sub(r"[\s\-_.·•]+", "", limpio):
        return True
    return False


def _buscar_viajantes_jerarquia(base: str, term: str, lim: int) -> List[Dict[str, Any]]:
    """Catálogo de vendedores (tabla viajantes), no usuarios del sistema."""
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cursor = conn.cursor()
            try:
                sql = """
                    SELECT
                        CodViajante AS cod_viajante,
                        COALESCE(Nombre, '') AS nombre_viajante
                    FROM viajantes
                    WHERE (Anulado IS NULL OR Anulado = 'No' OR Anulado = '')
                """
                params: List[Any] = []
                if term:
                    like = f"%{term}%"
                    sql += """
                      AND (
                        Nombre LIKE %s
                        OR CAST(CodViajante AS CHAR) LIKE %s
                      )
                    """
                    params.extend([like, like])
                sql += " ORDER BY Nombre, CodViajante LIMIT %s"
                params.append(lim)
                cursor.execute(sql, tuple(params))
                rows = _fetchall_dict(cursor)
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("_buscar_viajantes_jerarquia (%s): %s", base, exc)
        return []

    out: List[Dict[str, Any]] = []
    for row in rows:
        cv = to_int_or_none(row.get("cod_viajante"))
        if cv is None:
            continue
        nombre_raw = str_or_default(row.get("nombre_viajante"), "").strip()
        if _nombre_viajante_inutil(nombre_raw):
            continue
        nombre = nombre_raw
        out.append(
            {
                "id_usuario": None,
                "cod_usuario": "",
                "nombre_usuario": nombre,
                "apellido_usuario": "",
                "cod_viajante": cv,
                "nombre_viajante": nombre,
                "etiqueta": nombre,
                "text": nombre,
            }
        )
    return out


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
