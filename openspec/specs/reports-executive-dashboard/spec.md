# Especificación — API Dashboard gerencial (legacy AdministraNET)

**Capacidad:** `reports-executive-dashboard`  
**Origen archivado:** `dashboard-gerencial-endpoints-legacy` (14/07/2026)  
**Versión de contrato:** `executive-dashboard-v1`  
**Alcance:** Solo lectura MySQL legacy (`base_empresa`). API P0/P1 bajo `/api/reports/executive-dashboard/` y UI Command Center (`command-center-gerencial`).

Referencias: `docs/audits/dashboard-administranet-gap-analysis.md`, `openspec/specs/reports-ejecutivo-ventas/spec.md` (ventas del día — endpoint separado).

---

## Requisitos transversales

### REQ-ED-SEC-01 — Autenticación y permiso

- Todos los endpoints bajo `/api/reports/executive-dashboard/` **MUST** exigir usuario autenticado con **`ManagerialReportsPermission`**.
- Sin `base_empresa` en sesión ni `DEFAULT_BASE_EMPRESA`, la API **MUST** responder **400** con cuerpo JSON `{"detail": "..."}` en español indicando empresa no disponible.

### REQ-ED-SEC-02 — Solo lectura

- Los endpoints **MUST NOT** ejecutar `INSERT`, `UPDATE`, `DELETE` ni transacciones de escritura en MySQL legacy.

### REQ-ED-FILT-01 — Parámetros de consulta comunes

| Parámetro | Formato | Default | Uso |
|-----------|---------|---------|-----|
| `fecha_inicio` | `yyyy-MM-dd` | fecha local (hoy) | Inicio período agregados |
| `fecha_fin` | `yyyy-MM-dd` | fecha local (hoy) | Fin período agregados |
| `fecha` | `yyyy-MM-dd` | — | Atajo legacy: un solo día (`fecha_inicio` = `fecha_fin` = `fecha`) |
| `sucursal` | int o vacío / `todas` | sin filtro | `CodSucursal` en tablas de comprobante |
| `limit` | int 1–500 | 100 | Solo endpoints P1 con filas |
| `offset` | int ≥ 0 | 0 | Solo endpoints P1 |

- Si `fecha_inicio` > `fecha_fin`, la API **MUST** responder **400**.
- Fechas inválidas **MUST** ignorarse con fallback al default (mismo criterio que `executive_summary_api_views._parse_fecha`).

### REQ-ED-META-01 — Metadatos obligatorios

- Toda respuesta **MUST** incluir objeto **`meta`** con al menos:
  - `definicion`: literal `executive-dashboard-v1`
  - `base_empresa`: string usado en la consulta
  - `fecha_referencia`: `yyyy-MM-dd` (derivada de `fecha_fin`; compatibilidad meta)
  - `periodo`: `{ "inicio": "yyyy-MM-dd", "fin": "yyyy-MM-dd" }`
  - `cod_sucursal_filtro`: int o `null`
  - `notas_semanticas`: arreglo de strings (puede estar vacío)

### REQ-ED-ERR-01 — Errores legacy

- Fallo de conexión MySQL **MUST** responder **503** con `detail` en español y `error_type`: `legacy_transient_failure`.
- Parámetros inválidos explícitos **MUST** responder **400** con `error_type`: `invalid_data`.
- El sistema **MUST NOT** devolver datos de muestra (`get_sample_data`) en estos endpoints.

### REQ-ED-TYPE-01 — Tipos AdministraNET

- Valores numéricos enviados a SQL **MUST** normalizarse con `core.utils.administranet_types` (`to_int_or_none`, `to_decimal_or_none`, `to_date_or_none`).
- Montos en JSON **MUST** ser `number` con hasta 2 decimales en agregados monetarios.

### REQ-ED-CACHE-01 — Caché opcional

- Agregados P0 **MAY** usar la misma política de caché que informes (`REPORTS_CACHE_ENABLED`) con clave que incluya `base_empresa`, endpoint, período y sucursal.
- La respuesta **SHOULD** incluir `meta.cached` (bool) cuando aplique.

---

## Orquestador (P0)

### REQ-ED-ORCH-01 — Ruta y método

- **`GET /api/reports/executive-dashboard/`** **MUST** devolver resúmenes de todas las áreas P0 en un solo payload.

### REQ-ED-ORCH-02 — Estructura `areas`

- **`areas.ventas`** **MUST** incluir los mismos campos que `GET .../ventas/resumen/` (subconjunto del área ventas).
- **`areas.inventario`**, **`areas.compras`**, **`areas.manufactura`**, **`areas.cruzados`** **MUST** reflejar sus endpoints de resumen respectivos.
- **`areas.tesoreria`** **MUST** incluir el mismo subconjunto de campos que `GET .../tesoreria/resumen/` (sin `meta` anidado duplicado), incluyendo **`areas.tesoreria.banco`** obtenido con segunda llamada `_safe_legacy_area` (KPIs `librobanco`; **MUST NOT** sumarse con saldos de caja).
- **`areas.ventas_cobros`** **MUST** incluir `facturado_por_medio` y `cobrado_caja_por_medio` (ver `reports-executive-dashboard-ventas-cobros`).
- **`areas.crm`** **MUST NOT** aparecer (CRM deprecado en Command Center v1+).
- **`areas.impuestos`** **MUST NOT** aparecer.

### REQ-ED-ORCH-03 — Tolerancia a fallos parciales

- Si un sub-servicio de área falla con error transitorio, el orquestador **MUST** marcar esa área con `disponible: false` y `error: { "tipo", "mensaje" }` sin fallar todo el payload (**degraded mode**). Aplica a **`areas.tesoreria`**, **`areas.ventas_cobros`** y demás áreas operativas.
- Si falla ventas (área crítica P0), el orquestador **MAY** responder **503** completo (decisión de implementación documentada en design).

### REQ-ED-ORCH-04 — Enlaces

- **`meta.endpoints`** **SHOULD** listar rutas relativas de cada sub-recurso para consumo granular.
- **`meta.endpoints`** **MUST** incluir al menos: `tesoreria`, `ventas_cobros`, `tesoreria_banco`, `tesoreria_movimientos_caja`, `ventas_cobros_detalle`, con rutas bajo `/api/reports/executive-dashboard/`.

---

## Ventas — período (P0)

### REQ-ED-VEN-01 — Ruta

- **`GET /api/reports/executive-dashboard/ventas/resumen/`**

### REQ-ED-VEN-02 — Semántica KPI (alineada a informes legacy)

| Campo JSON | Definición |
|------------|------------|
| `ventas_netas` | Suma FA–NC en `cuentacliente.SubtotalDesc` en `[fecha_inicio, fecha_fin]` (mismos tipos que `_get_ventas_netas_total`) |
| `remitos_no_facturados_monto` | Suma `comp_ped` REM, `Estado='Pendiente'`, no anulados, en período |
| `pedidos_pendientes_monto` | Suma PED `Estado IN ('En preparación','Preparado')`; en resumen período **MUST** usar `filtrar_por_fecha=true` (mismo criterio que `sales_summary` con fechas) |
| `total_operativo` | `ventas_netas + remitos_no_facturados_monto + pedidos_pendientes_monto` |

### REQ-ED-VEN-03 — Campos adicionales

- **`pedidos_pendientes_cantidad`**: conteo de comprobantes PED elegibles (opcional P0 si costo SQL bajo; si no, `null` + nota en `meta.notas_semanticas`).
- **`disponible`**: `true` cuando la consulta finalizó correctamente.

### REQ-ED-VEN-04 — No duplicar ventas del día

- Este endpoint **MUST NOT** reemplazar `GET /api/reports/executive-summary/` (intradía, series, margen, Top 10).
- **`meta.notas_semanticas`** **MUST** incluir referencia a que ventas del día y ventas de período son definiciones distintas.

### REQ-ED-VEN-P1-01 — Detalle pedidos pendientes

- **`GET /api/reports/executive-dashboard/ventas/pedidos-pendientes/`** **MUST** devolver `{ "filas": [...], "total_monto", "total_registros" }` con paginación `limit`/`offset`.
- Columnas mínimas por fila: `codigo_movimiento`, `nro_comprobante`, `fecha`, `codigo_cliente`, `nombre_cliente`, `estado`, `subtotal_desc`.

### REQ-ED-VEN-P1-02 — Detalle remitos no facturados

- **`GET /api/reports/executive-dashboard/ventas/remitos-no-facturados/`** — misma estructura paginada que pedidos.

---

## Inventario (P0)

### REQ-ED-INV-01 — Ruta

- **`GET /api/reports/executive-dashboard/inventario/resumen/`**

### REQ-ED-INV-02 — KPIs agregados

| Campo | Definición |
|-------|------------|
| `valor_stock` | Suma valorizada por `stock_deposito.saldo` × `articulo.PrecioCosto` (paridad Info_Stock `lista_precio=0`) |
| `productos_con_stock` | Conteo de `IDArt` con saldo > 0 en al menos un depósito |
| `productos_bajo_minimo` | Conteo donde disponible (`saldo − reservado` por depósito, agregado por artículo) < `articulo.PuntoPedido` y `PuntoPedido > 0` |
| `productos_sin_stock` | Conteo con stock total 0 y demanda pendiente > 0 (opcional v1: solo conteo con saldo 0) |

- **`valor_stock`**, **`productos_con_stock`**, **`productos_sin_stock`**: snapshot de saldo actual (sin histórico por fecha).
- **`reservado`** y **`productos_bajo_minimo`**: subconsulta PED **MUST** filtrar `comp_ped.Fecha` en `[fecha_inicio, fecha_fin]`.
- Filtro sucursal: cuando informe base no soporta sucursal en existencias, **`meta.notas_semanticas`** **MUST** indicar que `sucursal` no aplica a inventario en v1.

### REQ-ED-INV-P1-01 — Detalle existencias

- **`GET /api/reports/executive-dashboard/inventario/existencias/`** **MUST** devolver filas paginadas reutilizando criterios del slug `stock-existencias` (sin reimplementar búsqueda predictiva del cliente).

---

## Compras (P0)

### REQ-ED-COMP-01 — Ruta

- **`GET /api/reports/executive-dashboard/compras/resumen/`**

### REQ-ED-COMP-02 — KPIs v1 (paridad BO / OC pendiente)

| Campo | Definición |
|-------|------------|
| `oc_pendientes_cantidad` | Conteo de comprobantes `cuentaproveedor` con `TipoComprobante='OC'`, `Estado='Pendiente'`, `Anulado='No'` con renglón pendiente en `stockp` |
| `oc_pendientes_unidades` | Suma unidades pendientes en esos renglones |
| `oc_pendientes_importe` | Suma `stockp.PrecioNetoxR` pendiente (o criterio documentado equivalente al informe BO) |

- SQL **MUST** alinearse a subconsulta `oc_pendiente` de `_run_backorder_vs_stock_vs_facturacion` (no usar `stock_deposito.saldo_pedido_proveedor`).
- Las OC contabilizadas **MUST** tener `cuentaproveedor.Fecha` dentro de `[fecha_inicio, fecha_fin]` (Command Center; distinto del subquery BO que no filtra fecha en OC pendiente).

### REQ-ED-COMP-03 — Validación

- **`meta.notas_semanticas`** **MUST** documentar criterio de fecha (`cp_oc.Fecha` en período) y paridad con subconsulta BO.
- **`compras_validacion: pendiente_vb6`** **MUST NOT** aparecer tras validación (2026-05).

---

## Manufactura (P0)

### REQ-ED-MFG-01 — Ruta

- **`GET /api/reports/executive-dashboard/manufactura/resumen/`**

### REQ-ED-MFG-02 — KPIs (paridad tablero MPR)

| Campo | Fuente lógica |
|-------|----------------|
| `pedidos_fabrica_pendientes` | `len(listar_pedidos_fabrica(..., estado='Pendiente'))` o equivalente sin límite 500 en agregado |
| `opt_atrasadas` | Cantidad de `id_lista_produccion` distintos en `listar_opt_listado(..., solo_atrasadas=True)` |
| `unidades_pendientes_produccion` | Suma `cantidad_pendiente_prod` de `listar_lista_produccion_agrupada` |
| `items_urgentes` | Mínimo entre 15 y ventana pack + atrasadas (misma heurística que `TableroView`) |

- El área **`manufactura`** y el endpoint **`.../manufactura/resumen/`** **MUST** omitirse (UI y orquestador) cuando el módulo **`mpr`** no está activo en `ModuleConfig` (`ModuleManager.is_module_active('mpr')`).
- **`meta.modulos.mpr`** **MUST** indicar `true`/`false` en el orquestador.
- Todas las fuentes MPR del resumen **MUST** recibir `fecha_desde` / `fecha_hasta` del período: `comp_ped.Fecha` en pedidos de fábrica; demanda/OPT vía pedidos vinculados en `lista_produccion_detalle` o `fecha_objetivo` cuando no hay pedido.

### REQ-ED-MFG-03 — Error de esquema MPR

- Si `MprSchemaError`, el área **MUST** responder `disponible: false` y `error.tipo`: `mpr_schema_not_ready` (HTTP 200 en endpoint de área; orquestador en modo degradado).

---

## Cruzados (P0)

**Etiqueta UI (Command Center):** «Demanda pendiente» — el slug API `cruzados` y la clave `areas.cruzados` no cambian.

### REQ-ED-CRUZ-01 — Ruta

- **`GET /api/reports/executive-dashboard/cruzados/resumen/`**

### REQ-ED-CRUZ-02 — Totales sin detalle masivo

| Campo | Definición |
|-------|------------|
| `backorder_importe` | Suma `bo_importe` agregada por artículo (misma SQL agregada que BO, sin límite 1000 filas en respuesta) |
| `backorder_unidades` | Suma cantidades BO |
| `stock_reservado_unidades` | Suma reservado PED En preparación/Preparado |
| `facturacion_periodo` | Total facturación FA–NC en período (opcional `fecha_inicio_facturacion` / `fecha_fin_facturacion`; default = período principal) |
| `demand_coverage_pct` | Si `backorder_importe > 0`: `100 * (1 - faltante_cubierto/bo)` según reglas BO simplificadas en agregado; si BO=0, `null` |

### REQ-ED-CRUZ-P1-01 — Detalle backorder

- **`GET /api/reports/executive-dashboard/cruzados/backorder/`** **MUST** paginar filas (máx `limit` 500) con columnas alineadas al informe `bo-stock-facturacion`.

---

## Inventario existencias (P1) — búsqueda

- **`GET /api/reports/executive-dashboard/inventario/existencias/`** **MAY** aceptar `busqueda` o `q` (≥ 2 caracteres) para filtrar en servidor (artículo, código, depósito, marca, rubro).
- Command Center **MUST** exponer buscador predictivo en el modal de existencias (debounce, mín. 2 caracteres, usable en móvil).

---

## Tesorería (P0/P1)

Ver spec dedicada: **`openspec/specs/reports-executive-dashboard-tesoreria/spec.md`**.

- P0: **`GET .../tesoreria/resumen/`** — saldos y flujos en caja (`caja`, `caja_abm`); `banco_disponible=false`.
- P1: **`GET .../tesoreria/banco/resumen/`** — KPIs `librobanco` + `cuenta_banco` (anidado en orquestador, no sumado con caja).
- P1: **`GET .../tesoreria/movimientos-caja/`** — listado paginado (excluye cierre/transferencia).

---

## Ventas por medio de cobro (P0/P1)

Ver spec dedicada: **`openspec/specs/reports-executive-dashboard-ventas-cobros/spec.md`**.

- P0: **`GET .../ventas/cobros/resumen/`** — `facturado_por_medio` y `cobrado_caja_por_medio`.
- P1: **`GET .../ventas/cobros/detalle/`** — filas paginadas con fallback caja + `medio_cobpag` REC.

---

## CRM — deprecado

- El módulo CRM AdministraNET **no** forma parte del Command Center.
- El orquestador **MUST NOT** incluir `areas.crm` en respuestas v1+.
- No implementar endpoints CRM salvo decisión explícita de producto.

---

## Escenarios de aceptación

1. **Dado** usuario gerencial con `base_empresa` válida, **cuando** `GET /api/reports/executive-dashboard/?fecha=2026-05-11`, **entonces** respuesta 200 con `meta.definicion=executive-dashboard-v1` y siete áreas operativas (`ventas`, `inventario`, `compras`, `manufactura`, `cruzados`, `tesoreria`, `ventas_cobros`) sin CRM ni `impuestos`.

2. **Dado** período mayo 2026 y sucursal 3, **cuando** `GET .../ventas/resumen/?fecha_inicio=2026-05-01&fecha_fin=2026-05-11&sucursal=3`, **entonces** `meta.cod_sucursal_filtro=3` y montos ≥ 0.

3. **Dado** usuario sin permiso gerencial, **cuando** cualquier ruta executive-dashboard, **entonces** 403.

4. **Dado** MySQL no disponible, **cuando** `GET .../inventario/resumen/`, **entonces** 503 con `error_type=legacy_transient_failure`.

5. **Dado** esquema MPR incompleto, **cuando** `GET .../manufactura/resumen/`, **entonces** 200 con `disponible=false` y sin excepción no capturada.

6. **Dado** `fecha_inicio` posterior a `fecha_fin`, **cuando** cualquier endpoint con período, **entonces** 400.

7. **Dado** implementación P1, **cuando** `GET .../ventas/pedidos-pendientes/?limit=50&offset=0`, **entonces** máximo 50 filas y `total_registros` ≥ cantidad de filas devueltas.

---

## Fuera de alcance (v1)

- Semáforos, Operational Health Score.
- Escritura legacy.
- CRM con datos reales.
- Sustitución de `POST /api/reports/query/`.

## Evolución post-spec (implementación)

- **Tesorería y ventas por cobro (P0/P1):** implementado y archivado en `adminnet-module-migration-command-center-finance` (14/07/2026). Specs: `reports-executive-dashboard-tesoreria`, `reports-executive-dashboard-ventas-cobros`.
- Refactor T13: delegación `query_runner` → `ventas_metrics` (completado en change `dashboard-gerencial-endpoints-legacy`).
- Clasificación caja compartida: `reports/services/executive_dashboard/caja_classification.py` (REC→cobranzas, FA→ventas).
