# Especificación: dashboard «Resumen general» (panel ejecutivo de ventas)

## Alcance

- **Vista nueva** en el módulo **Reportes**: **Resumen general** — panel ejecutivo con KPIs y gráficos de **ventas facturadas** (solo `cuentacliente`), visible según **permisos gerenciales**.
- **CRUD de clasificación de puntos de venta (PV)** para el dashboard: **no es pantalla aparte**; se abre en un **modal** desde el **mismo indicador KPI** «Mayorista vs Salón (minorista)», mediante un **icono de engranaje** (Material: `settings` o equivalente en el sistema de iconos Synap) en la tarjeta del KPI. Dentro del modal: **tres columnas** (izquierda / centro / derecha), **arrastre** y **botones de dirección**; el centro lista PV **activos en AdministraNET** y **no anulados**, pendientes de clasificar.
- **Fuente temporal intradiaria:** agrupación por hora usando **`cuentacliente.FechaControl`** (ver § Fuentes de datos). **Fecha contable del comprobante:** `cuentacliente.Fecha` para totales diarios y serie de 7 días.

## Objetivo de producto

Ofrecer a dirección una **lectura rápida** del día: monto, comparativos, tickets, ticket medio, unidades, reparto mayorista/salón, curva horaria y tendencia semanal, **sin** mezclar remitos no facturados ni pedidos pendientes en estos indicadores (solo facturación).

---

## Permisos y alcance de datos

| Tema | Regla |
|------|--------|
| Nivel | **Dashboard gerencial.** Requiere permiso equivalente a **`reports.view_managerial`** (y usuario autenticado con empresa activa). |
| Visibilidad | Quien tiene acceso gerencial al informe ve **el detalle completo** de la empresa: **sin** restricción obligatoria por sucursal o PV. El panel incluye filtro **opcional por sucursal** (`cuentacliente.CodSucursal`): por defecto **todas**; al elegir una sucursal, **todos** los agregados (KPIs, series, split mayorista/salón y Top 10) se calculan solo para esa sucursal. |
| Permiso CRUD PV | Definir en implementación (p. ej. mismo permiso gerencial o **`configuracion.empresa`** / grupo **Ventas** con permiso dedicado `ventas.config_pv_canal` — cerrar al desarrollar). |

---

## Reglas de negocio: facturación (base de todos los KPIs)

| Tema | Regla |
|------|--------|
| Tabla | **`cuentacliente`** (base AdministraNET de la empresa). |
| Comprobantes | Misma familia que informes de ventas netas: `TipoComprobante IN ('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM')`. |
| Anulados | `Anulado = 'No'`. |
| Movimiento | `CodigoMovimiento <> 0`. |
| Ventas netas (importe) | Por línea de comprobante: facturas suman `SubtotalDesc`; notas de crédito restan `SubtotalDesc` (criterio alineado a [`reports/services/query_runner.py`](../../reports/services/query_runner.py) `_get_ventas_netas_total` / [`ventas_netas.py`](../../reports/services/ventas_netas.py)). |
| Día «hoy» | **`Fecha`** = fecha de comprobante en zona acordada (ver § Zona horaria). Para comparativos se usan los **mismos** criterios de filtro de fecha que en el resto de reportes (fecha servidor de aplicación o parámetro explícito si el producto lo expone). |
| Serie horaria (eje X = hora) | Filtrar filas del día por **`Fecha` = día seleccionado** y agrupar por **hora extraída de `FechaControl`** (no usar `Fecha` para la hora: es tipo `DATE` sin componente horario). |

---

## KPIs (definiciones)

| KPI | Definición |
|-----|------------|
| **Ventas del día (total)** | Suma de **ventas netas** (importe) para `Fecha` = día objetivo. |
| **Ventas vs ayer (%)** | `((Ventas_hoy − Ventas_ayer) / NULLIF(Ventas_ayer, 0)) × 100`. Si ayer es 0 y hoy > 0, política de UI: mostrar «N/D» o «+100 %» según criterio de producto. |
| **Ventas vs ayer (monto)** | Diferencia **`Ventas_hoy − Ventas_ayer`** en moneda (campo API `gap_vs_ayer_monto`). La UI del KPI «Vs ayer» **MUST** mostrar **% y monto** en la misma tarjeta. |
| **Ventas vs mismo día semana pasada** | Misma fórmula comparando `Fecha` = hoy vs `Fecha` = hoy − 7 días. |
| **Cantidad de tickets** | Número de **comprobantes de venta** (FA–FM) en el día, **sin** contar notas de crédito como ticket adicional (definición: un ticket = una factura de venta). Las NC ajustan monto en ventas netas pero no incrementan el conteo de tickets. |
| **Ticket promedio** | `Ventas_netas_del_día / NULLIF(Cantidad_tickets, 0)` usando la misma ventana de `Fecha` y los mismos filtros. |
| **Unidades vendidas** | Misma lógica numérica que el informe de objetivos / ventas netas por unidades: renglones **`stock`** ligados a `cuentacliente` por `CodigoMovimiento`, con signo según factura vs NC. Rango: **`stock.Fecha`** coherente con el día de facturación del informe (paridad [`ventas_netas.py`](../../reports/services/ventas_netas.py) `_sum_unidades_sql_stock_line` y filtros `TipoComp` alineados al proyecto). |
| **Mayorista vs Salón (minorista)** | Suma de **ventas netas** del día agrupada por **canal derivado del PV** según la configuración del **modal** (§ CRUD). En la tarjeta del KPI: **icono engranaje** para abrir el modal. PV **sin clasificar** pueden excluirse del reparto o agruparse en «Sin asignar» según decisión de implementación (documentar en release). |
| **Top 10 productos (v1)** | Hasta **10** artículos (`IDArt`) del día; mismos filtros que **Unidades vendidas** (`stock` + `cuentacliente`, `TipoComp`, `Anulado`, y sucursal si aplica). **Orden** configurable: por **venta neta** (suma de `stock.PrecioNetoxR` con signo FA/NC, descendente) o por **unidades** (suma neta de cantidades, descendente); desempate con la otra métrica. Cada fila incluye código, descripción, unidades e importe neto. API: `meta.top_productos_criterio` = `importe_neto_linea`; `meta.top_productos_orden` = `importe_neto` \| `unidades`. |
| **Margen bruto del día** | Sobre renglones **`stock`** del mismo día y filtros que **Unidades vendidas** / Top 10: suma de `PrecioNetoxR` (**venta neta líneas**) con signo FA/NC y **costo normalizado** según **`configuracion`**: si `utiliza_embalaje='Si'` y (`utiliza_bulto_cerrado='Si'` o `utiliza_display='Si'`), escala empaque con `PrecioCostoxU × Cantidad / divisor` (Bulto: `multiplicador_comp`; fraccionado TPV: `cantidad_unidad_display`); si no, `PrecioCostoxU × Cantidad` (fallback `PrecioCostoxR`). API: `meta.utiliza_embalaje_display_bulto`, `meta.margen_costo_criterio`. |
| **Margen por rubro / subrubro** | Agregación por `articulo` → `rubro` y `subrubro`; **Top 10** por venta neta del grupo descendente (SQL `LIMIT 10`); sin clasificación → **«Sin clasificar»**. |

---

## Gráficos

| Gráfico | Descripción |
|---------|-------------|
| **Ventas por hora (día actual)** | Eje X: horas 0–23 (o franjas configurables). Eje Y: ventas netas del día. Agregación: sumar ventas netas por comprobante usando **`FechaControl`** para la hora, con **`Fecha`** = día seleccionado. |
| **Comparativo semanal** | Últimos **7 días** calendario (incluyendo hoy): una serie de **ventas netas diarias** (`Fecha` + mismas reglas de facturación). |

---

## Zona horaria

- **`Fecha` y `FechaControl`** se interpretan según **zona horaria del servidor MySQL** o conversión explícita a la **zona de la empresa** (recomendado alinear con [`docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md`](../general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md) / «fecha servidor» donde aplique).
- La spec exige **una sola política** documentada en implementación (p. ej. `CONVERT_TZ` o sesión `time_zone` fijada en el pool de conexiones de reportes).

---

## CRUD: clasificación Mayorista / Minorista (Salón)

### Ubicación en UI

- **Contenedor:** **modal** superpuesto al dashboard (mismo contexto de **Resumen general**), no ruta nueva.
- **Apertura:** desde la **tarjeta KPI** que muestra el reparto **Mayorista vs Salón**, botón/icono **engranaje** visible para usuarios con permiso de configuración (ver § Permisos — «Permiso CRUD PV»). Quienes solo lean el KPI no ven el engranaje o lo ven deshabilitado según política de permisos.
- **Cierre:** acciones típicas **Guardar** / **Cancelar** (o solo **Cerrar** si no hubo cambios); opcional **ESC** para cerrar con confirmación si hay cambios sin guardar.

### UX (contenido del modal)

- **Tres columnas:** (1) **Mayorista**, (2) **Puntos de venta sin asignar**, (3) **Minorista (Salón)**.
- **Origen lista central:** PV cargados desde AdministraNET (`punto_venta`), **no anulados** y **habilitados** según criterio de negocio (p. ej. `anulado` / flags equivalentes en el esquema real).
- **Interacción:** **arrastrar y soltar** entre columnas y/o **botones** con iconos de flecha (mover a izquierda, a derecha, al centro).
- **Persistencia:** al **Guardar**, se almacena la asignación por **`id_pv`** (y ámbito **empresa** / `base_empresa`).
- **Contadores** opcionales por columna para validación visual.

### Modelo de datos (implementación)

- **Opción A (recomendada para no tocar VB6):** tabla de configuración en **Synap (PostgreSQL/SQLite según proyecto)** con `base_empresa` o `empresa_id`, `id_pv`, `canal` ∈ { `mayorista`, `minorista` }, unicidad `(empresa, id_pv)`.
- **Opción B (legacy MySQL):** nueva columna en `punto_venta` o tabla satélite en MySQL, gestionada vía [`core/services/legacy_mysql_schema/catalog.py`](../../core/services/legacy_mysql_schema/catalog.py) según [HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md](../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md).

**Nota:** La evolución futura a tipos finos (**Normal, Mayorista, TPV, Ecom minorista, Ecom mayorista**) puede mapearse a subetiquetas dentro de Mayorista/Minorista o ampliar el enum; la **v1** de esta spec es el **reparto binario** más columna central de **sin asignar**.

---

## API y UI (contrato sugerido)

- **Ruta sugerida (front):** entrada desde **Reportes** — ítem **Resumen general** o home del submódulo ventas/reportes (cerrar en diseño de navegación).
- **Backend:** endpoint dedicado (p. ej. `GET /api/reports/executive-summary/` o ampliación de `reports-query` con `slug` reservado) que devuelva en un solo payload:
  - `fecha_referencia`, `kpis` (incluye `gap_vs_ayer_monto`), `serie_horaria[]`, `serie_7_dias[]`, `split_mayorista_minorista` (montos y/o %),
  - `top_productos[]` (hasta 10 ítems; ver tabla KPIs),
  - `margen_bruto` (totales día: `venta_neta_lineas`, `costo_neto_lineas`, `margen_absoluto`, `pct_sobre_venta_lineas`), `margen_por_rubro[]` (hasta 10), `margen_por_subrubro[]` (hasta 10); en `meta`: `definicion` = `executive-sales-v2`, `margen_costo_criterio`, `margen_venta_criterio`.
  - `meta` con zona horaria aplicada, versión de definición y `top_productos_criterio`.
- **CRUD (modal):** `GET` al abrir el modal (estado actual por PV) y `PUT` al **Guardar**; tras éxito, cerrar modal y **refrescar** el KPI «Mayorista vs Salón» (y totales que dependan del canal si aplica).

---

## Pruebas

- Tests de **contrato** (estructura JSON, límites de horas 0–23, suma de serie horaria vs total del día con tolerancia de redondeo).
- **Integración** opcional contra base de prueba con `cuentacliente` + `stock` cuando exista el runner.

---

## Referencias de código existente

- Totales ventas netas: [`reports/services/query_runner.py`](../../reports/services/query_runner.py) (`_get_ventas_netas_total`).
- Unidades: [`reports/services/ventas_netas.py`](../../reports/services/ventas_netas.py).
- Permisos reportes: [`reports/permissions.py`](../../reports/permissions.py) (`ManagerialReportsPermission`).
- UI reportes: [`reports/templates/reports/dashboard_detail.html`](../../reports/templates/reports/dashboard_detail.html), [`reports/static/reports/js/dashboard.js`](../../reports/static/reports/js/dashboard.js).
- Esquema `cuentacliente`: [`docs/general/tablas/cuentacliente.md`](../general/tablas/cuentacliente.md) — campo horario: **`FechaControl`**.

---

## Resumen de decisiones cerradas

| Decisión | Valor |
|----------|--------|
| Alcance monetario | Solo **facturación** (`cuentacliente`), sin remitos ni pedidos pendientes en estos KPIs. |
| Hora del gráfico intradiario | **`cuentacliente.FechaControl`**. |
| Día contable | **`cuentacliente.Fecha`**. |
| Nivel | **Gerencial**; visión **completa** con permiso. |
| Clasificación PV | **Modal** en el KPI «Mayorista vs Salón**, apertura con **icono engranaje**; tres columnas; **Mayorista** vs **Minorista (Salón)** + **sin asignar** al centro. |

---

## Implementación (Synap)

| Elemento | Ubicación |
|----------|-----------|
| Modelo clasificación PV | `reports.models.PuntoVentaCanalEjecutivo` (Synap DB; único por empresa + `id_pv`). |
| Agregados SQL | `reports/services/executive_sales_summary.py`. |
| API JSON | `GET /api/reports/executive-summary/` y `GET|PUT /api/reports/pv-canal-ejecutivo/` (`reports/executive_summary_api_views.py`). Permiso: **`reports.view_managerial`**. La empresa Django para guardar PV se resuelve con **`core.utils.empresa_sesion.get_empresa_django_from_request`** (sesión `base_empresa` + cruce CUIT/nombre con `core.Empresa`, no solo `request.user.empresa_activa`). **Query `GET /api/reports/executive-summary/`:** `fecha` (yyyy-MM-dd, opcional); `sucursal` (id `id_sucursal` numérico, opcional; vacío o `todas` = global); `top_orden` = `importe_neto` \| `unidades` (opcional, defecto importe). Respuesta incluye `sucursales_disponibles` (lista `{ id_sucursal, nombre_sucursal }` desde MySQL `sucursales` no anuladas) y `meta.cod_sucursal_filtro` / `meta.top_productos_orden` con los valores aplicados. |
| Vista HTML | `DashboardDetailView` usa plantilla `reports/executive_summary.html` si `slug=resumen-ejecutivo-ventas`. |
| Front | `reports/static/reports/js/executive_summary.js` (d3 v7 por CDN); select **Sucursal** (todas + opciones desde API) y **Orden Top 10** (venta neta / unidades; aplica a artículos); KPI «Vs ayer» con % + gap en $. **Rentabilidad del día:** KPIs venta/costo/margen por líneas y **Top 10** en orden **artículos → rubro → subrubro** (tabla en `lg+`, tarjetas en móvil). |
| Catálogo | `ReportDefinition` slug **`resumen-ejecutivo-ventas`** (migración `0034`). |
| Tests | `reports/tests/test_executive_summary_contract.py`. |
| Migración PostgreSQL | `reports/migrations/0031_add_puntoventacanalejecutivo.py` crea solo la tabla `reports_puntoventacanalejecutivo`. No usar en servidor un `makemigrations` autogenerado que vuelva a declarar modelos ya creados por migraciones `RunPython` (riesgo `DuplicateTable`). |
| Reparación servidor | Comando `python manage.py repair_panel_ejecutivo_postgres` (opción `--fix`): revisa tabla vs migración `0031_add_puntoventacanalejecutivo`; si falta la tabla ejecuta `migrate`; si la tabla existe y la migración no está aplicada, valida columnas y ejecuta `migrate --fake`. **`SYNAP_MIGRATIONS_POSTGRES_ONLY=1`** al llamar `migrate` / este comando si MySQL legacy es anterior a 8 (ver `django_project/settings.py`). |
| Arranque Docker | El comando `fix_reports_migrations` (entrypoint) **no debe** borrar `0031_add_puntoventacanalejecutivo.py`: versiones antiguas solo admitían migraciones hasta 0029 y eliminaban archivos `0031_*`; usar código que incluya el ajuste en `core/management/commands/fix_reports_migrations.py` (prefijos válidos hasta 0031). |
| Archivo borrado en disco | Con bind mount `.:/app`, si el archivo se borró en el host, **`git pull` no lo repone** si no tocó ese path en los commits. Ejecutar: `git restore reports/migrations/0031_add_puntoventacanalejecutivo.py` (desde la raíz del repo en el servidor). |

**UI (abr. 2026):** pantalla alineada visualmente al **catálogo de Reportes** (hero con gradiente, migas de pan), **Ventas** (cabecera oscura `slate`, botones sky/indigo) y **MPR** (tarjetas KPI con icono Material, hover y sombras). KPIs con barra lateral en color por métrica; comparativas `%` con badge verde/rojo; gráficos d3 con área degradada, rejilla y curva `curveMonotoneX`; modal PV con `backdrop-blur`, columnas por color (ámbar / gris / esmeralda) y CTA en gradiente purple/indigo. **Responsive:** `ResizeObserver` redibuja al cambiar ancho; eje horario con menos ticks y etiquetas numéricas horizontales bajo 768px; eje Y y márgenes izquierdos compactos en móvil; altura de gráfico reducida en viewports angostos.

**Extensión (may. 2026):** KPI «Vs ayer» con **delta en moneda** además del %; sección **Top 10 productos** (tabla en `lg+`, tarjetas en móvil). Cambio SDD archivado: `openspec/changes/archive/2026-05-11-executive-dashboard-top10-gap-usd/`. Spec consolidada: `openspec/specs/reports-ejecutivo-ventas/spec.md`.

**Implementado (11/05/2026):** bloque **Rentabilidad del día** (UI): margen bruto total y tablas por rubro y subrubro; contrato API ampliado (`openspec/changes/resumen-gerencial-margen-bruto/`). El % de margen del bloque rentabilidad es sobre **venta neta de líneas** del universo `stock` definido.

**Implementado (29/05/2026):** tablas **Top 10** unificadas en la sección rentabilidad: **artículos** (orden configurable), **rubro** y **subrubro** (por venta neta); backend con `LIMIT 10` en SQL de rubro/subrubro.

**Implementado (29/05/2026):** costo de margen **normalizado Display/Bulto** (`margen_costo_linea.py`): deja de sumar `PrecioCostoxR` crudo; usa unidad base × matriz VB6. Cambio SDD: `openspec/changes/margen-ejecutivo-costo-display-bulto/`.
