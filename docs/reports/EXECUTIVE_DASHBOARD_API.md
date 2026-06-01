# API Dashboard gerencial (solo lectura)

Contrato **`executive-dashboard-v1`**. Datos desde MySQL AdministraNET (`base_empresa` en sesión).

## UI Command Center

- **Ruta:** `/reports/dashboard/command-center-gerencial/`
- **Plantilla:** `reports/templates/reports/command_center.html`
- **JS:** `reports/static/reports/js/command_center.js`
- **Inicio Synap:** la tarjeta hero en `/core/dashboard/` solo se muestra con permiso **`reports.view_managerial`** y **`ReportDefinition.is_visible=True`** para el slug `command-center-gerencial`. Si el informe está desactivado en el catálogo, solo lo ve el usuario **`cod_usuario=supervisor`** (no el puesto Supervisor).
- **CRM:** deprecado — no se muestra en la UI ni en el payload del orquestador.
- **Móvil:** allowlist `MobileLevelAOnlyMiddleware`: `/core/dashboard/`, `/reports/`, `/reports/workspace/`, `/reports/dashboard/command-center-gerencial/` y APIs `executive-dashboard` / `executive-summary` (UI responsive en `dashboard.html` y `command_center.html`).

### Etiquetas UI (área `cruzados` en API)

En Command Center el bloque `areas.cruzados` se muestra como **Demanda pendiente** (subtítulo: pendientes, reservas y cobertura vs facturación). Las rutas API siguen el slug técnico `cruzados`. Métricas visibles: Backorder ($), Unidades pendientes, Stock reservado, Demanda cubierta (%). El detalle paginado equivale al informe `bo-stock-facturacion` por artículo.

## Permiso

`ManagerialReportsPermission` en todas las rutas.

## Rutas P0

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reports/executive-dashboard/` | Orquestador por área |
| GET | `/api/reports/executive-dashboard/ventas/resumen/` | Ventas netas, REM, PED (período) |
| GET | `/api/reports/executive-dashboard/inventario/resumen/` | Stock agregado (`valor_stock` = saldo × `PrecioCosto`) |
| GET | `/api/reports/executive-dashboard/compras/resumen/` | OC pendientes |
| GET | `/api/reports/executive-dashboard/manufactura/resumen/` | KPIs MPR (solo si módulo `mpr` activo) |
| GET | `/api/reports/executive-dashboard/cruzados/resumen/` | Demanda pendiente (BO, reservado, cobertura) |
| GET | `/api/reports/executive-dashboard/tesoreria/resumen/` | Tesorería **caja** (saldos, flujos, subcategorías); `banco_disponible: false` en P0 |
| GET | `/api/reports/executive-dashboard/ventas/cobros/resumen/` | Facturado por medio vs cobrado en caja |

**Ventas del día (intradía):** `GET /api/reports/executive-summary/` — spec `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md`.

### Tesorería (caja)

- **Fuente única de reglas:** `reports/services/executive_dashboard/caja_classification.py` (SQL + clasificación Python compartida con `cash_flow_*`).
- Saldos desde último `caja.Saldo` por `id_caja_abm_origen` (`sum_saldo_cajas`).
- **`saldo_final`** (y `saldo_final_coherente`): saldo inicial + variación neta — **paridad `cash_flow_waterfall`**.
- **`saldo_final_sistema`**: suma de saldos reales en BD al cierre del período.
- **`drift_sistema`**: diferencia sistema − coherente (drift legacy en `caja.Saldo`).
- Neto operativo **excluye** cierres, transferencias entre cajas e inversión/financiamiento (mismo criterio que waterfall).
- Subcategorías alineadas AdministraNET: ventas (FA/FB/…/TARJ), cobranzas (REC, CHEQ cliente, MCAJ cobro), proveedores (OP, FA/FB proveedor, **CHEQ entrega proveedor**, NCA).
- **No** incluye `librobanco` en P0 (`meta.notas_semanticas`).

Verificación: `python manage.py uat_tesoreria_cashflow --base <empresa> --fecha-inicio … --fecha-fin …`

### Inventario

- **`valor_stock`**: `SUM(stock_deposito.saldo × articulo.PrecioCosto)` — valorización a **costo** (paridad AdministraNET Info_Stock con `lista_precio=0`).
- Snapshot de saldo actual; el período del dashboard no altera el valor (sí aplica a reservado / bajo mínimo vía `cp_res.Fecha`).

### Ventas por cobro

- `facturado_por_medio`: `resumen_venta_cv` + fallback `cuentacliente` (FA–FM sin resumen).
- `cobrado_caja_por_medio`: ingresos en `caja` clasificados por medio (heurística `caja_classification`).
- Facturado en cuenta corriente ≠ cobrado en el mismo período si la venta es a plazo.

## Rutas P1 (detalle paginado)

| Método | Ruta | Respuesta |
|--------|------|-----------|
| GET | `/api/reports/executive-dashboard/ventas/pedidos-pendientes/` | `filas`, `total_registros`, `total_monto`, `limit`, `offset` |
| GET | `/api/reports/executive-dashboard/ventas/remitos-no-facturados/` | Igual |
| GET | `/api/reports/executive-dashboard/cruzados/backorder/` | Filas BO por artículo + `total_monto` (suma bo_importe) |
| GET | `/api/reports/executive-dashboard/inventario/existencias/` | Filas stock por depósito (sin `total_monto`); búsqueda opcional |

## Query params comunes

- `fecha_inicio`, `fecha_fin` (default: **hoy** / hoy)
- `fecha` (opcional, legacy): atajo de un solo día (`inicio` = `fin` = `fecha`)
- `sucursal` (int; vacío = todas)
- `limit` (1–500, default 100) — solo P1
- `offset` (≥ 0, default 0) — solo P1
- `busqueda` o `q` (mín. 2 caracteres, máx. 120) — solo existencias: filtra por artículo, código, manual, depósito, marca, rubro, subrubro

### Período por área (`fecha_inicio` / `fecha_fin`)

| Área | Criterio de fecha |
|------|-------------------|
| Ventas, Tesorería, Ventas/cobros, Cruzados | Comprobantes / movimientos en período |
| Compras | `cuentaproveedor.Fecha` de OC pendientes |
| Inventario | Snapshot saldo actual; **reservado** y **bajo mínimo** filtran PED por `comp_ped.Fecha` |
| Manufactura | `comp_ped.Fecha` (pedidos fábrica); demanda/OPT por pedido vinculado o `fecha_objetivo` |

**UI Command Center:** solo **Desde / Hasta** (default ambos = hoy). Enlaces a informes (p. ej. Panel del día, **Flujo de caja** desde Tesorería → `cash_flow_waterfall`) propagan `fecha_inicio`, `fecha_fin` y `sucursal` en la URL. El bloque **Manufactura**, el KPI **OPT atrasadas** y el enlace **Tablero MPR** solo se muestran si `ModuleConfig` tiene `mpr` activo (`meta.modulos.mpr` en el orquestador).

## Performance (may. 2026)

Diagnóstico sobre `administranet93` (mes vigente): el cuello de botella era `_sum_saldo_cajas` en tesorería — subconsulta correlacionada sobre `caja` (~640k filas) superaba 5 min y abortaba todo el orquestador.

**Corrección P0:**

- `_sum_saldo_cajas` reescrito con `MAX(fecha)` + `MAX(codigo_movimiento)` por `id_caja_abm_origen` (compatible MySQL 5.7).
- Errores SQL por área aislados en `run_command_center` (`_safe_legacy_area` + `legacy_cursor` sin envolver excepciones de queries).

Tiempos orientativos post-fix (misma base, período mes): ventas ~0,7 s, inventario ~0,4 s, tesorería ~2 s, total orquestador ~3 s.

**Carga UI (P1, may. 2026):** el frontend ya no bloquea con modal de espera ni espera al orquestador monolítico. Consulta en **paralelo** cada endpoint de área (`areaUrls` en plantilla) y pinta tarjetas al llegar cada respuesta. El `executive-summary` (ventas del día + sucursales) se dispara en **segundo plano** sin bloquear el grid. Fallback: si no hay `areaUrls`, usa `GET /api/reports/executive-dashboard/`.

## Código

- Servicios: `reports/services/executive_dashboard/`
- Vistas: `reports/executive_dashboard_api_views.py`
- OpenSpec: `openspec/changes/dashboard-gerencial-endpoints-legacy/`

## Tests

```bash
docker exec Synap_app python manage.py test reports.tests.test_executive_dashboard_contract reports.tests.test_caja_classification
```

OpenSpec cambio financiero: `openspec/changes/adminnet-module-migration-command-center-finance/`.
