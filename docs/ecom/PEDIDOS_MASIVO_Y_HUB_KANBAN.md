# Pedidos — Hub Kanban, territorio comercial y carga masiva por sucursales

**Change SDD:** `openspec/changes/archive/2026-07-13-ecom-pedidos-hub-kanban-masivo-sucursales/`  
**Fecha:** 13/07/2026  
**Estado:** archivado (verify PASS WITH WARNINGS)

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

## Schema / permisos (Phase 0–1)

- Permisos: `ecom.pedido_masivo.usar`, `ecom.config_vendedor_cliente_marca`
- MySQL: proveedor `ecom_vendedor_cliente_marca` (`ecom/sql/001_ecom_vendedor_cliente_marca.sql`)
- Postgres: `EcomPedidoMasivoDraft` + `EcomPedidoMasivoDraftCelda`
- Stubs menú: `/pedido-masivo-sucursales/`, `/config/vendedor-cliente-marca/` (UI completa Phase 2/4)