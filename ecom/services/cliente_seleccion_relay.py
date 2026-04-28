"""
Selección de cliente en sesión (paridad ``selecciona_cliente`` en ``relay-cliente-rapido.php``).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def construir_payload_cliente_seleccionado(
    base_empresa: str,
    codigo_cliente: int,
    cod_viajante_sesion: Optional[int],
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], List[Dict[str, Any]], str]:
    """
    Retorna ``(cliente_datos, autoriza_credito, domicilios, iva_incluido)``.

    ``autoriza_credito`` coincide con PHP: vacío si no hay fecha de atraso aplicable.
    """
    pool = get_mysql_pool()
    cv = cod_viajante_sesion
    sql_cli = """
        SELECT
            cliente.nombre_cliente AS cliente,
            cliente.id_cv AS id_cv,
            cond_venta.Descripcion AS condVenta,
            cliente.ListaPrecio AS listaPrecio,
            SUBSTRING(cliente.ListaPrecio, 6) AS codListaPrecio,
            cliente.Credito AS Credito,
            cliente.credito_limite_dias AS credito_limite_dias,
            cliente.id_sucursal AS id_sucursal,
            cliente.saldo AS saldo,
            cliente.Codigo AS Codigo,
            cliente.TipoCliente AS TipoCliente,
            cliente.Descuento AS descPie,
            cliente.Email AS email,
            cliente.EmailContacto AS emailcontacto,
            cliente.descuento_por_cli AS descRenglon,
            cond_venta.descuento AS descCondventa,
            contribuyentes.IDIva AS IDIva,
            contribuyentes.Abreviado AS abreviado
        FROM cliente
        LEFT JOIN cond_venta ON cond_venta.Codigo = cliente.id_cv
        LEFT JOIN contribuyentes ON contribuyentes.IDIva = cliente.IDIva
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    cliente_row: Optional[Dict[str, Any]] = None
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_cli, [codigo_cliente])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        if row:
            cliente_row = _json_safe(dict(zip(cols, row)))
    if not cliente_row:
        return None, {}, [], "no"

    if cv is not None:
        cliente_row["codViajante"] = cv

    autoriza: Dict[str, Any] = {}
    sql_atraso = """
        SELECT MIN(cuentacliente.Fecha) AS ultimaf
        FROM cuentacliente
        WHERE (cuentacliente.TipoComprobante IN (
            'FA','FB','FC','FE','FM','NDA','NDC','NDE','NDM','NDB'
        ))
          AND cuentacliente.Estado = 'N/Canc'
          AND cuentacliente.Anulado = 'No'
          AND cuentacliente.Codigo = %s
    """
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_atraso, [codigo_cliente])
        r = cursor.fetchone()
        ultimaf = r[0] if r else None
        limite = to_int_or_none(cliente_row.get("credito_limite_dias")) or 0

        if ultimaf and str(ultimaf).strip():
            try:
                if isinstance(ultimaf, datetime):
                    d2 = ultimaf.date()
                elif isinstance(ultimaf, date):
                    d2 = ultimaf
                else:
                    d2 = datetime.strptime(str(ultimaf)[:10], "%Y-%m-%d").date()
                d1 = date.today()
                intervalo = abs((d1 - d2).days)
                if limite != 0 and intervalo > limite:
                    autoriza = {
                        "limite_credito_dias": "No autorizado",
                        "dias_exceso_limite": intervalo,
                        "exceso": 1,
                    }
                else:
                    autoriza = {
                        "limite_credito_dias": "Autorizado",
                        "dias_exceso_limite": 0,
                        "exceso": 0,
                    }
            except Exception:
                autoriza = {}
        # Sin ``ultimaf`` PHP deja ``autorizaCredito`` vacío.

    id_iva = to_int_or_none(cliente_row.get("IDIva"))
    iva_incluido = "no" if id_iva == 1 else "si"

    sql_dom = """
        SELECT
            cm.id_cliente_domicilio AS idDom,
            cm.Calle AS Calle,
            cm.NroCalle AS NroCalle,
            cm.Dpto AS Dpto,
            pv.Provincia AS Provincia,
            dp.NombreDepartamento AS NombreDepartamento,
            dt.NombreDistrito AS NombreDistrito,
            z.nombre_zona AS nombre_zona,
            z.id_zona AS id_zona
        FROM cliente_domicilio AS cm
        LEFT JOIN provincia AS pv ON pv.CodProvincia = cm.CodProvincia
        LEFT JOIN departamento AS dp ON dp.IDDepartamento = cm.IDDepartamento
        LEFT JOIN distrito AS dt ON dt.IDDistrito = cm.IDDistrito
        LEFT JOIN erp_zona AS z ON z.id_zona = cm.id_zona
        WHERE cm.id_cliente = %s
          AND cm.anulado = 'No'
    """
    domicilios: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql_dom, [codigo_cliente])
        cols_d = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            domicilios.append(_json_safe(dict(zip(cols_d, row))))

    return cliente_row, autoriza, domicilios, iva_incluido


def _json_safe(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if isinstance(v, date) else v.isoformat()
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item
