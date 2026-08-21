"""Servicio de control de calidad consolidado por artículo."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)
from mpr.db import get_mysql_connection as get_connection
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
)

_CERO = Decimal("0")
_RE_SEMI = re.compile(r"^semi_(\d+)(?:_(docenas|unidades))?$")
_RE_LINEA = re.compile(
    r"^(seg2da|scrap)_(\d+)_op_(\d+)_t_(\d+)(?:_(docenas|unidades))?$"
)


def _cantidad_post(valor: Any, componente: Optional[str], unidades_por_docena: int) -> Decimal:
    cantidad = to_decimal_or_none(valor)
    if cantidad is None:
        return _CERO
    if componente == "docenas":
        return cantidad * Decimal(int(unidades_por_docena))
    return cantidad


def parsear_post_cc_consolidado(
    post,
    *,
    unidades_por_docena: int = 12,
) -> Dict[int, Dict[str, Any]]:
    """Normaliza el POST canónico; las claves Semi por operario se ignoran."""
    acumulado: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {"semi": _CERO, "_lineas": defaultdict(Decimal)}
    )
    for clave, valor in post.items():
        nombre = str(clave)
        match_semi = _RE_SEMI.fullmatch(nombre)
        if match_semi:
            aid = to_int_or_none(match_semi.group(1))
            if aid is not None:
                acumulado[aid]["semi"] += _cantidad_post(
                    valor, match_semi.group(2), unidades_por_docena
                )
            continue
        # C6: cualquier variante semi_{art}_op_{...} queda fuera.
        if nombre.startswith("semi_") and "_op_" in nombre:
            continue
        match_linea = _RE_LINEA.fullmatch(nombre)
        if not match_linea:
            continue
        destino_raw, art_raw, op_raw, turno_raw, componente = match_linea.groups()
        aid = to_int_or_none(art_raw)
        oid = to_int_or_none(op_raw)
        tid = to_int_or_none(turno_raw)
        if aid is None or oid is None or tid is None:
            continue
        destino = "2da" if destino_raw == "seg2da" else "scrap"
        acumulado[aid]["_lineas"][(oid, tid, destino)] += _cantidad_post(
            valor, componente, unidades_por_docena
        )

    salida: Dict[int, Dict[str, Any]] = {}
    for aid, datos in acumulado.items():
        lineas = [
            (oid, tid, destino, cantidad)
            for (oid, tid, destino), cantidad in sorted(datos["_lineas"].items())
            if cantidad != 0
        ]
        salida[aid] = {"semi": datos["semi"], "lineas": lineas}
    return salida


def _pivot_saldo_produccion(
    base_empresa: str,
    id_articulos: Optional[Iterable[int]] = None,
) -> Dict[int, Dict[str, float]]:
    """Lee el saldo vivo de todos los depósitos Producción."""
    ids = [x for x in (to_int_or_none(v) for v in (id_articulos or [])) if x is not None]
    params: List[Any] = [TIPO_MPR_PRODUCCION]
    filtro = ""
    if ids:
        filtro = f" AND sd.id_articulo IN ({','.join(['%s'] * len(ids))})"
        params.extend(ids)
    resultado: Dict[int, Dict[str, float]] = {}
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS saldo
            FROM stock_deposito sd
            INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
            WHERE d.tipo_mpr = %s
              AND COALESCE(d.anulado, 'No') = 'No'
              {filtro}
            GROUP BY sd.id_articulo
            """,
            params,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo") if isinstance(row, dict) else row[0])
            saldo = row.get("saldo") if isinstance(row, dict) else row[1]
            if aid is not None:
                resultado[aid] = {
                    TIPO_MPR_PRODUCCION: float(to_decimal_or_none(saldo) or _CERO)
                }
    return resultado


def construir_bloques_cc_articulo(
    base_empresa: str,
    fecha: date,
    *,
    solo_pendiente: bool = False,
    marcas_incluidos: Optional[Iterable[int]] = None,
    modo_roster: Optional[bool] = None,
) -> Dict[str, Any]:
    """Construye un bloque por artículo usando parte ∪ saldo ∪ ledger del día."""
    from mpr.repositories.parte import acumular_celdas_clasificacion_maquina_turno
    from mpr.repositories.clasificacion_borrador import (
        listar_lineas_borrador_cc_consolidado,
        tiene_borrador,
        tiene_borrador_cc_consolidado,
    )
    from mpr.repositories.transicion_lote import (
        clasificado_segunda_scrap_por_celda_fecha,
        semi_agregado_por_articulo_fecha,
    )
    from mpr.services import _fetch_descripciones_articulo, _filtrar_ids_por_marcas

    if not (base_empresa or "").strip() or to_date_or_none(fecha) is None:
        return {
            "bloques": [],
            "filas": [],
            "filas_vacio": True,
            "hay_filas_editables": False,
            "requiere_fecha": fecha is None,
            "requiere_fecha_turno": False,
            "tiene_borrador": False,
            "borrador_incompatible": False,
            "aviso_borrador": "",
        }
    if modo_roster is not None:
        solo_pendiente = not bool(modo_roster)

    celdas = acumular_celdas_clasificacion_maquina_turno(base_empresa, fecha, None)
    parte_por_fila: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    for (_maquina, aid, oid, tid), datos in celdas.items():
        clave = (int(aid), int(oid), int(tid))
        fila = parte_por_fila.setdefault(
            clave,
            {
                "id_articulo": int(aid),
                "id_operario": int(oid),
                "id_mpr_turno": int(tid),
                "operario_nombre": str_or_default(datos.get("operario_nombre"), "-"),
                "turno_nombre": str_or_default(datos.get("turno_nombre"), "-"),
                "fabricado": _CERO,
            },
        )
        fila["fabricado"] += to_decimal_or_none(datos.get("cantidad")) or _CERO

    ids_parte = {clave[0] for clave in parte_por_fila}
    stock = _pivot_saldo_produccion(base_empresa)
    ids_saldo = {
        int(aid)
        for aid, por_tipo in stock.items()
        if (to_decimal_or_none(por_tipo.get(TIPO_MPR_PRODUCCION)) or _CERO) > 0
    }
    semi = semi_agregado_por_articulo_fecha(
        base_empresa, fecha, sorted(ids_parte | set(stock))
    )
    universo = ids_parte | ids_saldo | set(semi)
    if marcas_incluidos:
        universo &= _filtrar_ids_por_marcas(
            base_empresa, sorted(universo), list(marcas_incluidos)
        )
    descripciones = _fetch_descripciones_articulo(base_empresa, sorted(universo))
    try:
        clasificado_celdas = clasificado_segunda_scrap_por_celda_fecha(
            base_empresa, fecha, sorted(universo)
        )
    except Exception:
        clasificado_celdas = {}
    try:
        borrador_nuevo = tiene_borrador_cc_consolidado(base_empresa, fecha)
        lineas_borrador = (
            listar_lineas_borrador_cc_consolidado(base_empresa, fecha)
            if borrador_nuevo
            else []
        )
    except Exception:
        borrador_nuevo = False
        lineas_borrador = []
    try:
        borrador_viejo = tiene_borrador(base_empresa, fecha, None)
    except Exception:
        borrador_viejo = False
    borrador_incompatible = bool(borrador_viejo and not borrador_nuevo)
    borrador_semi: Dict[int, Decimal] = {}
    borrador_celdas: Dict[Tuple[int, int, int], Dict[str, Decimal]] = {}
    for linea in lineas_borrador:
        aid_b = to_int_or_none(linea.get("id_articulo"))
        oid_b = to_int_or_none(linea.get("id_operario"))
        tid_b = to_int_or_none(linea.get("id_mpr_turno"))
        if aid_b is None:
            continue
        if oid_b is None or tid_b is None:
            borrador_semi[aid_b] = (
                borrador_semi.get(aid_b, _CERO)
                + (to_decimal_or_none(linea.get("cant_semi")) or _CERO)
            )
            continue
        borrador_celdas[(aid_b, oid_b, tid_b)] = {
            "segunda": to_decimal_or_none(linea.get("cant_2da")) or _CERO,
            "scrap": to_decimal_or_none(linea.get("cant_scrap")) or _CERO,
        }

    bloques: List[Dict[str, Any]] = []
    filas_legacy: List[Dict[str, Any]] = []
    confirmadas_ocultas = 0
    for aid in sorted(universo):
        saldo = to_decimal_or_none(
            stock.get(aid, {}).get(TIPO_MPR_PRODUCCION)
        ) or _CERO
        if solo_pendiente and saldo <= 0:
            continue
        filas = [
            dict(datos)
            for (art, _op, _turno), datos in sorted(parte_por_fila.items())
            if art == aid
        ]
        tenia_parte = bool(filas)
        for fila in filas:
            clave_celda = (
                aid,
                int(fila["id_operario"]),
                int(fila["id_mpr_turno"]),
            )
            fila["clasificado_2da_scrap"] = clasificado_celdas.get(
                clave_celda, _CERO
            )
            borrador_celda = borrador_celdas.get(clave_celda, {})
            fila["borrador_segunda"] = borrador_celda.get("segunda", _CERO)
            fila["borrador_scrap"] = borrador_celda.get("scrap", _CERO)
        if solo_pendiente:
            filas_pendientes = [
                fila
                for fila in filas
                if (
                    to_decimal_or_none(fila.get("clasificado_2da_scrap"))
                    or _CERO
                ) <= 0
            ]
            confirmadas_ocultas += len(filas) - len(filas_pendientes)
            filas = filas_pendientes
        huerfano = not tenia_parte
        if huerfano:
            filas = [{
                "id_articulo": aid,
                "id_operario": None,
                "id_mpr_turno": None,
                "operario_nombre": "Sin operario en el parte",
                "turno_nombre": "—",
                "fabricado": _CERO,
                "huerfano": True,
            }]
        codigo, descripcion = descripciones.get(aid, ("-", "-"))
        bloque = {
            "id_articulo": aid,
            "codigo_manual": str_or_default(codigo, "-"),
            "descripcion": str_or_default(descripcion, "-"),
            "saldo_produccion": saldo,
            "tope_confirmacion": saldo,
            "semi_mostrar": semi.get(aid, _CERO),
            "borrador_semi": borrador_semi.get(aid, _CERO),
            "solo_lectura": saldo <= 0,
            "huerfano": huerfano,
            "filas": filas,
        }
        bloques.append(bloque)
        for indice, fila in enumerate(filas):
            legacy = dict(fila)
            legacy.update({
                "codigo_manual": bloque["codigo_manual"],
                "descripcion": bloque["descripcion"],
                "saldo_produccion": float(saldo),
                "max_clasificable": float(saldo),
                "base_clasificable": float(saldo),
                "disponible": float(saldo),
                "solo_lectura": bloque["solo_lectura"],
                "show_articulo": indice == 0,
                "rowspan_articulo": len(filas) if indice == 0 else 1,
            })
            filas_legacy.append(legacy)

    return {
        "bloques": bloques,
        "filas": filas_legacy,
        "filas_vacio": not bloques,
        "hay_filas_editables": any(not b["solo_lectura"] for b in bloques),
        "confirmadas_ocultas": confirmadas_ocultas,
        "bloqueos": [],
        "requiere_fecha": False,
        "requiere_fecha_turno": False,
        "componentes": [],
        "componentes_vacio": not bloques,
        "tiene_borrador": borrador_nuevo,
        "borrador_incompatible": borrador_incompatible,
        "aviso_borrador": (
            "El borrador anterior no es compatible; volvé a cargar."
            if borrador_incompatible
            else ""
        ),
    }


def _saldo_produccion_articulo(
    id_articulo: int,
    base_empresa: str,
    *,
    cursor=None,
    for_update: bool = True,
) -> Decimal:
    """Obtiene el saldo Producción del artículo; C1 agrega ``FOR UPDATE``."""
    propio = cursor is None
    conn = None
    if propio:
        conn = get_connection(base_empresa)
        cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COALESCE(SUM(sd.saldo), 0) AS saldo
            FROM stock_deposito sd
            INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
            WHERE sd.id_articulo = %s
              AND d.tipo_mpr = %s
              AND COALESCE(d.anulado, 'No') = 'No'
            FOR UPDATE
            """ if for_update else """
            SELECT COALESCE(SUM(sd.saldo), 0) AS saldo
            FROM stock_deposito sd
            INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
            WHERE sd.id_articulo = %s
              AND d.tipo_mpr = %s
              AND COALESCE(d.anulado, 'No') = 'No'
            """,
            [int(id_articulo), TIPO_MPR_PRODUCCION],
        )
        row = cursor.fetchone()
        valor = row.get("saldo") if isinstance(row, dict) else (row[0] if row else 0)
        return to_decimal_or_none(valor) or _CERO
    finally:
        if propio and conn is not None:
            conn.close()


def _es_huerfano(base_empresa: str, fecha: date, id_articulo: int) -> bool:
    from mpr.repositories.parte import acumular_celdas_clasificacion_maquina_turno

    celdas = acumular_celdas_clasificacion_maquina_turno(base_empresa, fecha, None)
    return not any(int(clave[1]) == int(id_articulo) for clave in celdas)


def _celda_parte_existe(
    base_empresa: str,
    fecha: date,
    id_articulo: int,
    id_operario: int,
    id_mpr_turno: int,
) -> bool:
    from mpr.repositories.parte import acumular_celdas_clasificacion_maquina_turno

    celdas = acumular_celdas_clasificacion_maquina_turno(base_empresa, fecha, None)
    return any(
        int(clave[1]) == int(id_articulo)
        and int(clave[2]) == int(id_operario)
        and int(clave[3]) == int(id_mpr_turno)
        for clave in celdas
    )


def _atribuible_2da_scrap(
    base_empresa: str,
    fecha: date,
    id_articulo: int,
    id_operario: int,
    id_mpr_turno: int,
) -> Decimal:
    """Calcula el remanente atribuible a 2da/scrap del operario y turno."""
    from mpr.repositories.parte import acumular_celdas_clasificacion_maquina_turno
    from mpr.repositories.transicion_lote import (
        clasificado_segunda_scrap_por_celda_fecha,
    )

    fabricado = sum(
        (
            to_decimal_or_none(datos.get("cantidad")) or _CERO
            for clave, datos in acumular_celdas_clasificacion_maquina_turno(
                base_empresa, fecha, None
            ).items()
            if clave[1:] == (id_articulo, id_operario, id_mpr_turno)
        ),
        _CERO,
    )
    clasificado = clasificado_segunda_scrap_por_celda_fecha(
        base_empresa, fecha, [id_articulo]
    ).get((id_articulo, id_operario, id_mpr_turno), _CERO)
    return max(_CERO, fabricado - clasificado)


def _transferir_cc_en_cursor(
    *,
    cursor,
    base_empresa: str,
    id_usuario: int,
    id_articulo: int,
    tipo_destino: str,
    cantidad: Decimal,
    fecha: date,
    id_operario: Optional[int],
    operario_nombre: Optional[str],
    id_mpr_turno: Optional[int],
) -> Tuple[int, str]:
    """Mueve stock y registra ledger dentro de la misma transacción CC."""
    from mpr.repositories.transicion_lote import crear_transicion_lote_en_cursor
    from mpr.services import _transferir_etapa_en_cursor

    ok, codigo, comprobante, error = _transferir_etapa_en_cursor(
        cursor,
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        id_articulo=id_articulo,
        tipo_origen=TIPO_MPR_PRODUCCION,
        tipo_destino=tipo_destino,
        cantidad=cantidad,
        fecha=fecha,
    )
    if not ok or codigo is None:
        raise RuntimeError(error or "No se pudo transferir el stock del artículo.")
    crear_transicion_lote_en_cursor(
        cursor,
        id_articulo,
        TIPO_MPR_PRODUCCION,
        tipo_destino,
        cantidad,
        codigo,
        id_usuario,
        id_operario=id_operario,
        operario_nombre=operario_nombre,
        fecha_produccion=fecha,
        id_mpr_turno=id_mpr_turno,
        cantidad_extra=_CERO,
    )
    return codigo, comprobante or ""


def _borrador_lineas_articulo(
    base_empresa: str,
    fecha: date,
    id_articulo: int,
    *,
    eliminar: bool = True,
) -> List[Dict[str, Any]]:
    """Lista o elimina únicamente líneas 007 del artículo confirmado."""
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT l.*
            FROM mpr_cc_borrador b
            INNER JOIN mpr_cc_borrador_linea l
              ON l.id_mpr_cc_borrador = b.id_mpr_cc_borrador
            WHERE b.fecha_produccion = %s AND l.id_articulo = %s
            """,
            [fecha, int(id_articulo)],
        )
        columnas = [c[0] for c in (cursor.description or [])]
        filas = [
            row if isinstance(row, dict) else dict(zip(columnas, row))
            for row in (cursor.fetchall() or [])
        ]
        if eliminar:
            from mpr.repositories.clasificacion_borrador import (
                eliminar_borrador_cc_articulo,
            )

            eliminar_borrador_cc_articulo(
                base_empresa, fecha, int(id_articulo), cursor=cursor
            )
            conn.commit()
        return filas


def _nombre_operario_parte(
    base_empresa: str,
    fecha: date,
    id_articulo: int,
    id_operario: int,
    id_mpr_turno: int,
) -> str:
    from mpr.repositories.parte import acumular_celdas_clasificacion_maquina_turno

    for clave, datos in acumular_celdas_clasificacion_maquina_turno(
        base_empresa, fecha, None
    ).items():
        if clave[1:] == (id_articulo, id_operario, id_mpr_turno):
            return str_or_default(datos.get("operario_nombre"), "-")
    return "-"


def confirmar_cc_consolidado(
    base_empresa: str,
    id_usuario: int,
    fecha: date,
    payload: Dict[int, Dict[str, Any]],
) -> Dict[str, Any]:
    """Confirma cada artículo en una transacción MySQL independiente."""
    resultado: Dict[str, Any] = {"ok": [], "errores": [], "comprobantes": []}

    def _comprobante_transferencia(valor: Any) -> str:
        if isinstance(valor, tuple) and len(valor) >= 2:
            return str_or_default(valor[1], "")
        return ""

    for id_articulo_raw, datos in (payload or {}).items():
        aid = to_int_or_none(id_articulo_raw)
        if aid is None:
            resultado["errores"].append((id_articulo_raw, "Artículo inválido."))
            continue
        semi = to_decimal_or_none((datos or {}).get("semi")) or _CERO
        lineas_validas: List[Tuple[int, int, str, Decimal]] = []
        error_validacion: Optional[str] = None
        if semi < 0:
            error_validacion = "La cantidad de Semi no puede ser negativa."
        for linea in (datos or {}).get("lineas", []):
            if len(linea) != 4:
                error_validacion = "La línea de clasificación es inválida."
                break
            oid = to_int_or_none(linea[0])
            tid = to_int_or_none(linea[1])
            destino = str(linea[2])
            cantidad = to_decimal_or_none(linea[3])
            if oid is None or tid is None or destino not in {"2da", "scrap"}:
                error_validacion = "Falta operario o turno válido para 2da/desperdicio."
                break
            if cantidad is None or cantidad < 0:
                error_validacion = "Las cantidades no pueden ser negativas."
                break
            if cantidad > 0:
                lineas_validas.append((oid, tid, destino, cantidad))
        if error_validacion:
            resultado["errores"].append((aid, error_validacion))
            continue

        try:
            with get_connection(base_empresa) as conn:
                conn.autocommit(False)
                cursor = conn.cursor()
                try:
                    saldo = _saldo_produccion_articulo(
                        aid, base_empresa, cursor=cursor, for_update=True
                    )
                    total = semi + sum((linea[3] for linea in lineas_validas), _CERO)
                    if total > saldo:
                        raise ValueError(
                            f"La cantidad total ({total}) supera el saldo Producción disponible ({saldo})."
                        )
                    huerfano = (
                        _es_huerfano(base_empresa, fecha, aid)
                        if lineas_validas
                        else False
                    )
                    if huerfano and lineas_validas:
                        raise ValueError(
                            "El artículo no tiene parte del día; solo permite clasificar Semi."
                        )
                    for oid, tid, _destino, _cantidad in lineas_validas:
                        if not _celda_parte_existe(
                            base_empresa, fecha, aid, oid, tid
                        ):
                            raise ValueError(
                                "La 2da/desperdicio no corresponde a un operario y turno del parte."
                            )
                    post_por_celda: Dict[Tuple[int, int], Decimal] = defaultdict(Decimal)
                    for oid, tid, _destino, cantidad in lineas_validas:
                        post_por_celda[(oid, tid)] += cantidad
                    for (oid, tid), cantidad_post in post_por_celda.items():
                        atribuible = _atribuible_2da_scrap(
                            base_empresa, fecha, aid, oid, tid
                        )
                        if cantidad_post > atribuible:
                            raise ValueError(
                                "La 2da/desperdicio supera lo fabricado por el operario en el parte."
                            )

                    # Las líneas por operario se ejecutan primero; cualquier fallo
                    # impide incluso intentar el Semi dentro de esta transacción.
                    for oid, tid, destino, cantidad in lineas_validas:
                        tipo_destino = (
                            TIPO_MPR_2DA_SELECCION
                            if destino == "2da"
                            else TIPO_MPR_SCRAP
                        )
                        comprobante = _comprobante_transferencia(_transferir_cc_en_cursor(
                            cursor=cursor,
                            base_empresa=base_empresa,
                            id_usuario=int(id_usuario),
                            id_articulo=aid,
                            tipo_destino=tipo_destino,
                            cantidad=cantidad,
                            fecha=fecha,
                            id_operario=oid,
                            operario_nombre=_nombre_operario_parte(
                                base_empresa, fecha, aid, oid, tid
                            ),
                            id_mpr_turno=tid,
                        ))
                        if comprobante:
                            resultado["comprobantes"].append(comprobante)
                    if semi > 0:
                        comprobante = _comprobante_transferencia(_transferir_cc_en_cursor(
                            cursor=cursor,
                            base_empresa=base_empresa,
                            id_usuario=int(id_usuario),
                            id_articulo=aid,
                            tipo_destino=TIPO_MPR_SEMI_ELABORADO,
                            cantidad=semi,
                            fecha=fecha,
                            id_operario=None,
                            operario_nombre=None,
                            id_mpr_turno=None,
                        ))
                        if comprobante:
                            resultado["comprobantes"].append(comprobante)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
            _borrador_lineas_articulo(
                base_empresa, fecha, aid, eliminar=True
            )
            resultado["ok"].append(aid)
        except Exception as exc:
            resultado["errores"].append((aid, str(exc)))
    return resultado
