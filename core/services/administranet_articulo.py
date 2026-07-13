"""
Alta de artículos en MySQL AdministraNET (paridad mínima con CargaArticulo.frm).

No es el ABM completo VB6: cubre INSERT en `articulo` + filas `stock_deposito`
(saldo 0) por depósito, con secuencia CodigoArticulo por rubro/subrubro,
barra CODE128, IDSubRubro, UM y bulto.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)

# Defaults alineados a Terminado usable en MPR (pares).
_DEFAULTS_ALTA = {
    "CodigoRubro": 1,
    "CodigoSubRubro": 1,
    "CodigoSubRubroT": "1.1",
    "IDSubRubro": 1,
    "Alicuota": 1,
    "AlicuotaIB": 2,
    "TipoIVA": "Gravado",
    "TipoIB": "Gravado",
    "Discontinuo": "No",
    "Moneda": "Pesos",
    "tipo_art": "Articulo",
    "tipo_art_fab": "Terminado",
    "ensamblado": "No",
    "disponible_vta": "Si",
    "disponible_comp": "Si",
    "ecommerce": "No",
    "id_unimed": 1,  # Unidad (pares) — no heredar P2/P3 de plantillas raras
    "CodigoModelo": 1,
    "CodigoProveedor": 1,
    "PrecioCosto": 0,
    "Precio1V": 0,
    "Precio2V": 0,
    "Precio3V": 0,
    "Precio4V": 0,
    "Precio5V": 0,
    "saldo_articulo": 0,
    "cantidad_promedio_bulto": 12,
    "Simbologia": "CODE128",
    "SimbologiaF": "CODE128",
}

# Prefijo MMID / nombre BEST → CodMarca Admin (tabla marca.NombreMarca).
_MARCA_ALIAS = {
    "AT": "AT",
    "ATOMIK": "AT",
    "LE": "LEV",
    "LEV": "LEV",
    "LEVIS": "LEV",
    "PU": "PUM",
    "PUM": "PUM",
    "PUMA": "PUM",
    "HD": "HD",
    "HEAD": "HD",
    "REE": "REE",
    "REEBOK": "REE",
}


def _plantilla_defaults(base_empresa: str) -> dict[str, Any]:
    """Rubro/IVA/moneda de un Terminado reciente; UM/marca no se heredan a ciegas."""
    out = dict(_DEFAULTS_ALTA)
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cur:
            cur.execute(
                """
                SELECT CodigoRubro, CodigoSubRubro, CodigoSubRubroT, IDSubRubro,
                       Alicuota, AlicuotaIB, TipoIVA, TipoIB, Moneda, tipo_art,
                       CodigoModelo, CodigoProveedor
                FROM articulo
                WHERE COALESCE(TRIM(tipo_art_fab), '') = 'Terminado'
                  AND Discontinuo = 'No'
                  AND CodigoSubRubro IS NOT NULL
                  AND TRIM(COALESCE(CodigoSubRubroT, '')) <> ''
                  AND COALESCE(id_unimed, 0) = 1
                ORDER BY IDArt DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return out
            for key in (
                "CodigoRubro",
                "CodigoSubRubro",
                "CodigoSubRubroT",
                "IDSubRubro",
                "Alicuota",
                "AlicuotaIB",
                "TipoIVA",
                "TipoIB",
                "Moneda",
                "tipo_art",
                "CodigoModelo",
                "CodigoProveedor",
            ):
                if row.get(key) is not None and str(row.get(key)).strip() != "":
                    out[key] = row[key]
    except Exception:
        logger.exception("No se pudo leer plantilla de artículo en %s", base_empresa)
    return out


def resolver_codigo_marca(
    base_empresa: str, *, best_marca: str = "", best_id: str = ""
) -> int | None:
    """Resuelve CodMarca Admin desde marca BEST o prefijo del MMID."""
    candidatos: list[str] = []
    marca = str_or_default(best_marca, "").strip().upper()
    if marca:
        candidatos.append(marca)
        if marca in _MARCA_ALIAS:
            candidatos.append(_MARCA_ALIAS[marca])
    mid = str_or_default(best_id, "").strip().upper()
    m = re.match(r"^([A-Z]{1,4})", mid)
    if m:
        pref = m.group(1)
        candidatos.append(pref)
        if pref in _MARCA_ALIAS:
            candidatos.append(_MARCA_ALIAS[pref])
    if not candidatos:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cur:
            for cand in candidatos:
                cur.execute(
                    """
                    SELECT CodMarca FROM marca
                    WHERE anulado = 'No'
                      AND (
                        UPPER(TRIM(NombreMarca)) = %s
                        OR UPPER(TRIM(NombreMarca)) LIKE %s
                      )
                    ORDER BY CodMarca
                    LIMIT 1
                    """,
                    (cand, cand + "%"),
                )
                row = cur.fetchone()
                if row:
                    return to_int_or_none(row.get("CodMarca"))
    except Exception:
        logger.exception("No se pudo resolver marca Admin para %s", best_marca or best_id)
    return None


def bulto_desde_pack(best_pack: str | None) -> Decimal:
    """Docena comercial: pack 1→12, 2→6, 3→4, 4→3, 6→2; default 12."""
    pack = to_int_or_none(best_pack)
    if pack and pack > 0 and 12 % pack == 0:
        return Decimal(12 // pack)
    if pack and pack > 0:
        return Decimal(pack)
    return Decimal(12)


def codigo_barra_desde_secuencia(
    *, codigo_rubro: int, codigo_subrubro: int, codigo_articulo: int
) -> str:
    """Patrón Admin: RRRSSSAAAAAA (ej. 001001001384)."""
    return f"{codigo_rubro:03d}{codigo_subrubro:03d}{codigo_articulo:06d}"


def buscar_idart_por_id_manual(base_empresa: str, id_manual: str) -> int | None:
    mid = str_or_default(id_manual, "").strip()
    if not mid:
        return None
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            """
            SELECT IDArt FROM articulo
            WHERE TRIM(COALESCE(id_manual, '')) = %s
            LIMIT 1
            """,
            (mid,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return to_int_or_none(row.get("IDArt"))


def _siguiente_codigo_articulo(
    cur, *, codigo_rubro: int, codigo_subrubro: int
) -> int:
    cur.execute(
        """
        SELECT COALESCE(MAX(CodigoArticulo), 0) + 1 AS nxt
        FROM articulo
        WHERE CodigoRubro = %s AND CodigoSubRubro = %s
        """,
        (codigo_rubro, codigo_subrubro),
    )
    row = cur.fetchone()
    return int((row or {}).get("nxt") or 1)


def _asegurar_stock_deposito_cero(cur, id_art: int) -> int:
    cur.execute("SELECT CodDeposito FROM deposito")
    deps = [to_int_or_none(r.get("CodDeposito")) for r in cur.fetchall()]
    deps = [d for d in deps if d is not None]
    creados = 0
    for cod_dep in deps:
        cur.execute(
            """
            SELECT id_stock_deposito FROM stock_deposito
            WHERE id_articulo = %s AND id_deposito = %s
            LIMIT 1
            """,
            (id_art, cod_dep),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO stock_deposito (id_articulo, id_deposito, saldo)
            VALUES (%s, %s, %s)
            """,
            (id_art, cod_dep, 0),
        )
        creados += 1
    return creados


def crear_articulo(
    *,
    base_empresa: str,
    id_manual: str,
    nombre_articulo: str,
    codigo_articulo_t: str | None = None,
    cod_art_prov: str | None = None,
    detalle: str | None = None,
    tipo_art_fab: str = "Terminado",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Alta mínima AdministraNET (identidad + precios + barra + UM + bulto + stock_deposito).

    Returns:
        {success, idart, codigo_articulo, codigo_articulo_t, nro_cod_barra, stock_depositos_creados, message}
    """
    mid = str_or_default(id_manual, "").strip()
    nombre = str_or_default(nombre_articulo, "").strip()
    if not mid:
        raise ValueError("id_manual es obligatorio para el alta.")
    if not nombre:
        raise ValueError("NombreArticulo es obligatorio para el alta.")

    existente = buscar_idart_por_id_manual(base_empresa, mid)
    if existente:
        raise ValueError(
            f"Ya existe un artículo con id_manual={mid} (IDArt {existente}). "
            "Usá Asignar en lugar de dar de alta."
        )

    plantilla = _plantilla_defaults(base_empresa)
    if overrides:
        plantilla.update({k: v for k, v in overrides.items() if v is not None})

    codigo_rubro = to_int_or_none(plantilla.get("CodigoRubro")) or 1
    codigo_subrubro = to_int_or_none(plantilla.get("CodigoSubRubro")) or 1
    codigo_subrubro_t = str_or_default(plantilla.get("CodigoSubRubroT"), "1.1").strip() or "1.1"
    id_subrubro = to_int_or_none(plantilla.get("IDSubRubro")) or codigo_subrubro
    alicuota = to_int_or_none(plantilla.get("Alicuota")) or 1
    alicuota_ib = to_int_or_none(plantilla.get("AlicuotaIB")) or 2
    tipo_iva = str_or_default(plantilla.get("TipoIVA"), "Gravado")
    tipo_ib = str_or_default(plantilla.get("TipoIB"), "Gravado")
    moneda = str_or_default(plantilla.get("Moneda"), "Pesos")
    tipo_art = str_or_default(plantilla.get("tipo_art"), "Articulo")
    id_unimed = to_int_or_none(plantilla.get("id_unimed")) or 1
    codigo_marca = to_int_or_none(plantilla.get("CodigoMarca"))
    codigo_modelo = to_int_or_none(plantilla.get("CodigoModelo")) or 1
    codigo_proveedor = to_int_or_none(plantilla.get("CodigoProveedor")) or 1
    fab = str_or_default(tipo_art_fab, "Terminado").strip() or "Terminado"
    bulto = to_decimal_or_none(plantilla.get("cantidad_promedio_bulto"), "12") or Decimal(12)
    simbologia = str_or_default(plantilla.get("Simbologia"), "CODE128")
    simbologia_f = str_or_default(plantilla.get("SimbologiaF"), "CODE128")

    cod_prov = str_or_default(cod_art_prov, "-")
    det = str_or_default(detalle, "-")

    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        codigo_articulo = _siguiente_codigo_articulo(
            cur, codigo_rubro=codigo_rubro, codigo_subrubro=codigo_subrubro
        )
        cod_t = str_or_default(codigo_articulo_t, "").strip()
        if not cod_t:
            cod_t = f"{codigo_subrubro_t}.{codigo_articulo}"
        nro_barra = str_or_default(plantilla.get("NroCodBarra"), "").strip()
        if not nro_barra:
            nro_barra = codigo_barra_desde_secuencia(
                codigo_rubro=codigo_rubro,
                codigo_subrubro=codigo_subrubro,
                codigo_articulo=codigo_articulo,
            )

        fields = [
            "id_manual",
            "CodigoRubro",
            "CodigoSubRubro",
            "CodigoSubRubroT",
            "IDSubRubro",
            "CodigoArticulo",
            "CodigoArticuloT",
            "CodArtProv",
            "NombreArticulo",
            "Detalle",
            "PrecioCosto",
            "Precio1V",
            "Precio2V",
            "Precio3V",
            "Precio4V",
            "Precio5V",
            "Alicuota",
            "AlicuotaIB",
            "Moneda",
            "TipoIVA",
            "TipoIB",
            "Discontinuo",
            "tipo_art",
            "tipo_art_fab",
            "ensamblado",
            "disponible_vta",
            "disponible_comp",
            "ecommerce",
            "id_unimed",
            "CodigoModelo",
            "CodigoProveedor",
            "saldo_articulo",
            "cantidad_promedio_bulto",
            "NroCodBarra",
            "Simbologia",
            "SimbologiaF",
        ]
        values: list[Any] = [
            mid[:64],
            codigo_rubro,
            codigo_subrubro,
            codigo_subrubro_t[:32],
            id_subrubro,
            codigo_articulo,
            cod_t[:64],
            cod_prov[:128],
            nombre[:255],
            det,
            to_decimal_or_none(plantilla.get("PrecioCosto"), "0") or 0,
            to_decimal_or_none(plantilla.get("Precio1V"), "0") or 0,
            to_decimal_or_none(plantilla.get("Precio2V"), "0") or 0,
            to_decimal_or_none(plantilla.get("Precio3V"), "0") or 0,
            to_decimal_or_none(plantilla.get("Precio4V"), "0") or 0,
            to_decimal_or_none(plantilla.get("Precio5V"), "0") or 0,
            alicuota,
            alicuota_ib,
            moneda[:32],
            tipo_iva[:64],
            tipo_ib[:64],
            "No",
            tipo_art[:32],
            fab[:32],
            "No",
            str_or_default(plantilla.get("disponible_vta"), "Si")[:8],
            str_or_default(plantilla.get("disponible_comp"), "Si")[:8],
            str_or_default(plantilla.get("ecommerce"), "No")[:8],
            id_unimed,
            codigo_modelo,
            codigo_proveedor,
            0,
            bulto,
            nro_barra[:64],
            simbologia[:32],
            simbologia_f[:32],
        ]
        if codigo_marca is not None:
            fields.append("CodigoMarca")
            values.append(codigo_marca)

        placeholders = ", ".join(["%s"] * len(fields))
        field_sql = ", ".join(fields)
        cur.execute(
            f"""
            INSERT INTO articulo ({field_sql}, fecha_alta, fecha_mod)
            VALUES ({placeholders}, NOW(), NOW())
            """,
            tuple(values),
        )
        idart = to_int_or_none(getattr(cur, "lastrowid", None))
        if not idart:
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            idart = to_int_or_none((cur.fetchone() or {}).get("id"))
        if not idart:
            raise RuntimeError("INSERT articulo OK pero no se obtuvo IDArt.")

        n_sd = _asegurar_stock_deposito_cero(cur, idart)

    return {
        "success": True,
        "idart": idart,
        "id_manual": mid,
        "nombre": nombre,
        "codigo_articulo": codigo_articulo,
        "codigo_articulo_t": cod_t,
        "nro_cod_barra": nro_barra,
        "stock_depositos_creados": n_sd,
        "message": f"Artículo creado IDArt {idart} ({cod_t}).",
    }


def completar_campos_alta_articulo(
    *,
    base_empresa: str,
    idart: int,
    best_pack: str | None = None,
    best_marca: str = "",
    best_id: str = "",
) -> dict[str, Any]:
    """
    Completa campos faltantes en un artículo ya creado por alta Synap incompleta.
    No pisa precios > 0 ni barras ya cargadas.
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute("SELECT * FROM articulo WHERE IDArt = %s", (idart,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"No existe IDArt {idart}.")

        codigo_rubro = to_int_or_none(row.get("CodigoRubro")) or 1
        codigo_subrubro = to_int_or_none(row.get("CodigoSubRubro")) or 1
        codigo_articulo = to_int_or_none(row.get("CodigoArticulo")) or idart
        updates: dict[str, Any] = {}

        if row.get("IDSubRubro") is None:
            updates["IDSubRubro"] = codigo_subrubro

        um = to_int_or_none(row.get("id_unimed"))
        if um is None or um != 1:
            updates["id_unimed"] = 1

        bulto = to_decimal_or_none(row.get("cantidad_promedio_bulto"))
        if bulto is None or bulto <= 0:
            updates["cantidad_promedio_bulto"] = bulto_desde_pack(best_pack)

        barra = str_or_default(row.get("NroCodBarra"), "").strip()
        if not barra:
            updates["NroCodBarra"] = codigo_barra_desde_secuencia(
                codigo_rubro=codigo_rubro,
                codigo_subrubro=codigo_subrubro,
                codigo_articulo=codigo_articulo,
            )
        if not str_or_default(row.get("Simbologia"), "").strip():
            updates["Simbologia"] = "CODE128"
        if not str_or_default(row.get("SimbologiaF"), "").strip():
            updates["SimbologiaF"] = "CODE128"

        if to_int_or_none(row.get("CodigoModelo")) is None:
            updates["CodigoModelo"] = 1
        if to_int_or_none(row.get("CodigoProveedor")) is None:
            updates["CodigoProveedor"] = 1

        marca = resolver_codigo_marca(
            base_empresa, best_marca=best_marca, best_id=best_id or str_or_default(row.get("id_manual"))
        )
        if marca is not None:
            updates["CodigoMarca"] = marca

        if not updates:
            return {"idart": idart, "actualizados": {}, "message": "Sin cambios"}

        sets = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE articulo SET {sets}, fecha_mod = NOW() WHERE IDArt = %s",
            tuple(updates.values()) + (idart,),
        )
    return {"idart": idart, "actualizados": updates, "message": f"Actualizados {list(updates)}"}
