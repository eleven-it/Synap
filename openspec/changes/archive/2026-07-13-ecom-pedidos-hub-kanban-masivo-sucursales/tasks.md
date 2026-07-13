# Tasks: ecom-pedidos-hub-kanban-masivo-sucursales

## Phase 0 — Docs + permisos seed

- [x] 0.1 `docs/ecom/PEDIDOS_HUB_KANBAN.md` (home Lista|Kanban, estados, recuperación)
- [x] 0.2 `docs/ecom/VENDEDOR_CLIENTE_MARCA.md` (ternas, solape, permisos)
- [x] 0.3 `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` (matriz, borrador, batch/rollback)
- [x] 0.4 Registrar permisos Synap: `ecom.pedido_masivo.usar`, `ecom.config_vendedor_cliente_marca` (+ menú)

## Phase 1 — Schema + modelos

- [x] 1.1 DDL `ecom/sql/` + proveedor `legacy_mysql_schema` para `ecom_vendedor_cliente_marca` (unique cliente+marca)
- [x] 1.2 (Si hace falta) `ecom_usuario_viajante` + resolver en login/sesión
- [x] 1.3 Modelos Postgres `EcomPedidoMasivoDraft` + celdas; migración Django
- [x] 1.4 Tests unitarios unique / estados draft

## Phase 2 — Config Vendedor→Cliente→Marca

- [x] 2.1 Servicios CRUD + detección dueño en conflicto (409)
- [x] 2.2 Vista/template config (canon tablero / MPR list)
- [x] 2.3 URLs + permiso + tests

## Phase 3 — Hub Lista | Kanban (refactor `/pedidos/`)

- [x] 3.1 `pedidos_hub_pipeline.py`: unificar borradores + PED por columna
- [x] 3.2 Refactor `pedidos_hub.html` → shell tablero + toggle Lista/Kanban
- [x] 3.3 CTA Nuevo (Simple | Masivo); modal recuperar/archivar borrador
- [x] 3.4 API JSON hub (paginación, filtros vendedor)
- [x] 3.5 Tests hub + smoke template

## Phase 4 — Matriz pedido masivo

- [x] 4.1 Vistas/rutas `/pedido-masivo-sucursales/`
- [x] 4.2 API: cliente→sucursales; catálogo filtrado por ternas; autoguardado celdas
- [x] 4.3 UI matriz sticky (canon `tablero_produccion`)
- [x] 4.4 Tests catálogo filtrado + autoguardado

## Phase 5 — Batch checkout + resiliencia

- [x] 5.1 `batch_checkout_masivo` reutilizando `mayorista_checkout_service`
- [x] 5.2 Validación previa + compensación/anulación en fallo
- [x] 5.3 Draft CONFIRMANDO → BORRADOR+errores | CONFIRMADO+links
- [x] 5.4 Tests integración: OK N PED; fail mid-lote → 0 netos + draft intacto

## Phase 6 — Verify

- [x] 6.1 Suite ecom en `docker exec Synap_app`
- [x] 6.2 Checklist manual hub → continuar borrador → confirmar / fallar
- [x] 6.3 `sdd-verify` / verify-report
