"""Serializer CSV MTRIX — contrato congelado Accera V.3.5."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

HEADERS = {
    "CI": (
        "CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;CNPJ_CLIENTE;RAZAO_SOCIAL;ENDERECO;"
        "BAIRRO;CEP;CIDADE;ESTADO;NOME_RESPONSAVEL;TELEFONE;CNPJ_CLIENTE;ROTA;"
        "TIPO_LOJ;REPRESENTATIVIDADE"
    ),
    "PD": (
        "DT_ARQUIVO;CNPJ_DISTRIBUIDOR;CNPJ_FORNECEDOR;RAZAO_SOCIAL_FORNECEDOR;"
        "CODIGO_PRODUTO;TIPO_EMBALAGEM;EAN;TIPO_COD_BARRAS;DESCRICAO;DIVISAO;STATUS"
    ),
    "ES": "DT_ESTOQUE;CNPJ_FORNECEDOR;CNPJ_DISTRIBUIDOR;EAN;QTDE_TOTAL",
    "VD": (
        "CNPJ FORNECEDOR;CNPJ DISTRIBUIDOR;COD CLIENTE;DATA;NOTA_FISCAL;EAN;"
        "QTDE;PRECO;VENDEDOR;TIPO DE DOCUMENTO;CEP"
    ),
    "FV": (
        "CNPJ FORNECEDOR;CNPJ AGENTE DISTRIBUICAO;IDENTIFICACAO CLIENTE;"
        "CODIGO DO GERENTE;NOME DO GERENTE;CODIGO DO SUPERVISOR;NOME DO SUPERVISOR;"
        "CODIGO DO VENDEDOR;NOME DO VENDEDOR"
    ),
}

TIPOS_ORDEN = ("CI", "PD", "ES", "VD", "FV")
_SCI = re.compile(r"[eE]")


def sanitizar_campo(campo: Any, vacio: str = "NA") -> str:
    if campo is None:
        return vacio
    texto = str(campo).strip()
    if texto == "":
        return vacio
    texto = texto.replace(";", ",")
    texto = texto.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return texto.strip()


def ean_completo(campo: Any) -> str:
    if campo is None:
        return "0"
    texto = str(campo).strip()
    if texto == "":
        return "0"
    if _SCI.search(texto):
        try:
            return f"{int(float(texto.replace(',', '.')))}"
        except (ValueError, OverflowError):
            texto = texto
    return sanitizar_campo(texto, vacio="0")


def cnpj_cliente_mtrix(cnpj_original: Any, razon_social: Any) -> str:
    razon = str(razon_social or "").strip().upper()
    cnpj = str(cnpj_original or "").strip().replace("-", "")
    if razon == "CONSUMIDOR FINAL":
        return "99999999999"
    if cnpj in ("", "0") or (cnpj and set(cnpj) <= {"0"}):
        return "99999999999"
    return cnpj


def cnpj_fornecedor_ar(cnpj: str) -> str:
    limpio = (cnpj or "").replace("-", "").strip()
    if limpio.upper().startswith("AR"):
        return limpio
    return f"AR{limpio}"


def nombre_archivo(tipo: str, generated_at: datetime) -> str:
    stamp = generated_at.strftime("%d%m%Y%H%M%S")
    ms = f"{int(generated_at.microsecond / 1000):03d}"
    return f"{tipo}-INT{stamp}{ms}.csv"


def convertir_cantidad(valor: Any, multiplicador: int = 1) -> str:
    numero = float(valor or 0) * int(multiplicador or 1)
    if numero == int(numero):
        return str(int(numero))
    return f"{round(numero, 2):.2f}".replace(",", ".")


def convertir_precio(valor: Any, multiplicador: int = 1) -> str:
    numero = float(valor or 0) * int(multiplicador or 1)
    return f"{numero:.2f}".replace(",", ".")


def formatear_representatividade(valor: Any) -> str:
    """V.3.5 usa FORMAT de_DE (coma decimal, 2 decimales)."""
    if valor is None or str(valor).strip() == "":
        return "0,00"
    texto = str(valor).strip()
    if "," in texto and "." not in texto:
        return texto
    try:
        num = float(texto.replace(".", "").replace(",", ".")) if texto.count(".") > 1 else float(
            texto.replace(",", ".")
        )
    except ValueError:
        try:
            num = float(Decimal(str(valor)))
        except Exception:
            return "0,00"
    return f"{round(num, 2):.2f}".replace(".", ",")


def tipo_documento_vd(tipo_comp: str) -> tuple[str, bool]:
    codigo = (tipo_comp or "").strip().upper()
    if codigo in {"NC", "NCA", "NCB", "NCC", "ND", "NDA", "NDB", "NDC"}:
        return "N", True
    return "N", False


def agregar_vd(rows: Iterable[dict], multiplicador_cantidad: int = 1, multiplicador_precio: int = 1) -> list[dict]:
    agrupados: dict[str, dict] = {}
    orden: list[str] = []
    for row in rows:
        tipo_doc, es_dev = tipo_documento_vd(row.get("TIPO_COMP") or row.get("tipo_comp") or "")
        qty = float(row.get("QTDE") or row.get("qtde") or 0)
        if es_dev and qty > 0:
            qty = -qty
        precio = float(row.get("PRECO") or row.get("preco") or 0)
        # V.3.5 agrupa por COD_CLIENTE crudo (CUIT o "0"), no por el CNPJ de pantalla.
        codigo_crudo = str(row.get("COD_CLIENTE") or row.get("cod_cliente") or "")
        cnpj = cnpj_cliente_mtrix(codigo_crudo, row.get("RAZAO_SOCIAL") or row.get("razao_social"))
        ean = ean_completo(row.get("EAN") or row.get("ean"))
        data = str(row.get("DATA") or row.get("data") or "")
        nota = str(row.get("NOTA_FISCAL") or row.get("nota_fiscal") or "")
        vendedor = str(row.get("VENDEDOR") or row.get("vendedor") or "")
        cep = str(row.get("CEP") or row.get("cep") or "0")
        clave = f"{nota}|{ean}|{data}|{codigo_crudo}|{vendedor}|{tipo_doc}|{cep}"
        if clave not in agrupados:
            agrupados[clave] = {
                "COD_CLIENTE": cnpj,
                "DATA": data,
                "NOTA_FISCAL": nota,
                "EAN": ean,
                "VENDEDOR": vendedor,
                "TIPO_DOC": tipo_doc,
                "CEP": cep,
                "QTDE": qty,
                "PRECO": precio,
            }
            orden.append(clave)
        else:
            agrupados[clave]["QTDE"] += qty
            agrupados[clave]["PRECO"] += precio
    salida = []
    for clave in orden:
        item = agrupados[clave]
        item["QTDE"] = convertir_cantidad(item["QTDE"], multiplicador_cantidad)
        item["PRECO"] = convertir_precio(item["PRECO"], multiplicador_precio)
        salida.append(item)
    return salida


def _join(campos: list[str]) -> str:
    return ";".join(campos)


def serialize(tipo: str, rows: list[dict], cfg: dict, generated_at: datetime) -> tuple[str, bytes]:
    tipo = tipo.upper()
    header = HEADERS[tipo]
    fornecedor = cnpj_fornecedor_ar(cfg.get("cnpj_fornecedor") or "")
    distribuidor = (cfg.get("cnpj_distribuidor") or "").replace("-", "")
    lineas = [header]
    if tipo == "CI":
        for row in rows:
            cnpj = cnpj_cliente_mtrix(row.get("CNPJ_CLIENTE"), row.get("RAZAO_SOCIAL"))
            lineas.append(
                _join(
                    [
                        fornecedor,
                        distribuidor,
                        sanitizar_campo(cnpj),
                        sanitizar_campo(row.get("RAZAO_SOCIAL")),
                        sanitizar_campo(row.get("ENDERECO")),
                        sanitizar_campo(row.get("BAIRRO")),
                        sanitizar_campo(row.get("CEP"), vacio="0"),
                        sanitizar_campo(row.get("CIDADE") or row.get("CIUDAD")),
                        sanitizar_campo(row.get("ESTADO")),
                        sanitizar_campo(row.get("NOME_RESPONSAVEL")),
                        sanitizar_campo(row.get("TELEFONE"), vacio="NA"),
                        sanitizar_campo(cnpj),
                        sanitizar_campo(row.get("ROTA") or "RUTA"),
                        sanitizar_campo(row.get("TIPO_LOJ") or "Tienda"),
                        formatear_representatividade(row.get("REPRESENTATIVIDADE")),
                    ]
                )
            )
    elif tipo == "PD":
        fecha = str(cfg.get("fecha_archivo") or "")
        razon = sanitizar_campo(cfg.get("razon_social_fornecedor") or "DISTRIBUIDOR")
        for row in rows:
            disc = str(row.get("DISCONTINUO") or "No").strip().upper()
            status = "I" if disc == "SI" else "A"
            marca = (row.get("DIVISAO_MARCA") or "").strip()
            rubro = (row.get("DIVISAO_RUBRO") or "").strip()
            division = marca or rubro or "OTROS PRODUCTOS"
            lineas.append(
                _join(
                    [
                        fecha,
                        distribuidor,
                        fornecedor,
                        razon,
                        sanitizar_campo(row.get("CODIGO_PRODUTO")),
                        sanitizar_campo(row.get("TIPO_EMBALAGEM") or "0"),
                        ean_completo(row.get("EAN")),
                        sanitizar_campo(row.get("TIPO_COD_BARRAS") or "1"),
                        sanitizar_campo(row.get("DESCRICAO")),
                        sanitizar_campo(division),
                        status,
                    ]
                )
            )
    elif tipo == "ES":
        fecha = str(cfg.get("fecha_archivo") or "")
        mult = int(cfg.get("multiplicador_cantidad") or 1)
        for row in rows:
            lineas.append(
                _join(
                    [
                        fecha,
                        fornecedor,
                        distribuidor,
                        ean_completo(row.get("EAN")),
                        convertir_cantidad(row.get("QTDE_TOTAL"), mult),
                    ]
                )
            )
    elif tipo == "VD":
        agrupados = agregar_vd(
            rows,
            int(cfg.get("multiplicador_cantidad") or 1),
            int(cfg.get("multiplicador_precio") or 1),
        )
        for row in agrupados:
            lineas.append(
                _join(
                    [
                        fornecedor,
                        distribuidor,
                        sanitizar_campo(row["COD_CLIENTE"]),
                        sanitizar_campo(row["DATA"]),
                        sanitizar_campo(row["NOTA_FISCAL"]),
                        ean_completo(row["EAN"]),
                        row["QTDE"],
                        row["PRECO"],
                        sanitizar_campo(row["VENDEDOR"]),
                        sanitizar_campo(row["TIPO_DOC"]),
                        sanitizar_campo(row["CEP"], vacio="0"),
                    ]
                )
            )
    elif tipo == "FV":
        for row in rows:
            # V.3.5 escribe CNPJ_CLIENTE crudo; no aplica ObtenerCNPJClienteMTRIX.
            lineas.append(
                _join(
                    [
                        fornecedor,
                        distribuidor,
                        sanitizar_campo(row.get("CNPJ_CLIENTE")),
                        sanitizar_campo(row.get("COD_GERENTE") or "1"),
                        sanitizar_campo(row.get("NOME_GERENTE") or "GERENTE GENERAL"),
                        sanitizar_campo(row.get("COD_SUPERVISOR") or "1"),
                        sanitizar_campo(row.get("NOME_SUPERVISOR") or "SUPERVISOR"),
                        sanitizar_campo(row.get("COD_VENDEDOR")),
                        sanitizar_campo(row.get("NOME_VENDEDOR")),
                    ]
                )
            )
    else:
        raise ValueError(f"Tipo MTRIX desconocido: {tipo}")
    cuerpo = "\r\n".join(lineas) + "\r\n"
    return nombre_archivo(tipo, generated_at), cuerpo.encode("latin-1", errors="replace")
