# Tasks: Workflow límite de crédito en pedidos

> TDD estricto: pares RED→GREEN. Runner: `docker exec Synap_app python manage.py test ecom`.
> Pendientes de producto **cerrados** (ver `design.md` §Decisiones cerradas).

## Fase 0 — Infraestructura

- [x] 0.1 **RED** — `test_credito_pedidos_ddl.py`: tablas política/evaluación/evento/plantilla/aviso_log; cols `comp_ped` (`credito_hold_prep`, `estado_credito_finanzas`); proveedor `ecom_credito_pedidos`.
- [x] 0.2 **GREEN** — `catalog.py`: `run_ecom_credito_pedidos_mysql` + `PROVIDER_REGISTRY`; flags `configuracion_ecom` (master, hold, **SLA horas default 24**). **Dep:** 0.1
- [x] 0.3 **GREEN** — `ecom_config_mysql.py`: flags master/hold/SLA + helpers. **Dep:** 0.2
- [x] 0.4 **RED** — `test_credito_pedidos_permisos.py`: seed `finance.credito.aprobar` + **`finance.credito.configurar`**, comodines, specs permisos/roles.
- [x] 0.5 **GREEN** — `constantes_permisos.py` + `ecom/permissions.py` `puede_aprobar_credito()` / `puede_configurar_credito()`. **Dep:** 0.4

## Fase A — Evaluación, checkout, semáforo, matriz

- [x] A.1 **RED** — `test_credito_pedidos_politica.py`: `resolver_politica(cliente, canal)`. **Dep:** 0.2
- [x] A.2 **GREEN** — `credito_pedidos/politica.py` + `__init__.py`. **Dep:** A.1
- [x] A.3 **RED** — `test_credito_pedidos_exposicion.py`: capas ON/OFF; `Credito=0`. **Dep:** A.2
- [x] A.4 **GREEN** — `credito_pedidos/exposicion.py`: `calcular_exposicion()`. **Dep:** A.3
- [x] A.5 **RED** — `test_credito_pedidos_evaluacion.py`: `evaluar_pedido`, semáforo, snapshot. **Dep:** A.4
- [x] A.6 **GREEN** — `credito_pedidos/evaluacion.py`. **Dep:** A.5
- [x] A.7 **RED** — `test_credito_pedidos_checkout.py`: REQ-CHK-004 flag ON/OFF; alta no bloqueada. **Dep:** A.6, 0.3
- [x] A.8 **GREEN** — `mayorista_checkout_service.py` evaluador unificado; `mayorista_credito.py` fallback. **Dep:** A.7
- [x] A.9 **RED** — `test_pedido_masivo_matriz_credito.py`: fix naming `$` vs días. **Dep:** A.4
- [x] A.10 **GREEN** — `pedido_masivo_matriz.py` fix `credito_cliente_masivo()`. **Dep:** A.9
- [x] A.11 **RED** — `test_credito_pedidos_precheck.py`: REQ-VTA-10/11; modal Synap. **Dep:** A.6
- [x] A.12 **GREEN** — `credito_views.py` pre-check; `urls.py`; relay + `pedidos_order_header.html` semáforo. **Dep:** A.11

## Fase B — Finanzas, hold, avisos, UI, hub

- [x] B.1 **RED** — `test_aprobacion_pedidos_credito_desacople.py`: retiro `_REGLA_CREDITO`; REQ-APR-02. **Dep:** A.8
- [x] B.2 **GREEN** — `aprobacion_pedidos.py` desacople crédito/comercial. **Dep:** B.1
- [x] B.3 **GREEN** — Hold prep Synap: set/clear `credito_hold_prep`; gate transición «En preparación» si hold=`Si`; doc contrato VB6 `Pedido_prep` en `docs/ecom/` (ADR 9). **Dep:** 0.2, B.5
- [x] B.4 **RED** — `test_credito_pedidos_aprobacion.py`: cola Finanzas; no mutar `cliente.Credito`. **Dep:** B.2, 0.5
- [x] B.5 **GREEN** — `credito_pedidos/aprobacion.py`: eventos, hold, liberar PED. **Dep:** B.4
- [x] B.6 **RED** — `test_credito_pedidos_hub.py`: columna Finanzas; REQ-HUB-02/11. **Dep:** B.5
- [x] B.7 **GREEN** — `pedidos_hub_pipeline.py` + `pedidos_hub.html` CTAs gateadas. **Dep:** B.6
- [x] B.8 **RED** — `test_credito_pedidos_avisos.py`: plantillas, `EcomMailQueue`, dedup **24 h** + 1× `pedido_bloqueado` por PED. **Dep:** 0.2, 0.3
- [x] B.9 **GREEN** — `credito_pedidos/avisos.py` (SLA ADR 7b). **Dep:** B.8
- [x] B.10 **GREEN** — Gate ABM con `finance.credito.configurar`; cola con `finance.credito.aprobar` (ADR 8). **Dep:** 0.5
- [x] B.11 **GREEN** — Templates `ecom/credito/*` look Alta Movimiento. **Dep:** B.10, B.5
- [x] B.12 **GREEN** — `credito_views.py` ABM políticas, cola, plantillas + rutas. **Dep:** B.11

## Fase C — Regresión, docs

- [x] C.1 Regresión suites flag OFF. **Dep:** A.8, B.2
- [x] C.2 Integración marker `integration`: checkout→Finanzas→aprobar. **Dep:** B.12, B.3
- [x] C.3 `docs/ecom/CREDITO_PEDIDOS_WORKFLOW.md` (incl. §bridge VB6 + SLA + permisos). **Dep:** C.1

**Orden:** 0→A→B.1-2→B.4-5→B.3∥B.6-12→C.*

**Riesgos residuales:** R3 paridad exposición Dynamics (validar snapshots fase A); R4 perf lote masivo; parche VB6 `Pedido_prep` es companion documentado (fuera del árbol Python Synap).
