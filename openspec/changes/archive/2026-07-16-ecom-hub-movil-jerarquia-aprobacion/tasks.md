# Tasks: Hub pedidos móvil + jerarquía comercial y aprobación

**Change:** `ecom-hub-movil-jerarquia-aprobacion` · **Estado:** 35/35 completadas

## Phase 1: Organigrama DDL + migrate JSON + ABM + alcance helper

- [x] 1.1 Provider `ecom_jerarquia_aprobacion` en catalog.py
- [x] 1.2 `ecom/services/jerarquia_comercial.py`
- [x] 1.3 Comando `migrar_carteras_a_jerarquia` + backfill provider
- [x] 1.4 `ecom/services/alcance_comercial.py`
- [x] 1.5 `vendedor_operativo.py` delega alcance cuando ON
- [x] 1.6 Permisos `ecom.jerarquia.editar`, `ecom.pedidos.aprobar`
- [x] 1.7 API ABM jerarquía
- [x] 1.8 UI ABM en ajustes_ventas.html
- [x] 1.9 Tests jerarquía/alcance

## Phase 2: Hub mobile UI + PWA + pipeline scope

- [x] 2.1 `pedidos_hub_pipeline.py` filtro alcance
- [x] 2.2 `pedidos_hub.html` mobile chips+cards
- [x] 2.3 API hub payload mobile
- [x] 2.4 Middleware Nivel A
- [x] 2.5 PWA menú hub+venta
- [x] 2.6 Tests pipeline + middleware

## Phase 3: Ajustes flags

- [x] 3.1 Claves workflow/aprobación/umbrales
- [x] 3.2 UI toggles workflow
- [x] 3.3 API `AjustesWorkflowAPIView`
- [x] 3.4 Tests ajustes workflow

## Phase 4: Approval engine + APIs + hub bandeja

- [x] 4.1 `aprobacion_pedidos.py`
- [x] 4.2 Hook checkout `confirmar`
- [x] 4.3 APIs aprobación
- [x] 4.4 Pipeline columna comercial
- [x] 4.5 Hub UI CTA aprobar/rechazar
- [x] 4.6 Tests aprobación + checkout

## Phase 5: Objetivos + informe scope

- [x] 5.1 `objetivos_mysql.py` alcance org
- [x] 5.2 `ventas_objetivos_bo_runner.py` filtro alcance
- [x] 5.3 Tests objetivos + informe

## Phase 6: Docs + tests

- [x] 6.1 Docs `docs/ecom/`
- [x] 6.2 Docs `docs/general/`
- [x] 6.3 Test migración JSON
- [x] 6.4 Test E2E API flujo aprobación
- [x] 6.5 Suite ecom+core+reports
