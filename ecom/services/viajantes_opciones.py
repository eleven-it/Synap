"""
Opciones de combo «Vendedor / Viajante» para pantallas mayoristapp (paridad PHP ``lista-*-vendedor``).

``id_puesto == 1``: puede listar todos los viajantes y opción «Todos».
En caso contrario: solo el viajante de la sesión (como ``$codPuesto!=1`` en PHP).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario


def opciones_viajantes_para_filtro(base_empresa: str, sess_user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve ``opciones`` (lista de dicts valor/texto), ``valor_por_defecto`` y ``mostrar_opcion_todos``.
    """
    id_puesto = to_int_or_none(sess_user.get("id_puesto"))
    cv_ses = cod_viajante_desde_sesion_usuario(sess_user)
    # Paridad PHP: puesto 1 = acceso a todos los viajantes (supervisor de listados).
    mostrar_todos = id_puesto == 1

    pool = get_mysql_pool()
    where = ["viajantes.Anulado = %s"]
    params: List[Any] = ["No"]
    if not mostrar_todos and cv_ses is not None:
        where.append("viajantes.CodViajante = %s")
        params.append(cv_ses)

    sql = f"""
        SELECT
            viajantes.CodViajante AS valor,
            CONCAT(viajantes.Nombre, ' (cod:', viajantes.CodViajante, ')') AS texto
        FROM viajantes
        WHERE {' AND '.join(where)}
        ORDER BY texto ASC
    """

    rows: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            rows.append(dict(zip(cols, row)))

    opciones: List[Dict[str, Any]] = []
    if mostrar_todos:
        opciones.append({"valor": "todos", "texto": "- Todos -"})

    for r in rows:
        v = r.get("valor")
        t = r.get("texto")
        if v is not None:
            opciones.append({"valor": str(int(v)) if isinstance(v, (int, float)) else str(v), "texto": str(t or "")})

    if mostrar_todos:
        valor_default = "todos"
    elif opciones:
        valor_default = opciones[0]["valor"]
    elif cv_ses is not None:
        valor_default = str(cv_ses)
    else:
        valor_default = "todos"

    if not opciones and cv_ses is not None:
        opciones.append(
            {
                "valor": str(int(cv_ses)),
                "texto": "Vendedor asignado (cod: {})".format(int(cv_ses)),
            }
        )

    return {
        "opciones": opciones,
        "valor_por_defecto": valor_default,
        "mostrar_opcion_todos": mostrar_todos,
    }
