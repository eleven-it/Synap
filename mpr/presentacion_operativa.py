"""Presentación docenas/pares en pantallas operativas MPR."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mpr.services import descomponer_docenas_unidades, texto_docenas_pares, texto_docenas_unidades

SESSION_KEY = "mpr_presentacion_cantidad"
SESSION_KEY_ARMADO = "mpr_presentacion_armado"
MODOS = frozenset({"docenas", "unidades"})
DEFAULT_MODO = "docenas"
DEFAULT_MODO_ARMADO = "unidades"
UNIDADES_POR_DOCENA = 12

CAMPOS_TABLERO_CANTIDAD = (
    "resta_urgente",
    "resta_urgente_ped",
    "resta_total",
    "pendiente",
    "enviado",
    "envios",
    "produccion",
    "segunda_seleccion",
    "semi_elaborado",
    "total",
    "stock_proceso",
)

# Inventario real en Tablero de producción: Terminado (Pack usa ``total``) y
# aliases de stock terminado — no ocultar saldos negativos (paridad Armado).
CAMPOS_TABLERO_SIN_CLAMP_NEGATIVOS = frozenset(
    {"total", "terminado", "stock_terminado"}
)


def parse_modo_presentacion_operativa(raw: Optional[str]) -> str:
    modo = (raw or "").strip().lower()
    return modo if modo in MODOS else DEFAULT_MODO


def resolver_modo_presentacion_operativa(request) -> str:
    """Lee ?presentacion= de GET (persiste en sesión) o devuelve sesión/default."""
    raw = (request.GET.get("presentacion") or "").strip().lower()
    if raw in MODOS:
        request.session[SESSION_KEY] = raw
        if hasattr(request.session, "modified"):
            request.session.modified = True
        return raw
    return parse_modo_presentacion_operativa(request.session.get(SESSION_KEY))


def resolver_modo_presentacion_armado(request) -> str:
    """Presentación en Armado 1ra/2da: GET → sesión propia; default Pares (no hereda del Tablero)."""
    raw = (request.GET.get("presentacion") or "").strip().lower()
    if raw in MODOS:
        request.session[SESSION_KEY_ARMADO] = raw
        if hasattr(request.session, "modified"):
            request.session.modified = True
        return raw
    session_val = (request.session.get(SESSION_KEY_ARMADO) or "").strip().lower()
    if session_val in MODOS:
        return session_val
    return DEFAULT_MODO_ARMADO


def pcp_pares_y_docenas_decimal(
    cantidad: Any,
    *,
    clamp_negativos: bool = True,
) -> Dict[str, Any]:
    """Paridad PCP: columna Pares (entero) y Docenas = pares ÷ 12 (decimal).

    ``clamp_negativos=False`` conserva saldos negativos (inventario real, p. ej. Terminado en Armado).
    """
    try:
        pares = int(round(float(cantidad or 0)))
    except (TypeError, ValueError):
        pares = 0
    if clamp_negativos:
        pares = max(0, pares)
    return {
        "pares": pares,
        "docenas": round(pares / float(UNIDADES_POR_DOCENA), 2),
    }


def _enriquecer_bloque_demanda_pcp(out: Dict[str, Any]) -> None:
    """Columnas Demanda a producir al estilo PCP (Pedido, Reserva, Resta total, Resta urgente)."""
    pedido = out.get("dem_ped")
    if pedido is None:
        pedido = out.get("urgente", 0)
    out["pedido_pares"] = pcp_pares_y_docenas_decimal(pedido)["pares"]
    out["pedido_docenas_pcp"] = docenas_enteras_pcp(pedido)

    reserva = out.get("dem_res", 0)
    res_pcp = pcp_pares_y_docenas_decimal(reserva)
    out["reserva_pares"] = res_pcp["pares"]
    out["reserva_docenas_pcp"] = docenas_enteras_pcp(reserva)

    rt = pcp_pares_y_docenas_decimal(out.get("resta_total", 0))
    out["resta_total_pares"] = rt["pares"]
    out["resta_total_docenas_pcp"] = docenas_enteras_pcp(out.get("resta_total", 0))

    ru = pcp_pares_y_docenas_decimal(out.get("resta_urgente", 0))
    out["resta_urgente_pares"] = ru["pares"]
    out["resta_urgente_docenas_pcp"] = docenas_enteras_pcp(out.get("resta_urgente", 0))

    ru_ped = pcp_pares_y_docenas_decimal(out.get("resta_urgente_ped", 0))
    out["resta_urgente_ped_pares"] = ru_ped["pares"]
    out["resta_urgente_ped_docenas_pcp"] = docenas_enteras_pcp(
        out.get("resta_urgente_ped", 0)
    )


def docenas_enteras_pcp(cantidad: Any, *, clamp_negativos: bool = True) -> int:
    """Docenas para UI tablero: entero redondeado (pares ÷ 12)."""
    return int(
        round(
            float(
                pcp_pares_y_docenas_decimal(cantidad, clamp_negativos=clamp_negativos)[
                    "docenas"
                ]
            )
        )
    )


def _formato_entero_miles_es(n: int) -> str:
    """Entero con separador de miles es-AR (punto), sin decimales."""
    neg = n < 0
    s = str(abs(int(n)))
    bloques: list[str] = []
    while len(s) > 3:
        bloques.append(s[-3:])
        s = s[:-3]
    if s:
        bloques.append(s)
    cuerpo = ".".join(reversed(bloques)) if bloques else "0"
    return f"-{cuerpo}" if neg else cuerpo


def _display_cantidad_tablero(
    val: Any,
    modo: str,
    *,
    clamp_negativos: bool = True,
) -> str:
    """Solo docenas enteras o pares enteros — sin decimales, con separador de miles."""
    pcp = pcp_pares_y_docenas_decimal(val, clamp_negativos=clamp_negativos)
    if modo == "docenas":
        n = docenas_enteras_pcp(val, clamp_negativos=clamp_negativos)
    else:
        n = pcp["pares"]
    return _formato_entero_miles_es(n)


def _display_cantidad(val: Any, modo: str, *, usar_pares: bool = True) -> str:
    try:
        n = int(round(float(val or 0)))
    except (TypeError, ValueError):
        n = 0
    if modo == "docenas":
        if usar_pares:
            return texto_docenas_pares(n, unidades_por_docena_fijo=UNIDADES_POR_DOCENA)
        return texto_docenas_unidades(n, unidades_por_docena_fijo=UNIDADES_POR_DOCENA)
    return str(n)


def _enriquecer_cantidad_envio(
    out: Dict[str, Any],
    campo_base: str,
    modo: str,
) -> None:
    """Docenas/pares sueltos para inputs de envío (prefijo según campo_base)."""
    try:
        cant = int(round(float(out.get(campo_base) or 0)))
    except (TypeError, ValueError):
        cant = 0
    du = descomponer_docenas_unidades(cant, unidades_por_docena_fijo=UNIDADES_POR_DOCENA)
    out[f"{campo_base}_docenas"] = du["docenas"]
    out[f"{campo_base}_pares_sueltos"] = du["unidades"]
    out[f"{campo_base}_docenas_pcp"] = docenas_enteras_pcp(cant)
    # Alias legacy para plantillas en transición
    if campo_base == "resta_urgente":
        out["pendiente_docenas"] = du["docenas"]
        out["pendiente_unidades_sueltas"] = du["unidades"]


def enriquecer_fila_tablero_presentacion(
    fila: Dict[str, Any],
    modo: str,
) -> Dict[str, Any]:
    out = dict(fila)
    out["presentacion_modo"] = modo
    for campo in CAMPOS_TABLERO_CANTIDAD:
        if campo in out:
            clamp = campo not in CAMPOS_TABLERO_SIN_CLAMP_NEGATIVOS
            out[f"{campo}_display"] = _display_cantidad_tablero(
                out[campo], modo, clamp_negativos=clamp
            )
            out[f"{campo}_docenas_pcp"] = docenas_enteras_pcp(
                out[campo], clamp_negativos=clamp
            )
            if not clamp:
                try:
                    saldo = int(round(float(out[campo] or 0)))
                except (TypeError, ValueError):
                    saldo = 0
                out[f"{campo}_es_negativo"] = saldo < 0
    # Alias Terminado (Pack): raw ``terminado`` / ``stock_terminado`` fuera del loop.
    for campo in ("terminado", "stock_terminado"):
        if campo in out and f"{campo}_display" not in out:
            out[f"{campo}_display"] = _display_cantidad_tablero(
                out[campo], modo, clamp_negativos=False
            )
            out[f"{campo}_docenas_pcp"] = docenas_enteras_pcp(
                out[campo], clamp_negativos=False
            )
            try:
                saldo = int(round(float(out[campo] or 0)))
            except (TypeError, ValueError):
                saldo = 0
            out[f"{campo}_es_negativo"] = saldo < 0
    _enriquecer_bloque_demanda_pcp(out)
    if "a_enviar" not in out:
        from mpr.services import _calcular_a_enviar_componente

        # `envios` = ledger bruto; `enviado` = Fabricando (envíos − acreditado).
        envios_ledger = out.get("envios", out.get("enviado", 0))
        fabricando = out["enviado"] if "enviado" in out else None
        out["a_enviar"] = _calcular_a_enviar_componente(
            out.get("resta_urgente", 0),
            envios_ledger,
            resta_total=out.get("resta_total"),
            fabricando=fabricando,
        )
    _enriquecer_cantidad_envio(out, "a_enviar", modo)
    # Alias legacy: inputs/docenas de envío leen a_enviar_*
    if "a_enviar_docenas" in out:
        out["resta_urgente_docenas"] = out["a_enviar_docenas"]
        out["resta_urgente_pares_sueltos"] = out["a_enviar_pares_sueltos"]
        out["pendiente_docenas"] = out["a_enviar_docenas"]
        out["pendiente_unidades_sueltas"] = out["a_enviar_pares_sueltos"]
    return out


def enriquecer_filas_tablero_presentacion(
    filas: List[Dict[str, Any]],
    modo: str,
) -> List[Dict[str, Any]]:
    return [enriquecer_fila_tablero_presentacion(f, modo) for f in (filas or [])]


def enriquecer_resumen_tablero_kpi_presentacion(
    resumen: Dict[str, Any],
    modo: str,
) -> Dict[str, Any]:
    """
    Presentación Docenas|Pares para el Tablero de control (/mpr/).

    Conserva valores crudos en pares; añade ``*_display`` y etiquetas de unidad.
    """
    out = dict(resumen or {})
    modo_n = parse_modo_presentacion_operativa(modo)
    out["modo_presentacion"] = modo_n
    out["unidad_cantidad_label"] = "docenas" if modo_n == "docenas" else "pares"
    out["unidad_cantidad_label_titulo"] = (
        "Docenas" if modo_n == "docenas" else "Pares"
    )

    pending = out.get("kpi_pending_units", 0)
    out["kpi_pending_units_display"] = _display_cantidad_tablero(pending, modo_n)
    pending_ped = out.get("kpi_pending_units_ped", 0)
    out["kpi_pending_units_ped_display"] = _display_cantidad_tablero(
        pending_ped, modo_n
    )

    comps: List[Dict[str, Any]] = []
    for row in out.get("componentes_pendientes") or []:
        item = dict(row)
        item["resta_urgente_display"] = _display_cantidad_tablero(
            item.get("resta_urgente", 0), modo_n
        )
        item["resta_urgente_ped_display"] = _display_cantidad_tablero(
            item.get("resta_urgente_ped", 0), modo_n
        )
        item["fabricando_display"] = _display_cantidad_tablero(
            item.get("fabricando", 0), modo_n
        )
        comps.append(item)
    out["componentes_pendientes"] = comps

    packs: List[Dict[str, Any]] = []
    tot_stock = tot_resta = tot_ped = 0
    for row in out.get("top_packs_pendientes") or []:
        item = dict(row)
        for campo in (
            "stock_terminado",
            "resta_urgente",
            "resta_urgente_ped",
            "a_fabricar",
        ):
            clamp = campo not in CAMPOS_TABLERO_SIN_CLAMP_NEGATIVOS
            item[f"{campo}_display"] = _display_cantidad_tablero(
                item.get(campo, 0), modo_n, clamp_negativos=clamp
            )
            if not clamp:
                try:
                    saldo = int(round(float(item.get(campo) or 0)))
                except (TypeError, ValueError):
                    saldo = 0
                item[f"{campo}_es_negativo"] = saldo < 0
        tot_stock += int(round(float(item.get("stock_terminado") or 0)))
        tot_resta += int(round(float(item.get("resta_urgente") or 0)))
        tot_ped += int(round(float(item.get("resta_urgente_ped") or 0)))
        packs.append(item)
    out["top_packs_pendientes"] = packs
    out["top_urgencias"] = packs
    out["totales_packs_stock"] = tot_stock
    out["totales_packs_resta"] = tot_resta
    out["totales_packs_ped"] = tot_ped
    out["totales_packs_stock_display"] = _display_cantidad_tablero(
        tot_stock, modo_n, clamp_negativos=False
    )
    out["totales_packs_resta_display"] = _display_cantidad_tablero(tot_resta, modo_n)
    out["totales_packs_ped_display"] = _display_cantidad_tablero(tot_ped, modo_n)
    return out


CAMPOS_TABLERO_ARMADO = (
    "pedido",
    "stock_terminado",
    "stock_reserva",
    "resta_urgente",
    "resta_armar",
    "max_armable",
    "a_armar",
)

# Inventario real: no ocultar saldos negativos (paridad Inventario Stock).
CAMPOS_ARMADO_SIN_CLAMP_NEGATIVOS = frozenset({"stock_terminado"})


def enriquecer_fila_tablero_armado(
    fila: Dict[str, Any],
    modo: str,
    *,
    marcas_etiqueta: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    out = dict(fila)
    out["presentacion_modo"] = modo
    for campo in CAMPOS_TABLERO_ARMADO:
        if campo in out:
            clamp = campo not in CAMPOS_ARMADO_SIN_CLAMP_NEGATIVOS
            out[f"{campo}_display"] = _display_cantidad_tablero(
                out[campo], modo, clamp_negativos=clamp
            )
            out[f"{campo}_docenas_pcp"] = docenas_enteras_pcp(
                out[campo], clamp_negativos=clamp
            )
            if not clamp:
                try:
                    saldo = int(round(float(out[campo] or 0)))
                except (TypeError, ValueError):
                    saldo = 0
                out[f"{campo}_es_negativo"] = saldo < 0
    cm = out.get("codigo_marca")
    if cm is not None and marcas_etiqueta:
        out["marca_nombre"] = marcas_etiqueta.get(int(cm), "")
    else:
        out["marca_nombre"] = out.get("marca_nombre") or ""
    out["a_armar_docenas_pcp"] = docenas_enteras_pcp(out.get("a_armar", 0))
    return out


def enriquecer_filas_tablero_armado(
    filas: List[Dict[str, Any]],
    modo: str,
    *,
    marcas_etiqueta: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    return [
        enriquecer_fila_tablero_armado(f, modo, marcas_etiqueta=marcas_etiqueta)
        for f in (filas or [])
    ]
