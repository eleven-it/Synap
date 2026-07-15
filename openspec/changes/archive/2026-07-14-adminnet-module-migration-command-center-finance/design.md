# Design: Command Center — tesorería y ventas por cobro

**Cambio:** `adminnet-module-migration-command-center-finance`  
**Specs:** `reports-executive-dashboard-tesoreria`, `reports-executive-dashboard-ventas-cobros`, delta `reports-executive-dashboard`

---

## Technical Approach

Extender el módulo existente `reports/services/executive_dashboard/` con dos servicios de métricas read-only MySQL, vistas DRF y tarjetas en Command Center. Reutilizar clasificación de `query_runner` **sin** invocar `POST /api/reports/query/`. Impuestos fuera de alcance.

---

## Architecture Decisions

| Decisión | Elección | Alternativa rechazada | Rationale |
|----------|----------|----------------------|-----------|
| Saldo caja P0 | Último `caja.Saldo` por `id_caja_abm_origen` | `caja_saldo.Saldo` | Paridad con `cash_flow_waterfall` ya validado en reports |
| Caja vs banco | Endpoints separados; P0 solo caja | KPI único “tesorería” | Evita doble conteo caja→depósito |
| Clasificación movimientos | Extraer `_classify_movement` / `_get_payment_method` a módulo compartido | Duplicar SQL en metrics | Un solo lugar de verdad |
| Neto consolidado | Excluir `Cierre de Caja` y `Transferencia de Fondos` | Sumar todo | Ya implementado en waterfall |
| Facturado por medio | `resumen_venta_cv` + fallback `cuentacliente` | Solo `caja` | Cta cte facturada no está en caja al emitir |
| Cobrado por medio | Agregado `caja` + `_get_payment_method` | `medio_cobpag` en P0 | Sin uso en reports hoy; P1 detalle |
| Orquestador | `_safe_legacy_area` para nuevas áreas | Fail-fast total | Consistente con inventario/compras |
| UI | Dos tarjetas MPR/reportes; sin impuestos | Reusar patrón ventas legacy | Canon `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` |

---

## Data Flow

```text
GET executive-dashboard/*
        │
        ▼
ExecutiveDashboard*APIView (ExecutiveDashboardMixin)
        │
        ├─ resolve_filters_from_query_params → DashboardFilters
        │
        └─ legacy_cursor(base_empresa)
                │
                ├─ fetch_tesoreria_resumen(cursor, filters)
                │       └─ SQL caja + caja_abm (saldos, flujos, por_tipo_caja)
                │
                ├─ fetch_ventas_cobros_resumen(cursor, filters)
                │       ├─ SQL resumen_venta_cv + cuentacliente
                │       └─ SQL caja (ingresos, medio)
                │
                └─ run_command_center → areas.tesoreria | ventas_cobros
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `reports/services/executive_dashboard/caja_classification.py` | Create | `classify_movement`, `get_payment_method` (movidos desde `query_runner`) |
| `reports/services/query_runner.py` | Modify | Importar helpers desde `caja_classification` (re-export o delegación) |
| `reports/services/executive_dashboard/tesoreria_metrics.py` | Create | `fetch_tesoreria_resumen` |
| `reports/services/executive_dashboard/ventas_cobros_metrics.py` | Create | `fetch_ventas_cobros_resumen` |
| `reports/services/executive_dashboard/command_center.py` | Modify | Áreas + `ENDPOINTS_RELATIVOS` |
| `reports/executive_dashboard_api_views.py` | Modify | 2 vistas resumen |
| `reports/api_urls.py` | Modify | Rutas P0 |
| `reports/templates/reports/command_center.html` | Modify | Tarjetas tesorería y ventas cobro |
| `reports/static/reports/js/command_center.js` | Modify | Render KPIs; cache bust |
| `reports/tests/test_executive_dashboard_contract.py` | Modify | Contrato JSON + mocks |
| `docs/reports/EXECUTIVE_DASHBOARD_API.md` | Modify | Contratos y ejemplos |

---

## Interfaces / Contracts

### `fetch_tesoreria_resumen(cursor, filters) -> dict`

Retorna campos REQ-ED-TES-02–07 + `disponible` + `meta` vía `build_meta` en la vista.

Filtro sucursal: `AND c.cod_sucursal = %s` cuando `filters.cod_sucursal` no es None.

Exclusión interna (SQL CASE o post-filtro):

```python
EXCLUIR_TIPOS_INTERNO = ("%Cierre de Caja%", "%Transferencia de Fondos%")
```

### `fetch_ventas_cobros_resumen(cursor, filters) -> dict`

Buckets fijos; montos `Decimal` → `float` con 2 decimales en serialización JSON.

### URLs (P0)

```text
GET /api/reports/executive-dashboard/tesoreria/resumen/
GET /api/reports/executive-dashboard/ventas/cobros/resumen/
```

Nombres DRF sugeridos: `ExecutiveDashboardTesoreriaResumenAPIView`, `ExecutiveDashboardVentasCobrosResumenAPIView`.

---

## UI (Command Center)

| Tarjeta | Contenido |
|---------|-----------|
| **Tesorería (caja)** | Saldo ini/fin, variación neta, filas: ventas / cobranzas / proveedores; nota “No incluye bancos” si `banco_disponible=false` |
| **Ventas por cobro** | Dos columnas o bloques: Facturado por medio \| Cobrado en caja |

Patrón visual: mismos includes que `command_center.html` existente (cards reportes/MPR). Textos en español.

---

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Exclusión tipos internos, buckets medio | Tests puros sobre helpers de clasificación |
| Contract | Shape JSON endpoints + orquestador | `test_executive_dashboard_contract.py` con `@patch legacy_cursor` |
| Integration | SQL opcional empresa dev | Manual UAT vs `cash_flow_waterfall` mismo período |

Comando: `docker exec Synap_app python manage.py test reports.tests.test_executive_dashboard_contract`

---

## Migration / Rollout

No migration required. Despliegue por rama; cache bust en `command_center.js`. P1 banco documentado sin implementar.

---

## Open Questions

- [ ] Confirmar en empresa piloto si todas las FB fuera TPV graban `resumen_venta_cv`
- [ ] Validar totales Serie facturado vs informe estadístico legacy (UAT negocio)
