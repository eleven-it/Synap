"""Contrato formal de etapas y transiciones del pipeline MPR.

Módulo puro: sin I/O, sin acceso a base de datos, sin modelos Django.
Las etapas 2–6 del refactor MPR importarán sus constantes desde aquí.

Fórmulas derivadas (implementación diferida a etapa 2):
    Total = Σ stock_deposito(id_articulo, id_deposito)
              WHERE id_deposito ∈ depósitos con tipo_mpr ∈ TIPOS_QUE_SUMAN_STOCK
              AND suma_stock = 'Si'

    Enviado_virtual = OPT_acumulado_liberado(id_articulo) − OPP_acumulado_registrado(id_articulo)
      (ledger sin movimiento físico en stock_deposito)

    Pendiente = max(0, Demanda_componente − Enviado_virtual − Total)
      Demanda_componente: vía services._explosion_demanda_componentes_pedido_reserva_pack()
      neteada contra stock_terminado del pack

Semántica Enviado vs. Producción:
    - Enviado a producción (VIRTUAL): OPT liberado acumulado − OPP registrado acumulado.
      No genera movimiento en stock_deposito.
    - Producción (FÍSICO): nace al registrar OPP; refleja stock en depósito tipo_mpr=Produccion.
    El desmontaje del automatismo en ejecutar_liberar_opt() se hace en etapa 5.
"""
from __future__ import annotations

from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
)
# Etapa 10: 'Planchado' deja de ser una etapa con stock del pipeline. La constante
# se re-exporta como DEPRECADA (backward-compat de imports) pero NO participa en
# ORDEN_ETAPAS_MPR, TIPOS_QUE_SUMAN_STOCK ni TRANSICIONES_LEGALES.
from mpr.services import TIPO_MPR_PLANCHADO  # noqa: F401  (deprecado)

# ---------------------------------------------------------------------------
# Estados virtuales (sin depósito físico en stock_deposito)
# ---------------------------------------------------------------------------

ESTADO_VIRTUAL_PENDIENTE = "Pendiente"
ESTADO_VIRTUAL_ENVIADO = "Enviado"

# ---------------------------------------------------------------------------
# Orden canónico de las 7 etapas (2 virtuales + 5 físicas)
#
# Etapa 10: se elimina "Planchado" como etapa/depósito con stock. El planchado
# es un momento dentro de la producción (ahí se inspecciona), pero nunca deja
# saldo: la clasificación sale directo de Producción hacia
# {2da Selección | Semi Elaborado | Desperdicio}.
# ---------------------------------------------------------------------------

ORDEN_ETAPAS_MPR: tuple[str, ...] = (
    ESTADO_VIRTUAL_PENDIENTE,   # 1 — virtual, derivado: max(0, Demanda − Enviado − Total)
    ESTADO_VIRTUAL_ENVIADO,     # 2 — virtual, ledger: OPT liberado − OPP registrado
    TIPO_MPR_PRODUCCION,        # 3 — físico, nace al registrar OPP (incluye planchado)
    TIPO_MPR_2DA_SELECCION,     # 4 — físico, clasificado desde Producción
    TIPO_MPR_SEMI_ELABORADO,    # 5 — físico, clasificado desde Producción
    TIPO_MPR_TERMINADO,         # 6 — físico, destino final del armado
    TIPO_MPR_SCRAP,             # 7 — físico, terminal, excluido del Total
)

# ---------------------------------------------------------------------------
# Etapas físicas que suman al Total.
# Desperdicio (Scrap) está explícitamente excluido.
# ---------------------------------------------------------------------------

TIPOS_QUE_SUMAN_STOCK: frozenset[str] = frozenset({
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
})

# ---------------------------------------------------------------------------
# Grafo de transiciones legales: origen → conjunto de destinos permitidos.
#
# Transición (a) Pendiente→Enviado: reducción derivada, sin movimiento físico;
#   se gestiona vía ejecutar_liberar_opt() (desmontaje diferido a etapa 5).
# Transición (b) Enviado→Produccion: registro de OPP (genera movimiento_stock).
# Transición (c) Produccion→{2daSeleccion|SemiElaborado|Scrap}: clasificación
#   consolidada (Etapa 10). El planchado es un momento dentro de producción y no
#   deja stock; la inspección determina directamente el destino final.
# Transición (d) {2daSeleccion|SemiElaborado}→Terminado: armado final
#   (ya implementado en services.py; sin cambios en etapa 1).
# ---------------------------------------------------------------------------

TRANSICIONES_LEGALES: dict[str, frozenset[str]] = {
    ESTADO_VIRTUAL_ENVIADO:  frozenset({TIPO_MPR_PRODUCCION}),
    TIPO_MPR_PRODUCCION:     frozenset({TIPO_MPR_2DA_SELECCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP}),
    TIPO_MPR_2DA_SELECCION:  frozenset({TIPO_MPR_TERMINADO}),
    TIPO_MPR_SEMI_ELABORADO: frozenset({TIPO_MPR_TERMINADO}),
    TIPO_MPR_SCRAP:          frozenset(),   # terminal
    TIPO_MPR_TERMINADO:      frozenset(),   # terminal
}


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------

def es_transicion_legal(origen: str, destino: str) -> bool:
    """True si la transición origen→destino está definida en el contrato del pipeline."""
    return destino in TRANSICIONES_LEGALES.get(origen, frozenset())


def validar_transicion(
    origen: str,
    destino: str,
    cantidad: "int | float",
    saldo_origen: "int | float",
) -> "tuple[bool, str | None]":
    """Valida legalidad de transición y disponibilidad de saldo.

    Retorna (ok, mensaje_error). Módulo puro: sin I/O ni acceso a DB.
    El saldo_origen debe obtenerse previamente desde stock_deposito.

    Args:
        origen: etapa de origen (constante TIPO_MPR_* o ESTADO_VIRTUAL_*).
        destino: etapa de destino.
        cantidad: unidades a mover (debe ser > 0).
        saldo_origen: stock disponible en la etapa origen.

    Returns:
        (True, None) si la transición es válida y el saldo alcanza.
        (False, mensaje) en caso de error.
    """
    if not es_transicion_legal(origen, destino):
        return False, f"Transición no permitida: {origen} → {destino}."
    if not (cantidad > 0):
        return False, "La cantidad debe ser mayor a cero."
    if cantidad > saldo_origen:
        return False, (
            f"Saldo insuficiente en {origen}: "
            f"disponible {saldo_origen}, solicitado {cantidad}."
        )
    return True, None
