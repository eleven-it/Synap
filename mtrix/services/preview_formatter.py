"""Formato de pantalla para preview Mtrix (no altera el CSV)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mtrix.services.csv_serializer import cnpj_cliente_mtrix, ean_completo


def _fecha_pantalla(valor: Any) -> str:
    texto = str(valor or "").strip()
    if len(texto) == 8 and texto.isdigit():
        return f"{texto[6:8]}/{texto[4:6]}/{texto[0:4]}"
    if len(texto) == 10 and texto[4] == "-" and texto[7] == "-":
        try:
            dt = datetime.strptime(texto, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return texto
    return texto


def format_row(tipo: str, row: dict) -> dict:
    tipo = (tipo or "").upper()
    salida = dict(row)
    if tipo == "CI":
        salida["CNPJ_CLIENTE"] = cnpj_cliente_mtrix(row.get("CNPJ_CLIENTE"), row.get("RAZAO_SOCIAL"))
        salida["CIDADE"] = row.get("CIDADE") or row.get("CIUDAD")
    elif tipo == "VD":
        salida["COD_CLIENTE"] = cnpj_cliente_mtrix(
            row.get("COD_CLIENTE") or row.get("CNPJ_CLIENTE"),
            row.get("RAZAO_SOCIAL"),
        )
        salida["DATA"] = _fecha_pantalla(row.get("DATA"))
        salida["EAN"] = ean_completo(row.get("EAN"))
    elif tipo in {"PD", "ES"}:
        salida["EAN"] = ean_completo(row.get("EAN"))
        if tipo == "PD":
            salida["DT_ARQUIVO"] = _fecha_pantalla(row.get("DT_ARQUIVO") or row.get("DATA"))
        if tipo == "ES":
            salida["DT_ESTOQUE"] = _fecha_pantalla(row.get("DT_ESTOQUE") or row.get("DATA"))
    elif tipo == "FV":
        # V.3.5 exporta el CUIT crudo; el preview no lo reemplaza por 99999999999.
        salida.setdefault("COD_GERENTE", "1")
        salida.setdefault("NOME_GERENTE", "GERENTE GENERAL")
        salida.setdefault("COD_SUPERVISOR", "1")
        salida.setdefault("NOME_SUPERVISOR", "SUPERVISOR")
    return salida
