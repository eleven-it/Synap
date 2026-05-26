# Auditoría de Dashboard Gerencial sobre Sistema Legacy

**Proyecto:** Synap (Django + MySQL AdministraNET legacy)  
**Fecha de auditoría:** 11/05/2026  
**Alcance:** Código y documentación en el repositorio `Synap` — sin cambios de implementación.  
**Objetivo de diseño auditado:** Cabina ejecutiva multiárea (CRM, Ventas, Compras, Inventario, Manufactura) con tres niveles (CEO / Manager / Action).

---

## 1. Resumen ejecutivo

### Estado general

**No existe** en este repositorio un **Dashboard Gerencial Ejecutivo unificado** que responda a las siete preguntas de negocio ni a los tres niveles funcionales (CEO View, Manager View, Action View). Lo que sí existe es un **ecosistema fragmentado**:

1. **Panel ejecutivo de ventas facturadas** (`resumen-ejecutivo-ventas`) — vista parcial, orientada al **día contable**, solo área Ventas (facturación + margen por rubro/subrubro reciente).
2. **Catálogo de reportes** (`reports/`) — decenas de informes **operativos o gerenciales por slug**, cada uno en pantalla propia (`/reports/dashboard/<slug>/`), sin integración en una sola cabina.
3. **Tablero MPR** (`mpr/tablero/`) — manufactura sobre modelos Synap + MySQL legacy, **no** integrado al panel ejecutivo.
4. **Plantillas declarativas seed** (`reports/migrations/0002_seed_initial_reports.py`) — muchos slugs con **métricas en `config` JSON pero sin motor de datos** (caen en `get_sample_data` / «not implemented yet»).
5. **Módulo CRM** — **no implementado** en Synap (menú comentado; tablas legacy documentadas en `docs/general/tablas/`).
6. **Módulo Compras** — captura OCR/factura (`compras/`), **no** dashboard gerencial de compras.

La integración con legacy **está resuelta a nivel de conexión MySQL por `base_empresa`** (`reports/services/connection_pool.py`, `query_runner.py`, `executive_sales_summary.py`), no mediante un conector Odoo ni JSON-2 (no aplicable a este repo).

### Nivel de avance estimado

| Dimensión | Avance estimado | Comentario |
|-----------|-----------------|------------|
| CEO View unificada | **~5 %** | Solo `executive_summary` parcial (ventas del día). |
| Manager View por área | **~12 %** | Informes sueltos por slug + tablero MPR. |
| Action View accionable | **~8 %** | Tablas en informes legacy; sin modelo unificado de alerta/acción. |
| KPIs globales esperados | **~10 %** | Fragmentos (ventas netas, pedidos pendientes, stock BO, MPR atrasadas). |
| KPIs cruzados | **~5 %** | `bo-stock-facturacion`, `total-consolidado-operativo` parcial. |
| Scores operativos | **0 %** | No encontrado. |
| Capa agentic/predictiva | **0 %** | No encontrado. |

**Avance global ponderado hacia el diseño objetivo: ~8–12 %.**

### Principales fortalezas

- **Conexión legacy madura** para ventas facturadas: reglas documentadas en `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` y código en `executive_sales_summary.py` (FA/NC, `cuentacliente`, `stock`).
- **Catálogo de reportes extensible** (`ReportDefinition`, API `reports-query`, export Excel).
- **Informes operativos profundos** ya implementados: ventas netas, pedidos pendientes, remitos no facturados, backorder vs stock (`bo-stock-facturacion`), existencias, objetivos vs BO.
- **MPR** con tablero operativo de producción (OPT atrasadas, pedidos pendientes, unidades).
- **UI canónica** documentada (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`) para nuevas pantallas gerenciales.
- **Tests de contrato** del resumen ejecutivo (`reports/tests/test_executive_summary_contract.py`).

### Principales debilidades

- **No hay una sola pantalla** que integre CRM → Ventas → Stock → Compras → MRP → Entrega.
- **CRM y Compras gerenciales ausentes** en código Synap.
- **Muchos slugs del seed** son placeholders declarativos sin datos reales.
- **KPIs dispersos** en `query_runner.py` (~4.400+ líneas), `executive_sales_summary.py`, `mpr/views.py` — sin capa `metrics/` ni contratos KPI.
- **Frontend ejecutivo** = plantilla Django + JS monolítico (`executive_summary.js` ~900 líneas), no SPA modular.
- **Sin scores, semáforos globales, funnel comercial ni cadena operativa visual** en el panel ejecutivo.
- **Riesgo semántico alto** al mezclar facturación, pedidos, remitos y backorder en distintos informes sin narrativa única.

### Riesgos críticos

1. **Decisión gerencial sobre “ventas”** usando solo `resumen-ejecutivo-ventas` ignora pipeline, pedidos pendientes de entrega y backlog — subestima riesgo de entrega.
2. **Margen del panel ejecutivo** (`PrecioNetoxR` en líneas) **≠** KPI «Ventas del día» (`SubtotalDesc` en comprobante) — ya documentado en `meta.nota_venta_neta_lineas_vs_comprobante`; puede confundir a dirección.
3. **Informes declarativos seed** (`compras_cumplimiento`, `logistica_otif`, `inventario_rotacion_cobertura`) pueden aparecer en catálogo y **mostrar datos de muestra** si se ejecutan (`query_runner.py` líneas 333–338).
4. **Consultas pesadas** a MySQL transaccional sin capa de agregados/materializados dedicada al dashboard.
5. **MPR ≠ Manufactura completa legacy**: OPT/OPP/Armado Synap, no paridad total con todos los estados MRP del diseño objetivo.

### Próxima acción recomendada

1. **Congelar definiciones semánticas** (venta confirmada vs facturada vs cotizada; stock físico vs reservado vs pendiente) en un diccionario legacy compartido.
2. **Definir MVP de CEO View** como **orquestador de APIs** que agregue 8–12 KPIs ya calculables desde servicios existentes, sin reimplementar SQL.
3. **Excluir del catálogo gerencial** slugs sin implementación real hasta tener `query_runner` o motor declarativo conectado.
4. **Planificar Fase 0** corrigiendo riesgos de datos engañosos antes de ampliar visualizaciones.

---

## 2. Mapa de arquitectura actual encontrada

### Framework detectado

| Capa | Tecnología | Evidencia |
|------|------------|-----------|
| Backend | **Django** (Python) | `django_project/`, `manage.py` |
| BD operativa Synap | **PostgreSQL** | `settings.DATABASES['default']`, modelos `reports`, `mpr`, `core` |
| BD legacy empresa | **MySQL AdministraNET** | `settings.DATABASES['mysql']`, `base_empresa` en sesión |
| UI informes / ejecutivo | **Django templates** + **Tailwind** + **Alpine** (parcial) + **d3 v7** | `reports/templates/`, `executive_summary.html` |
| UI soporte (otro producto) | **React 18 + MUI + TanStack Query** | `support/frontend/` — **no** es el dashboard gerencial operativo |
| API REST | **Django REST Framework** | `reports/api_views.py`, `reports/api_urls.py` |

### Carpetas relevantes

| Ruta | Rol |
|------|-----|
| `reports/` | Catálogo, dashboards por slug, `query_runner`, API informes, resumen ejecutivo |
| `reports/services/executive_sales_summary.py` | Agregados panel ejecutivo ventas |
| `reports/executive_summary_api_views.py` | `GET /api/reports/executive-summary/` |
| `reports/static/reports/js/executive_summary.js` | UI panel ejecutivo |
| `reports/static/reports/js/dashboard.js` | UI informes legacy/declarativos (~10k líneas) |
| `mpr/` | Manufactura Synap (OPT, OPP, tablero) |
| `compras/` | Hub factura compra (operativo, no KPI gerencial) |
| `ventas/` | Presupuestos ventas (PRE), no dashboard |
| `core/services/` | Pool MySQL, stock, permisos legacy |
| `docs/reports/` | Specs funcionales informes |
| `docs/general/tablas/` | Schemas legacy documentados |
| `openspec/specs/reports-ejecutivo-ventas/` | Spec panel ventas |

### Componentes principales de “dashboard”

| Componente | Tipo | Ruta |
|------------|------|------|
| Resumen ejecutivo ventas | Vista dedicada CEO-parcial | `reports/templates/reports/executive_summary.html` |
| Dashboard genérico por informe | `dashboard_detail.html` + `dashboard.js` | `reports/views.py` → `DashboardDetailView` |
| Tablero MPR | Vista manufactura | `mpr/templates/mpr/tablero.html` |
| Dashboard soporte | Casos/SLA (otro dominio) | `support/frontend/.../DashboardPage.tsx` |

### Servicios de datos

| Servicio | Función |
|----------|---------|
| `reports/services/query_runner.py` | Dispatcher SQL legacy por `ReportDefinition.slug` |
| `reports/services/executive_sales_summary.py` | Payload único resumen ejecutivo |
| `reports/services/ventas_netas.py` | Lógica ventas netas reutilizada |
| `reports/services/ventas_objetivos_bo_runner.py` | Objetivos vs backorder |
| `reports/services/catalog_service.py` | Catálogo + labels métricas |
| `reports/services/connection_pool.py` | Pool MySQL por empresa |
| `mpr/services.py` | Lógica OPT/OPP/demanda |
| `core/services/administranet_stock.py` | Stock/artículos |

### Hooks / stores

- **No encontrado** capa React de dashboard gerencial en Synap principal.
- `support/frontend` usa `useQuery` — dominio soporte, no operaciones.

### Tipos / interfaces

- Contratos JSON **implícitos** en respuestas Python (`run_executive_summary` dict).
- `ReportDefinition.config` JSON schema declarativo (`metrics`, `dimensions`) — muchos sin implementación.
- **No encontrado** paquete TypeScript de KPIs ni OpenAPI dedicado al dashboard ejecutivo.

### Rutas / páginas

| Ruta HTTP | Vista |
|-----------|-------|
| `/reports/dashboard/resumen-ejecutivo-ventas/` | Panel ejecutivo ventas |
| `/reports/dashboard/<slug>/` | Informe individual |
| `/api/reports/executive-summary/` | API JSON resumen ejecutivo |
| `/api/reports/query/` | API ejecución informes |
| `/mpr/` | Tablero MPR |

### Fuentes de datos, endpoints, queries

- **MySQL tablas legacy** (principal): `cuentacliente`, `stock`, `stockp`, `comp_ped`, `articulo`, `rubro`, `subrubro`, `cuentaproveedor`, `proveedor`, `cliente`, `sucursales`, `punto_venta`, etc.
- **PostgreSQL Synap**: `reports_puntoventacanalejecutivo`, modelos MPR, `ReportDefinition`.
- **Procedimientos almacenados**: **No encontrado** uso directo en panel ejecutivo (Inferido: lógica en SQL embebido Python/VB6 parity).
- **Vistas MySQL**: **No encontrado** capa de vistas materializadas para dashboard en código auditado.

### Observaciones

- Arquitectura **orientada a informes individuales**, no a **command center**.
- El panel más cercano al CEO View es **solo ventas facturadas intradía**.

---

## 3. Mapa de fuentes legacy detectadas

| Fuente | Tipo | Área | Campos / uso relevante | Relación | Riesgo semántico | Observaciones |
|--------|------|------|------------------------|----------|------------------|---------------|
| `cuentacliente` | tabla | Ventas / Finanzas | `Fecha`, `FechaControl`, `TipoComprobante`, `SubtotalDesc`, `Anulado`, `CodigoMovimiento`, `CodSucursal`, `id_pv` | → `stock` por `CodigoMovimiento` | FA vs NC; facturación ≠ pedido | Base KPI ventas netas |
| `stock` | tabla | Ventas / Stock | `PrecioNetoxR`, `PrecioCostoxR`, `Cantidad`, `TipoComp`, `IDArt`, `Anulado` | → `cuentacliente`, `articulo` | Línea vs cabecera | Top 10, unidades, margen |
| `comp_ped` | tabla | Ventas / Logística | `TipoComprobante`, `Estado`, `Fecha`, `Codigo` (cliente) | → `stockp` | PED vs REM vs PRE | Pedidos pendientes, BO |
| `stockp` | tabla | Ventas / BO | `cantidad_pendiente`, `PrecioNetoxR`, `CodigoMovimiento` | → `comp_ped` | Backorder operativo | `bo-stock-facturacion` |
| `articulo` | tabla | Inventario / Ventas | `CodigoRubro`, `IDSubRubro`, `PrecioCosto`, nombres | → `rubro`, `subrubro` | Costo maestro vs costo línea | Margen por categoría |
| `rubro` / `subrubro` | tabla | Inventario | `CodigoRubro`, `NombreRubro`, `IDSubRubro` | Relación inferida | Sin FK en catálogo | Agrupación margen |
| `cuentaproveedor` | tabla | Compras | OC, estados, proveedor | → `stock` compras | OC vs recepción | Parcial en BO/stock report |
| `proveedor` | tabla | Compras | `Nombre`, `Codigo` | Relación inferida | — | Joins en cash flow / BO |
| `stock_deposito` / movimientos | tabla | Inventario | Saldos, depósitos | Relación inferida | Saldo vs disponible | `stock-existencias`, `administranet_stock` |
| `crm_*` (varias) | tabla | CRM | Documentadas en `docs/general/tablas/` | Relación inferida | — | **Sin uso en Synap UI** |
| Modelos MPR Synap + MySQL | servicio | Manufactura | OPT, OPP, listas producción | Propia app `mpr` | ≠ `mrp.production` Odoo-like | Tablero MPR |
| `ReportDefinition` | modelo PG | Metadatos | `slug`, `config` JSON | — | Slugs sin datos | Placeholders |

---

## 4. Matriz de KPIs encontrados

*(Solo KPIs con evidencia en código; equivalente esperado según diseño auditado.)*

| KPI encontrado | KPI esperado equivalente | Área | Archivo | Fuente legacy | Campos / fórmula (resumen) | Estado | Observaciones | Riesgo | Recomendación |
|----------------|---------------------------|------|---------|---------------|---------------------------|--------|---------------|--------|---------------|
| Ventas del día (`ventas_netas_dia`) | Ventas confirmadas (parcial: solo facturado día) | Ventas | `executive_sales_summary.py` | `cuentacliente` | SUM CASE FA − NC en `SubtotalDesc` por `Fecha` | **Parcial** | Solo día, no mes | No incluye pedidos sin facturar | Aclarar etiqueta «Ventas netas facturadas (día)» |
| Vs ayer % / gap $ | Variación vs período anterior | Ventas | idem | idem | Comparación día vs día−1 | **Completo** (día) | Sin 30/90d en panel | — | Extender series |
| Tickets / ticket promedio | Ticket promedio | Ventas | idem | `cuentacliente` | COUNT FA–FM; ventas/tickets | **Completo** (día) | NC no cuentan ticket | — | OK con spec |
| Unidades vendidas | — (operativo) | Ventas | idem | `stock`+`cc` | SUM cantidad con signo | **Completo** (día) | — | — | — |
| Mayorista vs Salón | Ventas por canal | Ventas | idem + modal PV | `cuentacliente` + PG `PuntoVentaCanalEjecutivo` | Split por `id_pv` | **Parcial** | Config manual PV | PV sin asignar | Integrar en CEO view |
| Top 10 productos | Ventas por producto | Ventas | idem | `stock` | SUM `PrecioNetoxR` por `IDArt` | **Parcial** | Solo top 10 día | — | Drill-down en informe |
| Margen bruto día | Margen estimado | Ventas | idem | `stock` | SUM neto − costo líneas | **Parcial** | Costo renglón | ≠ ventas comprobante | Mantener nota meta |
| Margen por rubro/subrubro | Ventas por categoría + margen | Ventas | idem | `articulo`→`rubro`/`subrubro` | GROUP BY | **Parcial** | Sin semáforo | — | Tablas en panel |
| Serie horaria / 7 días | Tendencias 7d (parcial) | Ventas | idem | `cuentacliente` | Por hora / por día | **Parcial** | No 30/90 en ejecutivo | — | Ampliar ventanas |
| Ventas netas (informe) | Ventas confirmadas mes | Ventas | `query_runner._run_ventas_netas` | `cuentacliente` | Período configurable | **Completo** (informe) | Informe separado | Duplicado conceptual | Unificar definición |
| Pedidos pendientes (informe) | Pedidos pendientes entrega / backlog | Ventas | `_run_pending_orders` | `comp_ped` | PED estados preparación | **Parcial** | No en panel CEO | Estados VB6 | Exponer KPI global |
| Remitos no facturados | Pedidos pendientes facturar | Ventas | `_run_uninvoiced_remitos` | `comp_ped` REM | — | **Parcial** | Informe aparte | — | KPI cruzado |
| Sales summary | Resumen ventas período | Ventas | `_run_sales_summary` | Varias | Netas + remitos + pedidos | **Parcial** | Consolidado | — | Fuente CEO view |
| Total consolidado operativo | KPIs globales fragmentados | Cruzado | `_run_total_consolidado_operativo` | Varias | Totales operativos | **Parcial** | No es dashboard | — | Orquestar |
| BO vs stock vs facturación | Demand coverage, sales at risk, backlog | Cruzado | `_run_backorder_vs_stock_vs_facturacion` | `comp_ped`, `stockp`, `cc` | BO detalle | **Parcial** | Límite 1000 filas | Performance | Agregar server-side |
| Stock existencias | Valor inventario, quiebres (parcial) | Inventario | `_run_stock_existencias` | `articulo`, stock depósito | — | **Parcial** | Informe | Semántica saldos | Validar vs mínimos |
| KPI pedidos pendientes MPR | Producción planificada (parcial) | Manufactura | `mpr/views.py` TableroView | MPR + MySQL | COUNT pedidos | **Parcial** | Solo MPR app | — | Integrar CEO |
| OPT atrasadas | Producción atrasada | Manufactura | idem | MPR services | COUNT OPT | **Parcial** | — | — | KPI global |
| Unidades pendientes MPR | — | Manufactura | idem | MPR | SUM unidades | **Parcial** | — | — | — |
| `logistica_otif` (seed) | OTIF / cumplimiento entregas | Logística | `0002_seed_initial_reports.py` | **Desconocido** | config JSON only | **Mockeado / ausente** | Sin runner | **Alto** | Ocultar o implementar |
| `compras_cumplimiento` (seed) | Compras confirmadas, lead time | Compras | seed | **Desconocido** | — | **Ausente** | Placeholder | **Alto** | No mostrar como real |
| `inventario_rotacion_cobertura` (seed) | Rotación, días inventario | Inventario | seed | — | — | **Ausente** | Placeholder | Medio | Implementar o quitar |
| `clientes_churn_ltv` (seed) | — (CRM/retención) | CRM/Ventas | seed + widgets | — | — | **Ausente** | Declarativo | Medio | — |

---

## 5. Matriz de KPIs faltantes (muestra priorizada Alta)

| KPI faltante | Área | Prioridad | Objetivo gerencial | Datos necesarios | Fuente legacy probable | Dependencias |
|--------------|------|-----------|-------------------|------------------|------------------------|--------------|
| Pipeline total / ponderado | CRM | **Alta** | Forecast ingresos | Oportunidades, probabilidad, importe | `crm_*` tablas VB6 | **CRM no en Synap** |
| Forecast ingresos | CRM/Ventas | **Alta** | ¿Cuánto vamos a vender? | Pipeline + histórico | CRM + `comp_ped` PRE | CRM + ventas |
| Operational Health Score | Global | **Alta** | Lectura 10 segundos | Todos los scores | Orquestación | Fases 1–4 |
| Pedidos pendientes entrega (global KPI) | Ventas | **Alta** | ¿Podemos entregar? | PED/REM estados, fechas | `comp_ped`, `stockp` | Ya hay informe |
| Pedidos atrasados / backlog vencido | Ventas | **Alta** | Riesgo entrega | Fechas compromiso | `comp_ped` | Validar campos fecha |
| Stock crítico / quiebres (global) | Inventario | **Alta** | Riesgo stock | Mín/máx, saldo, demanda | `articulo`, `stock_deposito`, BO | Informe existencias |
| Compras pendientes críticas | Compras | **Alta** | Riesgo abastecimiento | OC pendientes, fechas | `cuentaproveedor`, `stock` | Sin módulo compras KPI |
| OTIF / cumplimiento entregas | Logística | **Alta** | Promesa cliente | Entregas vs prometido | REM, rutas | Seed sin datos |
| Sales at Risk | Cruzado | **Alta** | Ventas en riesgo | BO + stock + prod | Ya parcial en BO | Unificar regla |
| Production at Risk | Cruzado | **Alta** | MO bloqueadas | Componentes, MPR | MPR + stock | Disponibilidad componentes |
| Cash-to-Stock Risk | Cruzado | **Media** | Capital inmovilizado | Valor stock + ventas | Inventario + ventas | — |
| CRM Score / Sales Score / … | Scores | **Media** | Semáforo por área | KPIs normalizados | — | Motor scoring |
| Funnel comercial | CRM/Ventas | **Media** | Conversión etapas | CRM + PRE + PED | CRM, `comp_ped` | CRM ausente |
| Cadena operativa visual | UX | **Media** | Flujo punta a punta | Estados agregados | Todas las áreas | Diseño UI |
| Action tables unificadas | Action View | **Alta** | Intervención gerencial | Alertas derivadas | — | Motor alertas |

*(Los ~80+ KPIs restantes del diseño objetivo están **ausentes** o solo cubiertos de forma indirecta por informes no integrados.)*

---

## 6. GAPs funcionales por área

### 6.1 CRM / Pre-venta

| | |
|-|-|
| **Implementado** | **No encontrado** módulo Synap ni endpoints. Referencias en `core/utils/utils.py` (menú comentado), tablas `crm_*` en `docs/general/tablas/`, exclusión explícita CRM en presupuesto (`docs/general/SPEC_PRESUPUESTO_VENTAS_SYNAP.md`). |
| **Parcial** | Seed `clientes_churn_ltv` en catálogo (declarativo, sin datos reales). |
| **Faltante** | Pipeline, conversiones, ciclo comercial, actividades, forecast por vendedor, oportunidades vencidas, motivos pérdida, etc. |
| **Riesgos** | Dirección sin visibilidad pre-venta; forecast solo desde ventas facturadas o pedidos. |
| **Recomendaciones** | Decidir: integrar CRM legacy MySQL o posponer área; no simular con churn seed. |

### 6.2 Ventas

| | |
|-|-|
| **Implementado** | Panel `resumen-ejecutivo-ventas`; informes `ventas_netas`, `pedidos-pendientes`, `remitos-no-facturados`, `ventas-por-vendedor`, `ventas-objetivos-vs-bo`, presupuestos PRE en desarrollo. |
| **Parcial** | Ventas “confirmadas mes” solo vía informes con filtros; conversión cotización→pedido no como KPI único global; backlog en `bo-stock-facturacion` pero no en CEO view. |
| **Faltante** | Cotizaciones abiertas agregadas, backlog normal/riesgo/vencido/bloqueado como KPIs globales, ventas canceladas, entrega parcial como KPI ejecutivo. |
| **Riesgos** | Panel diario facturado vs backlog mensual genera decisiones inconsistentes. |
| **Recomendaciones** | Orquestar API CEO con subconjunto de `sales_summary` + `pedidos-pendientes` + ejecutivo. |

### 6.3 Compras

| | |
|-|-|
| **Implementado** | `compras/` captura factura; joins `cuentaproveedor`/`proveedor` en cash flow y BO; seed `compras_cumplimiento` (sin datos). |
| **Parcial** | OC pendientes dentro de informes stock/BO (tooltip OC en `query_runner` ~3800). |
| **Faltante** | Todos los KPIs gerenciales de compras del diseño (lead time, cumplimiento proveedor, urgentes, críticas para ventas/producción, etc.). |
| **Riesgos** | Seed `compras_cumplimiento` puede inducir falsa sensación de cobertura. |
| **Recomendaciones** | Nuevo servicio `purchase_metrics` sobre `cuentaproveedor`; quitar o marcar slugs seed. |

### 6.4 Inventario / Stock

| | |
|-|-|
| **Implementado** | `stock-existencias`, lógica stock en BO, `core/services/administranet_stock.py`, rotación en seed (sin datos). |
| **Parcial** | Valorización y saldos en informes; no distingue claramente disponible vs reservado vs proyectado en panel ejecutivo. |
| **Faltante** | Stock Health Score, transferencias pendientes globales, sobrestock, días inventario en dashboard, exactitud inventario. |
| **Riesgos** | Confundir saldo depósito con stock libre para venta. |
| **Recomendaciones** | Normalizar semántica en diccionario; exponer 3–4 KPIs stock en CEO view desde existencias + BO. |

### 6.5 Manufactura / Producción

| | |
|-|-|
| **Implementado** | App `mpr/` completa (OPT, OPP, tablero, informes `mpr-*` en reports). |
| **Parcial** | Atrasos y pendientes; informes MPR en catálogo reportes. |
| **Faltante** | Integración en command center; scrap, eficiencia centro, cuello de botella, MO bloqueadas por material (regla explícita), cumplimiento plan % global. |
| **Riesgos** | Gerencia no ve MPR si no entra a `/mpr/`; duplicidad mental con informes `mpr-opt-atrasadas`. |
| **Recomendaciones** | API agregada MPR → KPIs globales «producción atrasada», «unidades pendientes». |

---

## 7. GAPs de KPIs cruzados

| KPI cruzado | Existe | Archivos | Datos disponibles | Faltantes | Complejidad | Prioridad | Riesgo semántico |
|-------------|--------|----------|-------------------|-----------|-------------|-----------|------------------|
| Demand Coverage | **Parcial** | `bo-stock-facturacion`, BO runner | BO, reservado, stock | Regla única documentada | Alta | Alta | Reservado vs pendiente |
| Sales at Risk | **Parcial** | idem | BO + cliente + importe | Umbral riesgo formal | Media | Alta | Definición riesgo |
| Production at Risk | **Parcial** | `mpr/views`, `mpr-brecha-demanda` | OPT atrasadas, demanda | Componentes BOM | Alta | Alta | Disponibilidad real |
| Purchase Impact | **Parcial** | BO (OC pendiente) | OC por artículo | Impacto $ ventas perdidas | Alta | Media | OC ≠ necesidad |
| Stock-to-Sales Alignment | **Parcial** | `total-consolidado-operativo`, BO | Ventas + stock | Ratio global KPI | Media | Media | Períodos distintos |
| Commercial-to-Delivery Gap | **Parcial** | ventas netas + pedidos + remitos | Facturado vs PED vs REM | Gap unificado | Media | Alta | Facturación ≠ entrega |
| Aging de pedidos | **Parcial** | `pedidos-pendientes`, BO | Fechas en `comp_ped` | Buckets estándar | Media | Alta | Requiere validación campos |
| Margin Risk | **Parcial** | `executive_sales_summary` margen | Costo línea | Margen vs presupuesto | Media | Media | Costo histórico línea |
| Supply Risk | **No** | — | Parcial vía compras en BO | Motor riesgo | Alta | Alta | — |
| Inventory Risk | **Parcial** | stock-existencias, BO | Mínimos, quiebres | Score | Media | Alta | — |
| Delivery Risk | **No** | — | REM, logística rutas | OTIF | Alta | Alta | — |
| Cash-to-Stock Risk | **No** | — | Valor stock (informe) | Ventas + carrying cost | Alta | Media | — |

---

## 8. GAPs de UX/UI

| Problema | Evidencia | Recomendación |
|----------|-----------|--------------|
| **No es CEO View unificada** | Una pantalla ventas + catálogo de informes | Landing «Command Center» con 12 KPIs + semáforos |
| **Jerarquía solo en ventas** | `executive_summary.html` bien diseñado; resto disperso | Misma jerarquía visual en vista global |
| **Sin lectura <10 s del negocio completo** | Requiere navegar múltiples slugs | Score + top 3 riesgos en hero |
| **Sin funnel ni cadena operativa** | No encontrado | Componente flujo CRM→Entrega (aunque CRM falte, placeholder) |
| **Semáforos ausentes globalmente** | Badges % en ventas; no por área | Semáforo por CRM/Ventas/Compras/Stock/MRP |
| **Tendencias 30/90 ausentes en ejecutivo** | Solo 7 días en ventas | Selectores período unificados |
| **Drill-down por área débil** | Drill = otro informe en catálogo | Tabs Manager View |
| **Action View ausente** | Tablas operativas sin «acción sugerida» | Columnas responsable, impacto, acción |
| **Estados loading/error** | Presentes en `executive_summary.js` | Estandarizar en orquestador |
| **Nombres gerenciales** | Mezcla técnica («PrecioNetoxR», «SubtotalDesc») | Glosario en UI |
| **Inconsistencia stack UI** | Django+Tailwind vs React soporte | No mezclar; mantener canon reportes |

---

## 9. GAPs de arquitectura frontend

| Problema | Archivos | Riesgo | Recomendación (sin implementar) |
|----------|----------|--------|--------------------------------|
| Lógica negocio en JS monolito | `executive_summary.js`, `dashboard.js` | Mantenimiento | Extraer `metrics/` + fetchers |
| Sin capa adaptación legacy | — | Acoplamiento SQL↔UI | `legacy-adapters/` por dominio |
| Sin contratos KPI versionados | Respuestas dict ad hoc | Breaking changes | `types/kpi-contract-v1` |
| Cálculos en render (d3) | `dashboard.js` | Performance | Pre-agregar en API |
| Duplicación ventas netas | `executive_sales_summary` vs `ventas_netas` | Inconsistencia | Servicio compartido |
| Sin tests UI | — | Regresiones | Playwright smoke CEO view |
| Informes declarativos vs legacy bifurcados | `query_runner.run` | Confusión | Flag `data_source_status` en catálogo |

---

## 10. GAPs de integración con sistema legacy

| Tema | Hallazgo |
|------|----------|
| **Fuentes bien usadas** | `cuentacliente`, `stock`, `comp_ped`, `stockp` alineados a docs VB6 en informes maduros. |
| **Fuentes dudosas** | Slugs seed (`ventas_resumen`, `compras_cumplimiento`) — **Requiere validación** si tienen vista MySQL real. |
| **Campos correctos (ventas)** | `SubtotalDesc`, `TipoComprobante`, `Anulado` — evidencia en `executive_sales_summary.py`. |
| **Campos dudosos** | Fechas compromiso entrega en PED — **Requiere validación funcional** por cliente. |
| **Queries problemáticas** | `bo-stock-facturacion` detalle hasta 1000 filas; múltiples scans por informe. |
| **Volumen** | Sin agregados nocturnos para dashboard; riesgo en horario pico. |
| **Multiempresa** | `base_empresa` en sesión; filtros sucursal en ejecutivo — OK parcial. |
| **Estados mal interpretados** | PED «En preparación» vs «Pendiente» en `pedidos-pendientes` — documentado pero crítico. |
| **Lógica oculta** | Paridad VB6 en comentarios `query_runner`; riesgo drift si VB6 cambia. |

---

## 11. GAPs de semántica de datos

| Confusión | Dónde puede ocurrir | Impacto gerencial |
|-----------|---------------------|-------------------|
| Ventas facturadas vs confirmadas (pedido) | Panel ejecutivo vs `pedidos-pendientes` | Sobreestimar capacidad de cierre |
| Ventas comprobante vs venta líneas (margen) | `meta.nota_venta_neta_lineas_vs_comprobante` | Margen % incoherente con ventas KPI |
| Stock físico vs reservado vs BO | `bo-stock-facturacion` vs `stock-existencias` | Prometer stock inexistente |
| Remito vs factura | `remitos-no-facturados` | Ingreso percibido sin facturar |
| OC confirmada vs recibida | Compras en BO tooltip | Compras “hechas” sin mercadería |
| Producción planificada vs ejecutable | MPR tablero vs disponibilidad componentes | Plan irreal |
| Pipeline vs forecast | CRM ausente | — |
| Anulado vs activo | Filtros `Anulado='No'` | Si falla filtro, KPI inflado |
| Costo línea vs `articulo.PrecioCosto` | Margen ejecutivo usa línea | Correcto operativamente; distinto a estándar |

---

## 12. Riesgos técnicos priorizados

| Riesgo | Severidad | Impacto | Evidencia | Recomendación |
|--------|-----------|---------|-----------|---------------|
| Slugs catálogo con datos sample | **Alta** | Decisiones sobre datos falsos | `query_runner.py` else → `get_sample_data` | Desactivar o etiquetar «demo» |
| Panel ejecutivo interpretado como “todo ventas” | **Alta** | Visión incompleta operación | Solo `resumen-ejecutivo-ventas` | Comunicación + CEO view real |
| Margen vs ventas día inconsistentes | **Media** | Confianza KPI | `executive_sales_summary` meta | UI dual label |
| query_runner monolito | **Media** | Deuda, bugs | ~4400 líneas | Extraer dominios |
| Carga MySQL producción | **Media** | Performance legacy | Múltiples informes pesados | Cache/reporting DB |
| MPR desconectado de reportes CEO | **Media** | Silo manufactura | Rutas separadas | API agregación |
| Sin tests KPI cruzados | **Media** | Regresiones silenciosas | Pocos tests integración BO | Fixtures SQL |

---

## 13. Riesgos legacy priorizados

| Riesgo legacy | Severidad | Área | Evidencia | Impacto gerencial | Recomendación |
|---------------|-----------|------|-----------|-------------------|---------------|
| FK no declaradas en catálogo | **Media** | Todas | `docs/general/tablas/*.md` | Joins incorrectos | Diccionario relaciones |
| Estados mágicos strings | **Alta** | Ventas/Compras | `TipoComprobante`, `Estado` | Filtros erróneos | Tabla estados canónicos |
| `comp_ped` vs `cuentacliente` doble vía | **Alta** | Ventas | Informes distintos | Doble conteo | Mapa documento→KPI |
| Anulaciones / NC | **Alta** | Ventas | Signo en SQL | Ventas infladas | Tests regresión |
| Multiempresa `base_empresa` | **Media** | Global | Sesión | Mezcla datos | Validar en API |
| CRM solo VB6 | **Alta** | CRM | Sin app Synap | Hueco pre-venta | Proyecto aparte |
| Registros huérfanos stock/cc | **Media** | Stock | **Inferido** | KPIs rotos | Queries calidad datos |
| Histórico reglas distintas | **Media** | Todas | **Requiere validación** | Comparar 30/90d | Congelar reglas por período |

---

## 14. Backlog recomendado para cubrir faltantes

### Fase 0 — Correcciones críticas

| | |
|-|-|
| **Objetivo** | Evitar datos engañosos. |
| **Tareas** | Marcar slugs sin runner; revisar labels ventas/margen; documentar diccionario estados PED/REM/FA; validar `Anulado` en todos los runners críticos. |
| **Archivos** | `catalog_service.py`, `query_runner.py`, `executive_summary.js`, catálogo UI |
| **DoD** | Ningún informe gerencial muestra sample sin aviso; glosario publicado. |

### Fase 1 — KPIs ejecutivos mínimos

| | |
|-|-|
| **Objetivo** | CEO View v0 con ~12 KPIs reales. |
| **Tareas** | API `executive-command-center/` agregando: ventas mes (ventas_netas), pedidos pendientes, remitos NF, stock crítico (de existencias), MPR atrasadas, margen día, backlog $ (BO total), variación vs mes anterior. |
| **Archivos** | Nuevo módulo `reports/services/executive_command_center.py`, plantilla única |
| **DoD** | Una URL; carga <5s con cache; permiso `reports.view_managerial`. |

### Fase 2 — Drill-down por área

| | |
|-|-|
| **Objetivo** | Manager View por tabs. |
| **Tareas** | Enlazar cada tab a informes existentes + mini-KPIs; Compras nuevo runner OC. |
| **DoD** | 5 tabs navegables sin perder contexto filtros. |

### Fase 3 — KPIs cruzados

| | |
|-|-|
| **Objetivo** | Sales at Risk, Demand Coverage, Commercial-to-Delivery Gap unificados. |
| **Tareas** | Servicio basado en reglas sobre BO + ventas + MPR. |
| **DoD** | 6 KPIs cruzados con definición escrita y tests. |

### Fase 4 — Scoring operativo

| | |
|-|-|
| **Objetivo** | Operational Health Score + scores por área. |
| **Tareas** | Motor scoring ponderado; semáforos UI. |
| **DoD** | Score 0–100 con explicación desplegable. |

### Fase 5 — Alertas predictivas / agentic

| | |
|-|-|
| **Objetivo** | Preparar arquitectura sin ML obligatorio. |
| **Tareas** | Motor reglas + cola alertas + Action View tabular. |
| **DoD** | Top 10 alertas con responsable y acción sugerida. |

---

## 15. Recomendación de arquitectura objetivo

Adaptación al stack **Django + JS** actual (no imponer React si producto quiere canon reportes):

```
reports/
  executive_dashboard/
    api/
      command_center_views.py      # GET agregado CEO
      area_views.py                # drill-down por área
    legacy_adapters/
      sales.py                     # cuentacliente, stock
      orders.py                    # comp_ped, stockp
      inventory.py                 # stock_deposito, articulo
      purchases.py                 # cuentaproveedor
      manufacturing.py             # delega mpr.services
    metrics/
      calculators/                 # una función por KPI
      contracts.py                 # shapes JSON versionados
      scoring.py                   # scores y health
      alerts.py                    # reglas riesgo
    normalizers/
      states.py                    # map legacy → canónico
    dictionary/
      LEGACY_FIELDS.md             # diccionario datos
    templates/
      command_center.html
    static/reports/js/
      command_center.js
    tests/
      test_metrics_*.py
```

**Principios:** fetching en adapters → cálculo en `metrics/` → render en JS; **nunca** SQL nuevo en plantillas.

---

## 16. Lista final de acciones recomendadas

| # | Acción | Motivo | Impacto | Esfuerzo | Prioridad |
|---|--------|--------|---------|----------|-----------|
| 1 | Inventariar slugs `ReportDefinition` con/sin runner real | Evitar datos sample | Alto | Bajo | **P0** |
| 2 | Publicar diccionario semántico legacy (venta/stock/pedido) | Alinear gerencia y dev | Alto | Medio | **P0** |
| 3 | Diseñar API `executive-command-center` reutilizando servicios | CEO View v0 | Muy alto | Alto | **P1** |
| 4 | Renombrar KPIs panel ventas («facturadas del día») | Reducir confusión | Medio | Bajo | **P1** |
| 5 | Integrar KPIs MPR + pedidos + BO en vista única | Operación completa | Muy alto | Alto | **P1** |
| 6 | Implementar métricas compras desde `cuentaproveedor` | Cerrar hueco abastecimiento | Alto | Alto | **P2** |
| 7 | Decidir estrategia CRM (integrar vs diferir) | Forecast confiable | Estratégico | Muy alto | **P2** |
| 8 | Extraer calculadores de `query_runner` por dominio | Mantenibilidad | Medio | Muy alto | **P2** |
| 9 | Capa cache/reporting read replica MySQL | Performance | Alto | Alto | **P2** |
| 10 | Motor alertas + Action View | Intervención gerencial | Alto | Alto | **P3** |
| 11 | Operational Health Score | Lectura 10s | Alto | Medio | **P3** |
| 12 | Tests integración KPIs cruzados | Calidad | Medio | Medio | **P3** |

---

## Anexo A — Respuesta a las 7 preguntas de negocio (estado actual)

| Pregunta | ¿Respondida hoy? | Evidencia |
|----------|------------------|-----------|
| 1. ¿Cuánto vamos a vender? | **No** | Sin CRM/pipeline en Synap |
| 2. ¿Cuánto estamos vendiendo realmente? | **Parcial** | Panel día + informe ventas netas |
| 3. ¿Podemos entregar lo vendido? | **Parcial** | Informes pedidos/BO; no en CEO view |
| 4. ¿Riesgo stock, compras o producción? | **Parcial** | Informes sueltos + MPR |
| 5. ¿Dónde está trabada la operación? | **No** | Sin alertas unificadas |
| 6. ¿Qué decisiones requieren intervención? | **No** | Sin Action View |
| 7. ¿Datos engañosos? | **Riesgo sí** | Margen vs ventas; slugs sample |

---

## Anexo B — Archivos clave citados

- `reports/services/executive_sales_summary.py` — motor panel ejecutivo ventas  
- `reports/executive_summary_api_views.py` — API REST  
- `reports/templates/reports/executive_summary.html` — UI  
- `reports/static/reports/js/executive_summary.js` — render KPIs/gráficos  
- `reports/services/query_runner.py` — informes legacy SQL  
- `reports/views.py` — `DashboardDetailView`, slug ejecutivo  
- `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` — spec funcional ventas  
- `mpr/views.py` — `TableroView` manufactura  
- `reports/migrations/0002_seed_initial_reports.py` — seeds declarativos  
- `core/utils/utils.py` — menú CRM comentado  

---

*Informe generado por auditoría estática del repositorio. No se modificó código de aplicación salvo este documento. Validaciones funcionales de campos legacy pendientes deben ejecutarse con negocio y DBA sobre instancia MySQL real.*
