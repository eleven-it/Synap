"""
Alta y edición de cliente rápido (paridad ``alta_cliente`` / ``edita_cliente`` / ``valida_cliente_existe`` en ``relay-cliente-rapido.php``).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario


def _si_no(val: Any, default: str = "No") -> str:
    if val is None:
        return default
    s = str(val).strip().lower()
    if s in ("si", "sí", "yes", "1", "true"):
        return "Si"
    return "No"


def trae_cuenta_contable_defecto(base_empresa: str) -> Optional[float]:
    sql = "SELECT id_pc FROM cont_paramatriz WHERE id_paramatriz = 1 LIMIT 1"
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        try:
            return float(row[0])
        except (TypeError, ValueError):
            return None


def valida_cliente_existe(
    base_empresa: str,
    tipo_doc: str,
    nombre_c: str,
    cuit_c: str,
    dni_c: str,
    id_cliente: Optional[int] = None,
) -> List[str]:
    """
    Misma lógica que PHP: duplicado por nombre o documento (mismo ``tipo_doc``),
    excluyendo filas con CUIT genérico; opcionalmente excluye ``Codigo`` al editar.
    """
    tipo_doc_c = str_or_default(tipo_doc, "CUIT")
    nombre_c = str_or_default(nombre_c, "-")
    doc_valido = str_or_default(cuit_c if tipo_doc_c == "CUIT" else dni_c, "-")

    params: List[Any] = []
    where_cod = ""
    if id_cliente is not None:
        where_cod = "cliente.Codigo <> %s AND "
        params.append(id_cliente)

    sql = f"""
        SELECT cliente.Codigo, cliente.nombre_cliente, cliente.CUIT
        FROM cliente
        WHERE {where_cod}
            cliente.CUIT <> '00-00000000-0'
            AND cliente.CUIT <> 0
            AND cliente.tipo_doc = %s
            AND (cliente.nombre_cliente = %s OR cliente.CUIT = %s)
    """
    params.extend([tipo_doc_c, nombre_c, doc_valido])

    err_nombre = 0
    err_cuit = 0
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            cc_nombre = row[1]
            cc_cuit = row[2]
            if nombre_c == cc_nombre:
                err_nombre += 1
            if doc_valido == cc_cuit:
                err_cuit += 1

    texto: List[str] = []
    if err_cuit != 0:
        texto.append("El Cuit - Dni ingresado ya existe en el sistema")
    if err_nombre != 0:
        texto.append("El nombre del cliente ya se encuentrea en el sistema")
    return texto


def alta_cliente_rapido(
    base_empresa: str,
    p: Dict[str, Any],
    sess_user: Dict[str, Any],
) -> Union[int, Dict[str, Any]]:
    """
    INSERT ``cliente`` + primer ``cliente_domicilio`` (``id_zona=1`` como PHP).
    Retorna ``codigo`` nuevo o ``dict`` con ``estado`` / ``cartel`` en error de validación.
    """
    tipo_doc_c = str_or_default(p.get("tipoDocCliente"), "CUIT")
    nombre_c = str_or_default(p.get("nombreCliente"), "-")
    cuit_c = str_or_default(p.get("nroCuitCliente"), "")
    dni_c = str_or_default(p.get("nroDocCliente"), "")
    err = valida_cliente_existe(base_empresa, tipo_doc_c, nombre_c, cuit_c, dni_c, None)
    if err:
        return {"estado": "error", "cartel": " | ".join(err)}

    docu = str_or_default(cuit_c if tipo_doc_c == "CUIT" else dni_c, "-")
    id_pc = trae_cuenta_contable_defecto(base_empresa)
    if id_pc is None:
        id_pc = 13.0

    lista_precio = str_or_default(p.get("listaPrecio"), "Lista 1")
    cod_viajante = cod_viajante_desde_sesion_usuario(sess_user) or 1
    id_sucursal = to_int_or_none(sess_user.get("id_sucursal")) or 1
    id_iva = to_int_or_none(p.get("ivaCliente")) or 1
    tipo_cli = to_int_or_none(p.get("tipoCliente")) or 1

    sql_ins = """
        INSERT INTO cliente (
            TipoCliente, nombre_cliente, Descuento, Credito, CodViajante,
            CUIT, tipo_doc, IDIva, Estado, ListaPrecio, id_cv, id_sucursal,
            telefono, Fax, Email, Calle, NroCalle, Dpto, CodProvincia,
            IDDepartamento, IDDistrito, id_pc
        ) VALUES (
            %s, %s, 0, 0, %s,
            %s, %s, %s, 'Activo', %s, 1, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
    """
    params_ins: List[Any] = [
        tipo_cli,
        nombre_c,
        cod_viajante,
        docu,
        tipo_doc_c,
        id_iva,
        lista_precio,
        id_sucursal,
        str_or_default(p.get("telefonoCliente"), "-"),
        str_or_default(p.get("faxCliente"), "-"),
        str_or_default(p.get("emailCliente"), "-"),
        str_or_default(p.get("calleCliente"), "-"),
        str_or_default(p.get("numeroCliente"), "-"),
        str_or_default(p.get("deptoCliente"), "-"),
        to_int_or_none(p.get("provinciaCliente")) or 1,
        to_int_or_none(p.get("departamentoCliente")) or 1,
        to_int_or_none(p.get("distritoCliente")) or 1,
        id_pc,
    ]

    pool = get_mysql_pool()
    nuevo_cod: int = 0
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_ins, params_ins)
        nuevo_cod = int(cursor.lastrowid)

        sql_dom = """
            INSERT INTO cliente_domicilio (
                Calle, NroCalle, Dpto, IDDistrito, CodProvincia, IDDepartamento,
                id_zona, id_cliente, anulado
            ) VALUES (%s, %s, %s, %s, %s, %s, 1, %s, 'No')
        """
        cursor.execute(
            sql_dom,
            [
                str_or_default(p.get("calleCliente"), "-"),
                str_or_default(p.get("numeroCliente"), "-"),
                str_or_default(p.get("deptoCliente"), "-"),
                to_int_or_none(p.get("distritoCliente")) or 1,
                to_int_or_none(p.get("provinciaCliente")) or 1,
                to_int_or_none(p.get("departamentoCliente")) or 1,
                float(nuevo_cod),
            ],
        )

    return nuevo_cod


def edita_cliente_rapido(
    base_empresa: str,
    p: Dict[str, Any],
    sess_user: Dict[str, Any],
) -> Union[int, Dict[str, Any]]:
    """
    UPDATE ``cliente``. Con ``permiso_alta_cliente`` = Si (PHP) actualiza documentos;
    si no, solo contacto y domicilio fiscal básico.
    """
    id_cli = to_int_or_none(p.get("codCliente"))
    if id_cli is None:
        return {"estado": "error", "cartel": "codCliente inválido"}

    permiso = _si_no(sess_user.get("permiso_alta_cliente"), "No")
    tipo_doc_c = str_or_default(p.get("tipoDocCliente"), "CUIT")
    nombre_c = str_or_default(p.get("nombreCliente"), "-")
    cuit_c = str_or_default(p.get("nroCuitCliente"), "")
    dni_c = str_or_default(p.get("nroDocCliente"), "")

    if permiso == "Si":
        err = valida_cliente_existe(base_empresa, tipo_doc_c, nombre_c, cuit_c, dni_c, id_cli)
        if err:
            return {"estado": "error", "cartel": " | ".join(err)}
        docu = str_or_default(cuit_c if tipo_doc_c == "CUIT" else dni_c, "-")
        id_iva = to_int_or_none(p.get("ivaCliente")) or 1
        tipo_cli = to_int_or_none(p.get("tipoCliente")) or 1
        sql = """
            UPDATE cliente SET
                TipoCliente = %s,
                nombre_cliente = %s,
                CUIT = %s,
                tipo_doc = %s,
                IDIva = %s,
                telefono = %s,
                Fax = %s,
                Email = %s,
                Calle = %s,
                NroCalle = %s,
                Dpto = %s,
                CodProvincia = %s,
                IDDepartamento = %s,
                IDDistrito = %s
            WHERE cliente.Codigo = %s
        """
        params = [
            tipo_cli,
            nombre_c,
            docu,
            tipo_doc_c,
            id_iva,
            str_or_default(p.get("telefonoCliente"), "-"),
            str_or_default(p.get("faxCliente"), "-"),
            str_or_default(p.get("emailCliente"), "-"),
            str_or_default(p.get("calleCliente"), "-"),
            str_or_default(p.get("numeroCliente"), "-"),
            str_or_default(p.get("deptoCliente"), "-"),
            to_int_or_none(p.get("provinciaCliente")) or 1,
            to_int_or_none(p.get("departamentoCliente")) or 1,
            to_int_or_none(p.get("distritoCliente")) or 1,
            id_cli,
        ]
    else:
        sql = """
            UPDATE cliente SET
                telefono = %s,
                Email = %s,
                Calle = %s,
                NroCalle = %s,
                Dpto = %s,
                CodProvincia = %s,
                IDDepartamento = %s,
                IDDistrito = %s
            WHERE cliente.Codigo = %s
        """
        params = [
            str_or_default(p.get("telefonoCliente"), "-"),
            str_or_default(p.get("emailCliente"), "-"),
            str_or_default(p.get("calleCliente"), "-"),
            str_or_default(p.get("numeroCliente"), "-"),
            str_or_default(p.get("deptoCliente"), "-"),
            to_int_or_none(p.get("provinciaCliente")) or 1,
            to_int_or_none(p.get("departamentoCliente")) or 1,
            to_int_or_none(p.get("distritoCliente")) or 1,
            id_cli,
        ]

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)

    return id_cli


def actualizar_cliente_rapido_json(base_empresa: str, sess_user: Dict[str, Any]) -> str:
    """
    Paridad ``actualizar_cliente_rapido``: lista JSON para desplegable (misma SQL que PHP).
    """
    todos = _si_no(sess_user.get("todos_clientes"), "No")
    usa_manual = _si_no(sess_user.get("usa_id_manual"), "No")
    cv = cod_viajante_desde_sesion_usuario(sess_user)
    if cv is None:
        cv = 1

    where_c = ""
    params: List[Any] = []
    if todos == "No":
        where_c = " AND cliente.CodViajante = %s "
        params.append(cv)

    if usa_manual == "Si":
        campo_id = "COALESCE(cliente.id_manual_cli, cliente.Codigo)"
    else:
        campo_id = "cliente.Codigo"

    sql = f"""
        SELECT
            {campo_id} AS codigo,
            CONCAT(LTRIM(cliente.nombre_cliente), ' Cod: ', {campo_id}) AS nombre,
            cliente.Codigo AS id
        FROM cliente
        WHERE cliente.Codigo <> 1
          AND cliente.Estado = 'Activo'
          {where_c}
        ORDER BY cliente.nombre_cliente
    """
    pool = get_mysql_pool()
    filas: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            filas.append(dict(zip(cols, row)))
    return json.dumps(filas, ensure_ascii=False)
