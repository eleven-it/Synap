# Exploración — Endpoints dashboard gerencial (legacy AdministraNET)

**Cambio:** `dashboard-gerencial-endpoints-legacy`  
**Modo:** Migration Mode (capa nueva de lectura; sin tocar pantallas)  
**Metodología:** `adminnet-module-migration` — separación Application / Legacy  
**Fecha:** 11/05/2026

---

## 1. Objetivo de la exploración

Identificar **qué endpoints existen**, **qué lógica legacy ya está implementada** (reutilizable) y **qué GAPs** hay respecto a un API de dashboard gerencial **solo obtención de datos** (sin migración de UI).

Referencia de brechas funcionales: `docs/audits/dashboard-administranet-gap-analysis.md`.

---

## 2. Patrones existentes en Synap

| Patrón | Ubicación | Uso |
|--------|-----------|-----|
| API dedicada + servicio agregado | `executive_summary_api_views.py` → `executive_sales_summary.py` | **Modelo a seguir** para KPIs dashboard |
| API relay GET + query params | `ventas_netas_relay_views.py` → `ventas_netas.py` | Listados/detalle ventas por período |
| API informe genérico POST | `ReportQueryAPIView` + `QueryRunnerService` | Requiere `ReportDefinition.slug` + payload; retorna grilla `QueryResult` |
| Pool MySQL por empresa | `reports/services/connection_pool.py` | `base_empresa` desde sesión |
| Permiso gerencial | `ManagerialReportsPermission` | Todos los endpoints propuestos |
| Tipos legacy | `core.utils.administranet_types` | Normalización INT/DATE/DECIMAL |
| Manufactura | `mpr/services.py`, `mpr/views.TableroView` | KPIs en contexto servidor HTML, **sin API REST de tablero** |

---

## 3. Endpoints existentes relevantes

| Método | Ruta | Qué devuelve | ¿Sirve dashboard gerencial? |
|--------|------|--------------|----------------------------|
| GET | `/api/reports/executive-summary/` | KPIs ventas **día**, series, margen, top 10, split PV | **Parcial** — solo ventas intradía |
| GET/PUT | `/api/reports/pv-canal-ejecutivo/` | Clasificación PV (PostgreSQL Synap) | Config, no KPI |
| POST | `/api/reports/query/` | Cualquier slug `ReportDefinition` | **Parcial** — contrato grilla, pesado |
| GET | `/api/reports/ventas-netas/relay/` | Ventas netas listado | Operativo vendedor |
| GET | `/api/reports/ventas-netas/relay/gerencia/` | Variante gerencia | Operativo |

**No encontrado:** `/api/reports/executive-dashboard/`, `/api/reports/command-center/`, endpoints por área (compras, inventario, crm, manufactura).

---

## 4. Lógica legacy ya implementada (reutilizable sin reescribir SQL)

### 4.1 Ventas — `executive_sales_summary.py`

| Función / bloque | Tablas | Granularidad |
|------------------|--------|--------------|
| `_ventas_netas_dia`, series, tickets | `cuentacliente` | Día |
| `_unidades_dia`, `_top_productos_*` | `stock` + `cc` | Día |
| `_margen_bruto_*`, rubro/subrubro | `stock`, `articulo`, `rubro`, `subrubro` | Día |
| `_split_canal` | `cc` + PG `PuntoVentaCanalEjecutivo` | Día |

### 4.2 Ventas — métodos en `query_runner.py` (instancia `QueryRunnerService`)

| Método | Equivalente KPI gerencial | Notas |
|--------|---------------------------|-------|
| `_get_ventas_netas_total` | Ventas confirmadas / netas período | `fecha_inicio`, `fecha_fin`, sucursal, PV |
| `_get_remitos_no_facturados_total` | Pendiente facturar | `comp_ped` REM Pendiente |
| `_get_pedidos_pendientes_total` | Pedidos pendientes entrega | PED; `filtrar_por_fecha` opcional |
| `_run_sales_summary` | Resumen ventas período | Combina los tres anteriores |
| `_run_total_consolidado_operativo` | Vista consolidada operativa | Suma VN+REM+PED |
| `_run_pending_orders` | Detalle pedidos pendientes | Tabla filas |
| `_run_uninvoiced_remitos` | Detalle remitos NF | Tabla filas |
| `_run_ventas_netas` | Ventas netas detalle/agregado | Informe completo |

### 4.3 Inventario / cruzado

| Método slug | KPIs |
|-------------|------|
| `_run_stock_existencias` | Valor stock, existencias por depósito |
| `_run_backorder_vs_stock_vs_facturacion` | Demand coverage, backlog, reservado, OC pendiente (detalle hasta 1000 filas) |

### 4.4 Manufactura — `mpr/`

| Fuente | KPIs |
|--------|------|
| `TableroView.get_context_data` | pedidos pendientes, OPT atrasadas, unidades pendientes, urgentes |
| `_run_mpr_opt_atrasadas`, `_run_mpr_pedidos_estado`, `_run_mpr_brecha_demanda` | Informes catálogo |

### 4.5 Compras

| Fuente | Estado |
|--------|--------|
| Joins `cuentaproveedor` / `proveedor` en cash flow y BO | **Parcial** — no hay totales gerenciales |
| Módulo `compras/` | Captura factura — **no KPI** |

### 4.6 CRM / Pre-venta

| Fuente | Estado |
|--------|--------|
| Tablas `crm_*` en `docs/general/tablas/` | Documentadas |
| Código Synap UI/API | **No encontrado** |
| Menú CRM | Comentado en `core/utils/utils.py` |

---

## 5. Mapa de GAPs → endpoints necesarios

### Leyenda

- **REUSAR** — exponer vía nuevo wrapper HTTP sin duplicar SQL  
- **EXTRAER** — sacar lógica de `QueryRunnerService` a servicio dedicado + endpoint  
- **NUEVO** — SQL/servicio aún no existe  
- **BLOQUEADO** — requiere definición funcional / tablas CRM  

### 5.1 Nivel CEO — Command Center (agregador)

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| E0 | `GET /api/reports/executive-dashboard/` | No existe orquestador | **NUEVO** servicio que compone sub-servicios | P0 |
| E0 | query: `fecha`, `fecha_inicio`, `fecha_fin`, `sucursal` | Filtros unificados | Alinear con executive-summary | P0 |

Payload objetivo (borrador): `areas.ventas`, `areas.inventario`, `areas.compras`, `areas.manufactura`, `areas.crm`, `meta`, `alertas[]` (vacío en v1).

### 5.2 Ventas

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| V1 | `GET .../executive-summary/` | Existe | **REUSAR** | — |
| V2 | `GET .../executive-dashboard/ventas/resumen/` | KPIs período (VN, REM, PED, total) | **EXTRAER** `_get_*_total` | P0 |
| V3 | `GET .../executive-dashboard/ventas/ventas-netas/` | Serie/agregado período | **EXTRAER** `_run_ventas_netas` simplificado | P1 |
| V4 | `GET .../executive-dashboard/ventas/pedidos-pendientes/` | Backlog entrega resumen + opción detalle | **EXTRAER** `_run_pending_orders` | P0 |
| V5 | `GET .../executive-dashboard/ventas/remitos-no-facturados/` | Pendiente facturar | **EXTRAER** | P1 |
| V6 | `GET .../executive-dashboard/ventas/backlog/` | KPIs backlog riesgo/vencido | **NUEVO** reglas sobre `comp_ped`/`stockp` | P2 |

### 5.3 Inventario

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| I1 | `GET .../executive-dashboard/inventario/resumen/` | Stock crítico, valor, quiebres | **EXTRAER** agregados de `_run_stock_existencias` | P0 |
| I2 | `GET .../executive-dashboard/inventario/existencias/` | Detalle paginado | **EXTRAER** con `limit`/`offset` | P1 |

### 5.4 Compras

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| C1 | `GET .../executive-dashboard/compras/resumen/` | OC pendientes, atrasadas | **NUEVO** `purchase_metrics.py` | P0 |
| C2 | `GET .../executive-dashboard/compras/oc-pendientes/` | Tabla accionable | **NUEVO** | P1 |

**Requiere validación funcional:** estados OC en `cuentaproveedor` (equivalente VB6).

### 5.5 Manufactura

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| M1 | `GET .../executive-dashboard/manufactura/resumen/` | OPT atrasadas, unidades | **EXTRAER** de `mpr/views` + services | P0 |
| M2 | `GET .../mpr/api/tablero/` (alternativa) | API bajo app mpr | **NUEVO** vista API en mpr | P1 |

### 5.6 CRM

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| R1 | `GET .../executive-dashboard/crm/resumen/` | Todo el área | **BLOQUEADO** — inventario VB6 + tablas `crm_*` | P2 |

Respuesta v1 recomendada: `crm.disponible: false`, `crm.motivo` en payload E0.

### 5.7 KPIs cruzados

| ID | Endpoint propuesto | GAP | Acción | Prioridad |
|----|------------------|-----|--------|-----------|
| X1 | `GET .../executive-dashboard/cruzados/resumen/` | Totales BO sin 1000 filas | **NUEVO** agregación sobre lógica BO | P0 |
| X2 | `GET .../executive-dashboard/cruzados/backorder/` | Detalle paginado | **EXTRAER** BO con paginación | P1 |

---

## 6. Riesgos detectados en exploración

1. **Duplicar SQL** si cada endpoint copia `query_runner` — viola mantenibilidad.  
2. **`ReportQueryAPIView`** como único mecanismo — contrato grilla no apto para cards KPI.  
3. **CRM sin dueño funcional** — bloquea forecast/pipeline.  
4. **Concurrencia / performance** — BO y existencias son pesados; endpoints deben ser agregados + paginación.  
5. **Semántica** — mismos nombres KPI que audit (venta facturada vs pedido).

---

## 7. Inserción arquitectónica recomendada (Application / Legacy)

```
reports/
  services/
    executive_dashboard/          # NUEVO — solo lectura legacy
      __init__.py
      base.py                     # base_empresa, pool, permisos helpers
      ventas_metrics.py           # EXTRAER de query_runner + executive_sales_summary
      inventory_metrics.py
      purchase_metrics.py         # NUEVO
      manufacturing_metrics.py    # delega mpr.services
      cross_metrics.py            # agregados BO
      command_center.py           # orquestador E0
  executive_dashboard_api_views.py
  api_urls.py                   # registrar rutas executive-dashboard/*
```

**Reglas (skill adminnet-module-migration):**

- Vistas API = Application layer únicamente.  
- SQL solo en `*_metrics.py` (Legacy read layer).  
- Sin escritura MySQL en esta fase.  
- Sin modificar contratos de informes existentes (`query/` sigue igual).

---

## 8. Criterios de aceptación exploración

- [x] Inventario endpoints actuales  
- [x] Mapa lógica reutilizable por área  
- [x] Lista GAPs con IDs y prioridades  
- [x] CRM marcado bloqueado  
- [x] Propuesta de estructura de módulo sin implementar aún  

---

## 9. Próximo paso SDD

**Propuesta** (`proposal.md`): alcance por fases, contrato JSON v1, fuera de alcance (UI), decisión sobre `POST /query/` vs GET dedicados.
