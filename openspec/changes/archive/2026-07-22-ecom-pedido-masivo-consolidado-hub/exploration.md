# Exploration: Pedido masivo consolidado en hub

**Change:** `ecom-pedido-masivo-consolidado-hub`  
**Fecha:** 22/07/2026  
**Modo persistencia:** openspec

## Diagnóstico

Al confirmar un pedido masivo, `batch_checkout_masivo` crea **N PED MySQL** (1 por sucursal con cantidad). El draft Postgres `EcomPedidoMasivoDraft` queda `estado=confirmado` con `codigos_movimiento[]`, pero el hub (`pedidos_hub_pipeline`) solo muestra PED sueltos en columnas operativas. No existe vista de lote ni enlace draft↔PED en la UI.

**Hoy en pipeline:** drafts masivos solo en borrador/confirmando/anulado (columna Borrador). Drafts confirmados **no** aparecen como entidad consolidada.

## Decisiones UX (LOCKED — 22/07/2026)

| Tema | Decisión |
|------|----------|
| Visibilidad | Lane **Cargas masivas** (fuera de columnas Kanban de estado) + tarjeta padre |
| PED hijos | Permanecen en columnas operativas con chip `Lote · {Cliente} (k/n)` |
| Detalle | Pantalla resumen del lote + pestaña **Qué se cargó** (matriz read-only) |
| Autorización | **Lote completo** (aprobar/rechazar todos los PED del draft) |
| CTA en hijos | Ocultar aprobar/rechazar individual si lote pendiente de autorización |

## Hooks existentes

- Modelo: `EcomPedidoMasivoDraft.codigos_movimiento` (`ecom/models.py`)
- Confirmación: `ecom/services/batch_checkout_masivo.py`
- Hub: `ecom/services/pedidos_hub_pipeline.py`
- Aprobación PED: `ecom/services/aprobacion_pedidos.py` + APIs por `cod_mov`

## Fuera de alcance (1ª entrega)

Agrupar lotes en columnas Kanban; quitar PED del tablero; FK lote en MySQL; reescribir checkout masivo; autorización PED-a-PED dentro de lote pendiente.

## Ready for Proposal

**Sí.** UX fijada; plan de implementación en 5 fases disponible. No requiere re-exploración de código.
