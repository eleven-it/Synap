"""Transformación fila AdministraNET → payload Odoo."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none

from odoo_migracion.services.external_id import ref_adminet


def _adminet_id(row: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        if row.get(k) is not None:
            return str(row[k])
    return ""


def map_empresa(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "id_empresa")
    vals = {
        "name": str_or_default(row.get("Nombre"), "-"),
        "vat": str_or_default(row.get("CUIT"), "").replace("-", ""),
        "street": str_or_default(row.get("Domicilio"), "-"),
        "phone": str_or_default(row.get("Telefono"), "-"),
        "email": str_or_default(row.get("Email"), False) or False,
        "ref": ref_adminet("empresa", aid),
    }
    return aid, vals


def map_uom(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "id_unimed")
    name = str_or_default(row.get("nombre_unimed"), f"UoM {aid}")
    vals = {
        "name": name,
        "ref": ref_adminet("uom", aid),
    }
    return aid, vals


def map_rubro(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "CodigoRubro")
    vals = {
        "name": str_or_default(row.get("NombreRubro"), f"Rubro {aid}"),
        "ref": ref_adminet("rubro", aid),
    }
    return aid, vals


def map_subrubro(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "IDSubRubro")
    vals = {
        "name": str_or_default(row.get("NombreSubRubro"), f"Subrubro {aid}"),
        "ref": ref_adminet("subrubro", aid),
        "_parent_rubro_id": str(to_int_or_none(row.get("CodigoRubro")) or ""),
    }
    return aid, vals


def map_marca(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "CodMarca")
    vals = {
        "name": str_or_default(row.get("NombreMarca"), f"Marca {aid}"),
        "code": aid,
        "active": (row.get("anulado") or "No") == "No",
        "ref": ref_adminet("marca", aid),
    }
    return aid, vals


def map_viajante(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "CodViajante")
    vals = {
        "name": str_or_default(row.get("Nombre"), f"Vendedor {aid}"),
        "ref": ref_adminet("viajante", aid),
        "comment": "Migrado desde viajantes AdministraNET",
        "employee": False,
    }
    return aid, vals


def map_deposito(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "id_deposito")
    vals = {
        "name": str_or_default(row.get("nombre_deposito"), f"Depósito {aid}"),
        "code": f"DEP{aid}",
        "ref": ref_adminet("deposito", aid),
    }
    return aid, vals


def _partner_common(row: Dict[str, Any], entity: str, id_key: str, name_key: str) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, id_key)
    name = str_or_default(row.get(name_key), f"{entity} {aid}")
    vat = str_or_default(row.get("CUIT"), "").replace("-", "")
    vals: Dict[str, Any] = {
        "name": name,
        "ref": ref_adminet(entity, aid),
        "street": str_or_default(row.get("Calle"), "-"),
        "phone": str_or_default(row.get("telefono") or row.get("TelefonoParticular"), "-"),
        "email": str_or_default(row.get("Email"), False) or False,
        "comment": f"Migrado AdministraNET {entity} {aid}",
    }
    if vat:
        vals["vat"] = vat
    return aid, vals


def map_proveedor(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid, vals = _partner_common(row, "proveedor", "Codigo", "Nombre")
    vals["supplier_rank"] = 1
    return aid, vals


def map_cliente(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid, vals = _partner_common(row, "cliente", "Codigo", "nombre_cliente")
    vals["customer_rank"] = 1
    cv = to_int_or_none(row.get("CodViajante"))
    if cv:
        vals["_viajante_adminet_id"] = str(cv)
    return aid, vals


def map_articulo(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "IDArt")
    name = str_or_default(row.get("NombreArticulo"), f"Artículo {aid}")
    default_code = str_or_default(row.get("CodigoArticulo") or row.get("id_manual"), aid)
    cost = to_decimal_or_none(row.get("PrecioCosto"))
    price = to_decimal_or_none(row.get("Precio1V"))
    vals: Dict[str, Any] = {
        "name": name,
        "default_code": default_code,
        "ref": ref_adminet("articulo", aid),
        "list_price": float(price) if price is not None else 0.0,
        "standard_price": float(cost) if cost is not None else 0.0,
        "sale_ok": True,
        "purchase_ok": True,
        "active": (row.get("Discontinuo") or "No") == "No",
        "_rubro_adminet_id": str(to_int_or_none(row.get("CodigoRubro")) or ""),
        "_subrubro_adminet_id": str(to_int_or_none(row.get("IDSubRubro")) or ""),
        "_marca_adminet_id": str(to_int_or_none(row.get("CodigoMarca")) or ""),
        "_uom_adminet_id": str(to_int_or_none(row.get("id_unimed")) or ""),
    }
    return aid, vals


def map_stock_saldo(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "id_stock_deposito")
    qty = to_decimal_or_none(row.get("saldo")) or 0
    vals = {
        "ref": ref_adminet("stock_saldo", aid),
        "_articulo_adminet_id": str(to_int_or_none(row.get("id_articulo")) or ""),
        "_deposito_adminet_id": str(to_int_or_none(row.get("id_deposito")) or ""),
        "quantity": float(qty),
    }
    return aid, vals


def map_cuenta_cliente(row: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    aid = _adminet_id(row, "id_cuentacliente")
    tipo = str_or_default(row.get("TipoComprobante"), "FA")
    nro = str_or_default(row.get("NroComprobante"), "")
    saldo = to_decimal_or_none(row.get("saldo")) or 0
    move_type = "out_invoice" if tipo in ("FA", "FB", "FC") else "out_refund"
    vals = {
        "ref": ref_adminet("cuenta_cliente", aid),
        "name": f"{tipo}-{nro}",
        "move_type": move_type,
        "_cliente_adminet_id": str(to_int_or_none(row.get("Codigo")) or ""),
        "amount_residual": float(saldo),
        "invoice_date": row.get("Fecha"),
        "_historico_sin_cae": True,
        "narration": "Migrado histórico AdministraNET — sin re-emisión CAE",
    }
    return aid, vals
