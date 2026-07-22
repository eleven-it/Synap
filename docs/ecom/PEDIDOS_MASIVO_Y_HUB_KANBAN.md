# Pedidos — Hub Kanban, territorio comercial y carga masiva por sucursales

**Change SDD:** `openspec/changes/archive/2026-07-13-ecom-pedidos-hub-kanban-masivo-sucursales/` (+ `openspec/changes/ecom-pedido-masivo-consolidado-hub/`)  
**Fecha:** 22/07/2026  
**Estado:** hub masivo archivado; consolidado lote en apply/verify

## Resumen

1. **`/ecom/mayoristapp/pedidos/`** deja de ser hub KPI y pasa a **Lista | Kanban** (estilo Odoo, visual Tablero de producción): borradores, enviados, por autorizar, aprobados, anulados.
2. **Config** Vendedor → Cliente → Marca (sin solape de marca por cliente); permiso supervisor.
3. **Pedido masivo:** matriz artículo × sucursal (`cliente_domicilio`); 1 PED por sucursal; borrador Postgres recuperable; rollback de lote sin perder carga.

## Documentos del change

| Artefacto | Path |
|-----------|------|
| Exploración | `openspec/changes/.../exploration.md` |
| Propuesta | `proposal.md` |
| Diseño | `design.md` |
| Tasks | `tasks.md` |
| Specs | `specs/*/` |

## Docs operativos

| Doc | Path |
|-----|------|
| Hub Lista\|Kanban | `docs/ecom/PEDIDOS_HUB_KANBAN.md` |
| Ternas territorio | `docs/ecom/VENDEDOR_CLIENTE_MARCA.md` |
| Pedido masivo | `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` |
| Jerarquía y aprobación lote | `docs/ecom/JERARQUIA_COMERCIAL_APROBACION.md` |

**Actualización 22/07/2026 (`ecom-pedido-masivo-consolidado-hub`):** resumen de lote `/pedidos/lote/<draft_id>/`; autorización comercial de lote completo; matriz `readonly=1` en pestaña «Qué se cargó». Ver docs operativos arriba.

**Rediseño hub 22/07/2026:** los lotes confirmados ya no usan lane **Cargas masivas**; la tarjeta `lote_masivo` va en la columna Kanban operativa y los PED hijos no se listan en el hub. Ver `PEDIDOS_HUB_KANBAN.md`.

**Corrección 22/07/2026:** borradores de pedido simple con ``cod_mov_origen`` cuyo PED ya no está **Pendiente** (p. ej. En preparación / En Remito) se **archivan** automáticamente y **no** aparecen en la columna Borrador del hub (`_archivar_draft_origen_no_editable` en `pedidos_hub_pipeline.py`).
**Corrección 14/07/2026:** la confirmación masiva normaliza filas MySQL de punto de venta en formato tupla o diccionario; los errores de resolución de PV responden JSON 400.

## Schema / permisos (Phase 0–1)

- Permisos: `ecom.pedido_masivo.usar`, `ecom.config_vendedor_cliente_marca`
- MySQL: proveedor `ecom_vendedor_cliente_marca` (`ecom/sql/001_ecom_vendedor_cliente_marca.sql`)
- Postgres: `EcomPedidoMasivoDraft` + `EcomPedidoMasivoDraftCelda`
- Stubs menú: `/pedido-masivo-sucursales/`, `/config/vendedor-cliente-marca/` (UI completa Phase 2/4)