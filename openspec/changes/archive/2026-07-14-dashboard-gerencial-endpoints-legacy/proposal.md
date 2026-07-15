# Propuesta — API dashboard gerencial (solo lectura legacy)

**Cambio:** `dashboard-gerencial-endpoints-legacy`  
**Fecha:** 11/05/2026  
**Modo:** Migration Mode (nueva capa API; Evolution Mode para informes existentes — no romper `query/`)  
**Artefactos:** OpenSpec + Engram (`sdd/dashboard-gerencial-endpoints-legacy/*`)

---

## 1. Intención

Construir una **capa REST de solo lectura** que exponga los datos del dashboard gerencial desde **MySQL AdministraNET** (`base_empresa`), **sin migrar pantallas**, reutilizando al máximo la lógica probada en `executive_sales_summary.py` y `query_runner.py`.

La UI (Command Center, cards, semáforos) será **consumidora** de estos endpoints en una fase posterior.

---

## 2. Problema que resuelve

Hoy el gerente debe:

- Abrir **múltiples informes** (`/reports/dashboard/<slug>/`) o el panel de **solo ventas del día**.
- Usar **POST `/api/reports/query/`** con contratos de grilla no diseñados para KPIs.
- Ir a **`/mpr/`** aparte para manufactura.

No hay un contrato JSON estable para “estado de la operación” por área.

---

## 3. Alcance

### Incluido

- Nuevo namespace API bajo `/api/reports/executive-dashboard/`.
- Servicios `reports/services/executive_dashboard/*` con lectura MySQL legacy.
- Extracción controlada de agregados desde `QueryRunnerService` (sin duplicar SQL en vistas).
- Endpoint orquestador **P0** + endpoints por área **P0/P1**.
- Permiso `ManagerialReportsPermission` en todos los recursos.
- Contrato JSON versionado (`meta.definicion`: `executive-dashboard-v1`).
- Documentación de campos y semántica en spec (fase siguiente).
- Tests de contrato por endpoint (servicios con cursor mock, patrón `test_executive_summary_contract`).

### Fuera de alcance

- Pantallas HTML, React, Command Center UI.
- Escritura en MySQL legacy.
- Scores (Operational Health Score) — fase posterior.
- Motor de alertas / Action View.
- CRM completo hasta inventario funcional de tablas `crm_*` con negocio.
- Sustituir `ReportQueryAPIView` ni cambiar slugs de informes existentes.

---

## 4. Enfoque técnico

### 4.1 Principios (adminnet-module-migration)

| Capa | Responsabilidad |
|------|-----------------|
| **API views** | Parseo query params, permisos, respuesta HTTP |
| **`*_metrics.py`** | SQL + agregación legacy |
| **`command_center.py`** | Orquesta llamadas a sub-servicios (sin SQL propio pesado) |
| **PostgreSQL Synap** | Solo PV canal (`PuntoVentaCanalEjecutivo`) — ya existente |

### 4.2 Reutilización vs código nuevo

| Área | Estrategia |
|------|------------|
| Ventas día | **Sin cambios** — `GET /executive-summary/` |
| Ventas período | **Extraer** `_get_ventas_netas_total`, `_get_remitos_*`, `_get_pedidos_*` a `ventas_metrics.py` |
| Inventario | **Extraer** agregados de `_run_stock_existencias` |
| Compras | **Nuevo** `purchase_metrics.py` (patrón BO para OC) |
| Manufactura | **Wrapper** sobre funciones existentes en `mpr.services` |
| Cruzados | **Nuevo** `cross_metrics.py` con totales derivados de BO |
| CRM | **Stub** en orquestador (`disponible: false`) |

### 4.3 Filtros comunes (query params)

| Parámetro | Tipo | Uso |
|-----------|------|-----|
| `fecha` | date | Referencia única (modo día, compatible executive-summary) |
| `fecha_inicio`, `fecha_fin` | date | Período (default: mes en curso o últimos 30 días — cerrar en spec) |
| `sucursal` | int | `CodSucursal` / `id_sucursal` según contexto |
| `limit`, `offset` | int | Solo endpoints con detalle tabular |

`base_empresa` desde sesión (mismo patrón que `executive_summary_api_views._base_empresa`).

---

## 5. Catálogo de endpoints propuesto

### Fase P0 — MVP datos gerenciales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reports/executive-dashboard/` | Orquestador: resúmenes por área + meta |
| GET | `/api/reports/executive-dashboard/ventas/resumen/` | VN, remitos NF, pedidos pend., totales período |
| GET | `/api/reports/executive-dashboard/inventario/resumen/` | Valor stock, ítems bajo mínimo, quiebres (agregados) |
| GET | `/api/reports/executive-dashboard/compras/resumen/` | OC pendientes / críticas (v1) |
| GET | `/api/reports/executive-dashboard/manufactura/resumen/` | OPT atrasadas, unidades pendientes |
| GET | `/api/reports/executive-dashboard/cruzados/resumen/` | Totales backlog / demand coverage (sin detalle masivo) |

**Existente (no duplicar):** `GET /api/reports/executive-summary/`

### Fase P1 — Detalle y drill-down API

| Método | Ruta |
|--------|------|
| GET | `/api/reports/executive-dashboard/ventas/pedidos-pendientes/` |
| GET | `/api/reports/executive-dashboard/ventas/remitos-no-facturados/` |
| GET | `/api/reports/executive-dashboard/cruzados/backorder/` |
| GET | `/api/reports/executive-dashboard/inventario/existencias/` |

### Fase P2 — CRM (condicionado)

| Método | Ruta |
|--------|------|
| GET | `/api/reports/executive-dashboard/crm/resumen/` |

Requiere spike: tablas `crm_cliente_potencial`, `crm_pre_llamada`, etc. y reglas VB6.

---

## 6. Contrato JSON (borrador orquestador)

```json
{
  "fecha_referencia": "2026-05-11",
  "periodo": { "inicio": "2026-05-01", "fin": "2026-05-11" },
  "areas": {
    "ventas": {
      "ventas_netas": 1250000.0,
      "pedidos_pendientes_monto": 320000.0,
      "remitos_no_facturados_monto": 85000.0,
      "disponible": true
    },
    "inventario": { "valor_stock": 0, "productos_bajo_minimo": 0, "disponible": true },
    "compras": { "oc_pendientes": 0, "disponible": true },
    "manufactura": { "opt_atrasadas": 0, "unidades_pendientes": 0, "disponible": true },
    "crm": { "disponible": false, "motivo": "Módulo no integrado en Synap v1" }
  },
  "meta": {
    "definicion": "executive-dashboard-v1",
    "base_empresa": "administranet93",
    "notas_semanticas": []
  }
}
```

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| SQL duplicado | Extraer a módulo único; `query_runner` importa desde ahí en refactor posterior |
| Performance MySQL | Solo agregados en P0; paginación obligatoria en detalle |
| Datos engañosos | Documentar en `meta.notas_semanticas`; reutilizar definiciones de audit |
| Romper informes | No modificar firmas públicas de `QueryRunnerService` en P0 |
| CRM incompleto | Stub explícito, no inventar KPIs |

---

## 8. Plan de entrega sugerido (solo endpoints)

| Fase | Entregable | DoD |
|------|------------|-----|
| **S0** | Spec + design OpenSpec | Contratos y tablas legacy por KPI |
| **S1** | `executive_dashboard/base.py` + tests | Pool + filtros |
| **S2** | P0 endpoints + tests contrato | 6 rutas GET responden JSON estable |
| **S3** | P1 detalle paginado | 4 rutas adicionales |
| **S4** | Refactor opcional: `query_runner` importa métricas | Sin cambio comportamiento informes |

---

## 9. Dependencias

- `docs/audits/dashboard-administranet-gap-analysis.md`
- `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` (semántica ventas día)
- `docs/general/tablas/*` (schemas)
- Validación funcional compras/CRM con negocio (**Requiere validación**)

---

## 10. Criterios de éxito

1. Un cliente HTTP puede armar un dashboard gerencial **solo con estas APIs**, sin `POST /query/`.
2. Ningún endpoint P0 ejecuta escritura legacy.
3. Tiempos de respuesta P0 aceptables con cache opcional (`REPORTS_CACHE_ENABLED`) en agregados.
4. Tests de contrato en contenedor: `docker exec Synap_app python manage.py test reports.tests.test_executive_dashboard_*`

---

## 11. Decisión abierta para spec

**¿Un solo GET orquestador vs solo endpoints por área?**

- **Recomendación:** ambos — orquestador para CEO (1 round-trip), endpoints por área para Manager View y cache granular.

---

*Propuesta lista para fase **spec** + **design** SDD. Sin implementación de código en esta entrega.*
