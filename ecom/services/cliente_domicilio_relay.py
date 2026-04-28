"""
Domicilios de cliente (paridad ``relay-cliente-domicilio.php``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_int_or_none


def id_cliente_de_domicilio(base_empresa: str, id_domicilio: int) -> Optional[int]:
    """``id_cliente`` de la fila (para permisos)."""
    pool = get_mysql_pool()
    sql = "SELECT id_cliente FROM cliente_domicilio WHERE id_cliente_domicilio = %s LIMIT 1"
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [id_domicilio])
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None
        try:
            return int(float(row[0]))
        except (TypeError, ValueError):
            return None


def trae_domicilio_completo(
    base_empresa: str, id_domicilio: int
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    sql = """
        SELECT
            cd.id_cliente_domicilio,
            cd.Calle,
            cd.NroCalle,
            cd.Dpto,
            cd.IDDistrito,
            di.NombreDistrito,
            cd.CodProvincia,
            p.Provincia,
            cd.IDDepartamento,
            d.NombreDepartamento,
            cd.id_zona,
            z.nombre_zona,
            cd.id_cliente,
            cd.anulado,
            cd.diasContacto,
            cd.id_pais,
            COALESCE(cd.hora_desde, '00:00:00') AS hora_desde,
            COALESCE(cd.hora_hasta, '00:00:00') AS hora_hasta,
            cd.periodicidad_visita_vendedor,
            cd.visita_vendedor_valor
        FROM cliente_domicilio AS cd
        LEFT JOIN provincia AS p ON p.CodProvincia = cd.CodProvincia
        LEFT JOIN departamento AS d ON d.IDDepartamento = cd.IDDepartamento
        LEFT JOIN distrito AS di ON di.IDDistrito = cd.IDDistrito
        LEFT JOIN erp_zona AS z ON z.id_zona = cd.id_zona
        WHERE cd.id_cliente_domicilio = %s
          AND cd.anulado = 'No'
        LIMIT 1
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [id_domicilio])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        if not row:
            return None, "domicilio_no_encontrado"
        return _json_safe(dict(zip(cols, row))), None


def alta_domicilio_relay(base_empresa: str, p: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    h_desde = f"{str_or_default(p.get('horaDesde'), '00')}:{str_or_default(p.get('minutoDesde'), '00')}:00"
    h_hasta = f"{str_or_default(p.get('horaHasta'), '00')}:{str_or_default(p.get('minutoHasta'), '00')}:00"
    id_cli = p.get("idCliente")
    try:
        id_cliente = float(id_cli) if id_cli is not None else None
    except (TypeError, ValueError):
        id_cliente = None
    if id_cliente is None:
        return {}, "id_cliente_invalido"

    sql = """
        INSERT INTO cliente_domicilio (
            Calle, NroCalle, Dpto, IDDistrito, CodProvincia, IDDepartamento,
            id_zona, id_cliente, hora_desde, hora_hasta,
            periodicidad_visita_vendedor, visita_vendedor_valor, anulado
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'No'
        )
    """
    params = [
        str_or_default(p.get("calleCliente"), "-"),
        str_or_default(p.get("numeroCliente"), "-"),
        str_or_default(p.get("deptoCliente"), "-"),
        to_int_or_none(p.get("distritoCliente")),
        to_int_or_none(p.get("provinciaCliente")),
        to_int_or_none(p.get("departamentoCliente")),
        to_int_or_none(p.get("zonaCliente")),
        id_cliente,
        h_desde,
        h_hasta,
        str_or_default(p.get("visitaVendedor"), "No"),
        str_or_default(p.get("intervaloVisita"), "No"),
    ]
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
    return {"estado": "ok", "cartel": "Domicilio Agregado"}, None


def edita_domicilio_relay(base_empresa: str, p: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    id_dom = to_int_or_none(p.get("idClienteDom"))
    if id_dom is None:
        return {}, "id_domicilio_invalido"
    h_desde = f"{str_or_default(p.get('horaDesdeEd'), '00')}:{str_or_default(p.get('minutoDesdeEd'), '00')}:00"
    h_hasta = f"{str_or_default(p.get('horaHastaEd'), '00')}:{str_or_default(p.get('minutoHastaEd'), '00')}:00"
    sql = """
        UPDATE cliente_domicilio SET
            Calle = %s,
            NroCalle = %s,
            Dpto = %s,
            IDDistrito = %s,
            CodProvincia = %s,
            IDDepartamento = %s,
            id_zona = %s,
            hora_desde = %s,
            hora_hasta = %s,
            periodicidad_visita_vendedor = %s,
            visita_vendedor_valor = %s
        WHERE id_cliente_domicilio = %s
    """
    params = [
        str_or_default(p.get("calleClienteEd"), "-"),
        str_or_default(p.get("numeroClienteEd"), "-"),
        str_or_default(p.get("deptoClienteEd"), "-"),
        to_int_or_none(p.get("distritoClienteEd")),
        to_int_or_none(p.get("provinciaClienteEd")),
        to_int_or_none(p.get("departamentoClienteEd")),
        to_int_or_none(p.get("zonaClienteEd")),
        h_desde,
        h_hasta,
        str_or_default(p.get("visitaVendedorEd"), "No"),
        str_or_default(p.get("intervaloVisitaEd"), "No"),
        id_dom,
    ]
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
    return {"estado": "ok", "cartel": "Domicilio Editado"}, None


def trae_opciones_visita(tipo_visita: str) -> Dict[str, Any]:
    """Paridad ``trae_opciones_visita`` (JSON)."""
    tv = (tipo_visita or "").strip()
    vuelta: Dict[str, Any] = {"msg": "ok"}
    if tv == "No":
        vuelta["titulo"] = "Cuando: "
        vuelta["opc"] = ["No"]
    elif tv == "Semanal":
        vuelta["titulo"] = "Dia: "
        vuelta["opc"] = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]
    elif tv == "Quincenal":
        vuelta["titulo"] = "Periodo: "
        vuelta["opc"] = ["01-15", "15-30"]
    elif tv == "Mensual":
        vuelta["titulo"] = "Dia: "
        vuelta["opc"] = [str(i) for i in range(1, 32)]
    else:
        vuelta["titulo"] = ""
        vuelta["opc"] = []
    return vuelta


def _json_safe(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item
