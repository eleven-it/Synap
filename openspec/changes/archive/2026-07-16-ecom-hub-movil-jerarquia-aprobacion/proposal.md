# Proposal: Hub pedidos móvil + jerarquía comercial y aprobación

**Change:** `ecom-hub-movil-jerarquia-aprobacion` · **Fecha:** 16/07/2026

## Intent

Mobile-first del hub mayorista de pedidos; reemplazar carteras ad-hoc (`ecom_vendedores_a_cargo_*` JSON) por jerarquía formal Gerente→Supervisor→Vendedor (árbol 1 padre); workflow comercial opcional con aprobación de pedidos y alcance org unificado en hub, objetivos e informe ventas-objetivos-vs-bo.

## Scope

### In Scope
- Hub `<lg` chips/cards; `≥lg` kanban; menú PWA hub+venta (Nivel A)
- Master `ecom_workflow_jerarquia_comercial` (default No)
- Tablas `ecom_org_gerente_supervisor`, `ecom_org_supervisor_vendedor`; ABM en Ajustes; migración JSON
- Helper `alcance_viajantes_comercial` (hub, aprobación, objetivos)
- Subflag `ecom_aprobacion_pedidos_activa`; motor reglas (monto, desc pie/renglón, crédito_no_autorizado, cliente_nuevo); estado aparte de `autorizacion_sistema`; routing Supervisor→Gerente; APIs aprobar/rechazar
- Workflow ON: objetivos CRUD + informe scoped por árbol; OFF: solo vendedor propio (actual)
- Ajustes: flags workflow/aprobación; atajos hub objetivos/backorder
- Permisos: `ecom.pedidos.ver_todos`, `ecom.pedidos.aprobar`, `ecom.jerarquia.editar`

### Out of Scope
- Relación N:M mesh org; cascada top-down editable de cuotas; masivo en móvil; reescritura VB6 crédito

## Capabilities

### New Capabilities
- `ecom-jerarquia-comercial`: DDL org, ABM, migración JSON, resolver alcance
- `ecom-aprobacion-pedidos`: reglas, estados comerciales, routing S/G, APIs
- `ecom-hub-pedidos-mobile`: UI responsive mobile-first, PWA menú, columnas aprobación
- `ecom-objetivos-alcance-jerarquia`: scope CRUD objetivos + informe por árbol
- `ecom-ajustes-workflow-comercial`: flags master/sub y atajos hub

### Modified Capabilities
- `ecom-pedidos-hub-kanban`: columnas/filtros aprobación + layout mobile
- `ecom-vendedor-operativo`: alcance vía helper org cuando workflow ON
- `ecom-gestion-pedidos-navegacion`: entrada mobile/PWA y deep links

## Approach

DDL en `catalog.py`. Flags en `configuracion_ecom` vía Ajustes. Servicio `alcance_viajantes_comercial(base, ctx)`: workflow OFF → comportamiento actual (JSON/`[cv]`); ON → recorre árbol según rol (vendedor/supervisor/gerente) + `ecom.pedidos.ver_todos`. Aprobación: campos/estado comercial separados de `autorizacion_sistema`; checkout evalúa reglas; hub expone cola pendiente. UI canon MPR/reports. Middleware Nivel A: hub, venta, APIs aprobación. Informe: filtrar vendedores en `ventas_objetivos_bo_runner` por alcance.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `core/services/legacy_mysql_schema/catalog.py` | New | Tablas org + índices |
| `ecom/services/vendedor_operativo.py` | Modified | Delegar alcance |
| `ecom/services/pedidos_hub_pipeline.py` | Modified | Filtros aprobación/alcance |
| `ecom/templates/ecom/pedidos_hub.html` | Modified | Mobile-first |
| `ecom/ajustes_ventas_views.py` | Modified | Flags workflow |
| `ventas/` + `reports/services/ventas_objetivos_bo_runner.py` | Modified | Alcance objetivos |
| `core/constantes_permisos.py` | Modified | Permisos nuevos |
| `core/middleware/mobile_level_a_middleware.py` | Modified | Rutas aprobación |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Migración JSON incompleta | Med | Comando backfill; fallback OFF |
| Colisión autorización sistema vs comercial | Med | Estados/campos separados |
| Performance informe árbol grande | Med | Cache alcance; filtros SQL |

## Rollback Plan

1. Flags master/sub → No en Ajustes (instantáneo).
2. Código usa path legacy JSON + filtros actuales.
3. Tablas org quedan; no se eliminan en rollback.

## Dependencies

`configuracion_ecom`, sesión mayoristapp, hub kanban existente, informe ventas-objetivos-vs-bo.

## Success Criteria

- [x] Hub usable móvil Nivel A (`<lg` cards)
- [x] ABM jerarquía + migración JSON verificada
- [x] Aprobación ON enruta S→G; OFF sin regresión
- [x] Objetivos/informe scoped por árbol con workflow ON
- [x] Permisos aplicados hub/APIs/Ajustes
