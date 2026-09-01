# Plan: filtros Punto de venta y/o Sucursal en reportes de ventas

**Fecha:** 31/08/2026  
**Estado:** propuesto (pendiente de confirmación de excepciones)  
**Objetivo:** todo informe de ventas del catálogo `/reports/` debe poder acotarse por **sucursal**, por **punto de venta (PV)**, o por **ambos**. Vacío = todas.

---

## 1. Contrato canónico

### 1.1 Semántica «y/o»

| Selección | Comportamiento |
|-----------|----------------|
| Ninguna sucursal y ningún PV | Universo completo (como hoy) |
| Solo sucursales | `CodSucursal IN (...)` |
| Solo PVs | `id_pv IN (...)` |
| Sucursales **y** PVs | **AND** (intersección). Un PV de otra sucursal no entra. |

No es un OR. «Y/o» significa que cada filtro es opcional e independiente; si vienen los dos, se combinan.

### 1.2 Payload (JSON `filters`)

| Campo | Tipo | Valor | Vacío |
|-------|------|--------|--------|
| `sucursales` | `list[int]` | `sucursales.id_sucursal` | omitir o `[]` = todas |
| `punto_venta` | `list[int]` | `punto_venta.id_punto_venta` | omitir o `[]` = todas |

Alias admitidos en runners (ya existen en BOM): `puntos_venta` → mismo que `punto_venta`. No introducir `sucursal` (singular) salvo compat de querystring en Command Center / Resumen ejecutivo.

Normalización: reutilizar `QueryRunnerService._parse_sucursales_pv()` (enteros, ignorar no numéricos).

### 1.3 Columnas MySQL (AdministraNET)

| Fuente | Sucursal | PV |
|--------|----------|-----|
| `cuentacliente` (facturación / NC) | `cc.CodSucursal` | `cc.id_pv` |
| `comp_ped` (PED / REM / PRE) | `cp.CodSucursal` | `cp.id_pv` |
| Catálogo de opciones | `sucursales.id_sucursal` (`anulado = 'No'`) | `punto_venta.id_punto_venta` (`anulado = 'No'`). Relación: `punto_venta.id_sucursal` |

### 1.4 UI

- Multiselect tags (mismo patrón que VO): `name="sucursales"` / `name="punto_venta"`.
- Hint: «Si no seleccionás ninguna, se mostrarán todas».
- Includes a reutilizar (no crear un tercero):
  - Familia VO / marcas / BOM: `reports/templates/reports/includes/filters_bo_punto_venta_sucursales_depositos_clientes.html`
  - Informes simples (período + sucursal/PV): `reports/templates/reports/includes/filters_sucursal_punto_venta.html`
- Opciones: `GET /api/reports/filters/?type=sucursales` y `?type=puntos_venta` (ya usados por `dashboard.js` / `tags_filter.mjs`). La API de PV ya devuelve `sucursal_id` (base para cascada).
- JS: `loadFilterOptions()` en `dashboard.js` **no carga PV** para la familia BO salvo `ventas-marcas-mensual` (ADR ~línea 6683). Levantar el gate **solo** para slugs de ventas (VO, VPV, VPA, VMSA, BOM); **no** para `bo-stock-facturacion`.
- **No usar** `filters_punto_venta_sucursales.html` (huérfano).
- **Cascada (recomendado, no bloqueante):** si hay sucursales elegidas, el desplegable de PV muestra solo PVs con `punto_venta.id_sucursal` en esa lista. Si no hay sucursal, el PV lista todos. El usuario puede filtrar **solo por PV** sin tocar sucursal. Implementar en `tags_filter.mjs`, no en un include nuevo.

### 1.5 Export

Excel/CSV del mismo slug debe respetar los mismos `filters`. No hay canal paralelo.

En informes de ventas, el bloque **Filtros aplicados** (y la hoja **Filtros** en licenciatarios) **siempre** declara el alcance:

| Filtro | Vacío | Con IDs |
|--------|-------|---------|
| Sucursales | `Todas` | Nombres (`sucursales.nombre_sucursal`); si no hay lookup, IDs |
| Puntos de venta | `Todos` | `PV {nro_punto_venta}`; si no hay lookup, IDs |

En pantalla, el resumen del período concatena `Sucursales: … · Puntos de venta: …` con los nombres de las etiquetas seleccionadas (vacío = Todas/Todos). No cambia el grano de las filas agregadas.

---

## 2. Matriz actual (31/08/2026)

Leyenda: **OK** = UI + SQL; **UI−** = SQL sí, include no; **NO** = falta ambos; **PARCIAL** = solo uno de los dos filtros.

| Informe | Slug | Sucursal UI | PV UI | Sucursal SQL | PV SQL | Estado |
|---------|------|-------------|-------|--------------|--------|--------|
| Ventas Netas | `ventas-netas` | Sí (`filters_sucursal_punto_venta`) | Sí | Sí (`cc.CodSucursal`) | Sí (`cc.id_pv`) | **OK** (dashboard). Relay `ventas_netas.py`: PV **escalar** `punto_venta_id`, sucursal **no** en whitelist |
| Objetivos de ventas por vendedor | `ventas-objetivos-vs-bo` | Sí (include BO) | **No** (PV solo si slug = VMM) | Sí | Sí (runner) | **UI− PV** |
| Ventas por vendedor | `ventas-por-vendedor` | Sí | **No** | Sí | Sí | **UI− PV** |
| Ventas por artículo | `ventas-por-articulo` | Sí | **No** | Sí | Sí | **UI− PV** |
| Ventas marcas mensual | `ventas-marcas-mensual` | Sí | Sí | Sí | Sí | **OK** |
| Ventas por marca y SuperArt | `ventas-marca-superart` | Sí | **No** | Sí | Sí | **UI− PV** |
| Ventas BOM en docenas | `ventas-bom-docenas` | Sí | **No** | Sí | Sí | **UI− PV** |
| Total Consolidado Operativo | `total-consolidado-operativo` | Sí | Sí | Sí (`query_runner`) | Sí | **OK** |
| Pedidos pendientes | `pedidos-pendientes` | **No** | **No** | Sí | Sí | **Fuera de alcance** (producto 31/08/2026) |
| Remitos no facturados | `remitos-no-facturados` | **No** | **No** | Sí | Sí | **Fuera de alcance** (producto 31/08/2026) |
| BO vs Stock vs Facturación | `bo-stock-facturacion` | Sí | **No** | Sí | Parse muerto, no SQL | **Fuera de alcance** (producto 31/08/2026). No tocar UI ni runner. |
| Ventas Mensuales Licenciatarios | `ventas-mensuales-licenciatarios` | No (spec: «alcance global») | No | No (`ventas_mensuales_licenciatarios_query.py`) | No | **NO** |
| Clientes sin ventas por vendedor | `clientes-sin-ventas-vendedor` | No | No | No | No | **NO** |
| Resumen ejecutivo (ventas) | `resumen-ejecutivo-ventas` | Sí (multiselect **clasificadas**) | **No** | Sí (`CodSucursal` en alcance) | No | **PARCIAL** |
| Command Center gerencial | `command-center-gerencial` | Sí (**select simple**) | **No** | Sí (`cod_sucursal`) | Área ventas: helpers aceptan lista PV en `ventas_metrics.py`, UI no los manda | **PARCIAL** |
| Evolución de precios | `evolucion-precios` | No | No | N/A (`precios_historial`, no es movimiento de venta) | N/A | Ver §3 |
| Documento — Presupuesto de ventas | `documento-presupuesto-ventas` | No | No | N/A (documento por `codigo_movimiento`) | N/A | Ver §3 |

**Fuera de alcance (confirmado 31/08/2026):** `bo-stock-facturacion`, `pedidos-pendientes`, `remitos-no-facturados`. No cambiar templates, JS ni SQL de esos slugs. El include BO es compartido: el PV se muestra **solo** en slugs de ventas (VO, VPV, VPA, VMSA, BOM, VMM), **nunca** en BO vs stock.

---

## 3. Excepciones

| Ítem | Decisión | Motivo |
|------|----------|--------|
| `bo-stock-facturacion` | **Fuera de alcance (confirmado)** | Producto 31/08/2026: no se toca. El include BO es compartido: **no** mostrar PV en este slug. |
| `pedidos-pendientes` | **Fuera de alcance (confirmado)** | Producto 31/08/2026: no se toca UI, `collectFilters` ni SQL. |
| `remitos-no-facturados` | **Fuera de alcance (confirmado)** | Producto 31/08/2026: no se toca (tampoco el slug viejo `uninvoiced_remitos`). |
| `documento-presupuesto-ventas` | **Fuera de alcance** | No es un listado: exporta un PRE ya identificado. |
| `evolucion-precios` | **Fuera de alcance** | Ranking de `precios_historial`, no facturación. |
| `ventas-mensuales-licenciatarios` | **Incluir, solo tramo AdministraNET** | Seed pre-cutover sin PV/sucursal; filtrar solo ANET post-cutover. |
| Resumen ejecutivo | **Incluir PV** | Dentro de sucursales clasificadas. |
| Command Center | **Incluir PV** | Además de sucursal; deep-links a VMM/VO. |

---

## 4. Oleadas de implementación

### Oleada 1 — Mostrar PV en informes de ventas de la familia BO

**Esfuerzo bajo. Sin cambio de métricas.** Runners de VO/VPV/VPA/VMSA/BOM **ya filtran PV**; la UI lo oculta salvo VMM.

**No tocar:** `bo-stock-facturacion`, `pedidos-pendientes`, `remitos-no-facturados`, `uninvoiced_remitos`, `_run_backorder_vs_stock_vs_facturacion`, ni el branch de `collectFilters` de pedidos.

1. En `filters_bo_punto_venta_sucursales_depositos_clientes.html`, ampliar el `{% if %}` del bloque Punto de venta a los slugs de ventas:
   - `ventas-marcas-mensual`, `ventas-objetivos-vs-bo`, `ventas-por-vendedor`, `ventas-por-articulo`, `ventas-marca-superart`, `ventas-bom-docenas`
   - **Excluir** `bo-stock-facturacion` (el include es compartido).
2. En `dashboard.js` `loadFilterOptions()`, cargar PV para esos slugs de ventas. Mantener el skip de PV en `bo-stock-facturacion` (`loadPuntoVentaOptions` no debe volverse verdadero para ese slug).
3. Tests de template: VO/VPV/VPA/VMSA/BOM renderizan `id="punto_venta"`; BO vs stock **no**. Tests de runner: payload PV en VO/VPA si falta (VMM ya tiene `test_filtro_punto_venta_incluye_id_pv_en_sql`).

**Archivos:** `filters_bo_punto_venta_sucursales_depositos_clientes.html`, `dashboard.js` (solo el gate de carga de PV), tests.

### Oleada 2 — Informes operativos sin filtro

#### 2.A Ventas Mensuales Licenciatarios

1. UI: incluir `filters_sucursal_punto_venta.html` **después** del bloque de pack/período en `filters_ventas_mensuales_licenciatarios.html` (o en `dashboard_detail.html` para ese slug).
2. Backend: `build_anet_sales_sql` / `fetch` en `ventas_mensuales_licenciatarios_query.py` debe aceptar `sucursales` y `punto_venta` y agregar:
   - `cc.CodSucursal IN (...)`
   - `cc.id_pv IN (...)`
3. El merge seed+ANET: **no** filtrar filas seed por PV/sucursal (no hay dato). Meta del resultado: `filtros_aplicados_solo_tramo_anet: true`.
4. Export Excel: mismos filtros en la consulta ANET; nota en hoja QA.
5. Actualizar spec `SPEC_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md` (hoy dice alcance global). Tests en `test_ventas_mensuales_licenciatarios.py`.

#### 2.B Clientes sin ventas por vendedor

1. UI: en `dashboard_clientes_sin_ventas_vendedor.html`, reutilizar el include de sucursal/PV (o los mismos tags) junto al período y vendedor.
2. JS del informe: enviar `sucursales` y `punto_venta` al API relay.
3. SQL: un cliente «tiene ventas» en el período si existe `cuentacliente` no anulado (misma familia FA/NC que hoy) **con** esos filtros. Sin ventas = no hay comprobante que cumpla período **y** sucursal/PV.
4. Tests en el módulo de `clientes_sin_ventas` (hoy no hay columnas de sucursal/PV).

### Oleada 3 — Relay Ventas Netas (paridad dashboard ↔ relay)

El dashboard `ventas-netas` ya filtra bien vía `query_runner._run_ventas_netas`. El relay `reports/services/ventas_netas.py` (usado por mayoristapp / API gerencia) solo tiene `punto_venta_id: Optional[int]`.

1. Ampliar whitelist `_append_filtros_cuentacliente` (o parámetros explícitos) con:
   - `sucursales` → `cc.CodSucursal IN`
   - `punto_venta` (lista) → `cc.id_pv IN`
2. Deprecar el escalar `punto_venta_id` (seguir aceptándolo: si viene, se trata como lista de un elemento).
3. Tests `test_ventas_netas_relay.py`.

### Oleada 4 — Paneles gerenciales

#### 4.A Resumen ejecutivo

1. Añadir tags `punto_venta` junto a `exec_sucursales` en `executive_summary.html`.
2. Querystring: `sucursales` (ya) + `punto_venta` repetible.
3. `executive_sales_summary.py`: cláusula `cc.id_pv IN (...)` en KPIs, series y margen, **después** del alcance de sucursales clasificadas.
4. Tests del API ejecutivo.

#### 4.B Command Center

1. Reemplazar `#cc-sucursal` simple por tags sucursal (multi) + tags PV, mismos ids canónicos si el JS de CC puede convivir; si no, mapear `cc-sucursal` → `sucursales` en el payload.
2. `executive_dashboard/base.py`: `cod_sucursal: int | None` hoy es **un** id. Extender a `sucursales: list[int] | None` y `puntos_venta: list[int] | None` sin romper query `?sucursal=` (compat).
3. `ventas_metrics.py` ya tiene `id_pv IN` / `CodSucursal IN` en varios helpers: cablear desde filtros.
4. Deep-link a VMM/VO: pasar `sucursales` y `punto_venta` en la query (hoy solo `sucursal` singular).

#### 4.C Cascada PV ← sucursal (opcional, todos los includes)

API filters: `GET /api/reports/filters/?type=puntos_venta&sucursales=1,2` filtra por `punto_venta.id_sucursal`. El JS recarga PVs al cambiar sucursales, conservando PVs aún válidos.

---

## 5. Qué no tocar

- **`bo-stock-facturacion`** (template, JS, `_run_backorder_vs_stock_vs_facturacion`).
- **`pedidos-pendientes`** y **`remitos-no-facturados`** / `uninvoiced_remitos` (`dashboard_detail.html`, `collectFilters`, `loadFilterOptions` de esos slugs).
- Inventario / stock / MPR / caja / cobranzas (salvo payload del Command Center).
- `documento-presupuesto-ventas` y `evolucion-precios`.
- Crear un include nuevo: hay dos canónicos; duplicar markup está prohibido por la fuente de verdad UI.
- Diálogos nativos; tags existentes.
- Concatenar IDs en SQL: siempre placeholders `%s` + `to_int_or_none`.

---

## 6. Tests (mínimo por oleada)

| Oleada | Cobertura |
|--------|-----------|
| 1 | Template: VO/VPV/VPA/VMSA/BOM muestran `punto_venta`; `bo-stock-facturacion` no. Runner: `punto_venta=[Y]` recorta SQL en esos slugs; `[]` = total. |
| 2.A | Query ANET con filtros; seed no filtrado; meta `filtros_aplicados_solo_tramo_anet`. |
| 2.B | Cliente con venta en otra sucursal **sí** aparece como «sin ventas» si se filtra la sucursal vacía. |
| 3 | Relay lista PV + sucursales; escalar `punto_venta_id` sigue andando. |
| 4 | Ejecutivo: PV recorta KPIs dentro de clasificadas. CC: payload multi + deep-link. |

Comando: `docker exec Synap_app python manage.py test reports.tests.<modulo>`.

Verificación UI (cuando haya browser): en cada slug de oleada, elegir una sucursal, generar, elegir un PV, generar, limpiar, generar. Comprobar que export Excel usa el mismo recorte.

---

## 7. Documentación a actualizar (al implementar)

- Este plan: marcar oleadas hechas.
- Specs: VML, clientes sin ventas, dashboard ejecutivo, Command Center.
- `docs/reports/MANUAL_USUARIO_REPORTES.md` (filtros sucursal/PV).
- Specs VO / VPV / VPA / VMM: ya mencionan sucursal/PV; no hace falta salvo cascada.

---

## 8. Criterios de aceptación

### 8.1 Oleada 1 — Whitelist PV en familia BO (completada)

**Estado:** implementado en PR 1 (Oleada 1).

| Elemento | Implementación |
|----------|----------------|
| Fuente de verdad Python | `SLUGS_VENTAS_CON_PUNTO_VENTA` en `reports/views.py` |
| Contexto template | `mostrar_filtro_punto_venta` en `DashboardDetailView.get_context_data` |
| Include BO | `filters_bo_punto_venta_sucursales_depositos_clientes.html` usa `{% if mostrar_filtro_punto_venta %}` |
| Gate JS | `SLUGS_VENTAS_PV` + `loadPuntoVentaOptions` en `dashboard.js` |
| Slugs con PV visible | VO, VPV, VPA, VMSA, BOM, VMM |
| Excluido | `bo-stock-facturacion` (por omisión en frozenset) |
| Tests | `reports/tests/test_filtros_pv_sucursal_ventas.py::TestOleada1Whitelist` |

### 8.2.A Oleada 2.A — Licenciatarios (completada)

**Estado:** implementado en PR 2 (Oleada 2.A).

| Elemento | Implementación |
|----------|----------------|
| UI | `filters_sucursal_punto_venta.html` en `dashboard_detail.html` con `ocultar_clientes_excluidos=True` (evita duplicar `id="clientes_excluidos"`) |
| SQL ANET | `build_anet_sales_sql` / `fetch_anet_sales` con `cc.CodSucursal IN` y `cc.id_pv IN` |
| Merge | `merge_pack_year` propaga filtros solo a `fetch_anet_fn`; seed sin filtrar |
| Runner | `run_ventas_mensuales_licenciatarios` parsea `filters.sucursales` / `filters.punto_venta`; meta `filtros_aplicados_solo_tramo_anet: true` |
| JS | `loadPuntoVentaOptions` + `getFilters` para slug `ventas-mensuales-licenciatarios` |
| Tests | `test_ventas_mensuales_licenciatarios.py` (clases Oleada2 + QueryTests) |

### 8.2.B Oleada 2.B — Clientes sin ventas (completada)

**Estado:** implementado en PR 2 (Oleada 2.B).

| Elemento | Implementación |
|----------|----------------|
| UI | Include sucursal/PV en `dashboard_clientes_sin_ventas_vendedor.html` (sin bloque clientes excluidos) |
| Relay | Query params `sucursales` / `puntoVenta` (CSV o repetibles) → servicio |
| SQL | Filtros en `ON` de `LEFT JOIN cc_periodo`; mismo recorte en `UltimaCompra` y `_resumen_por_vendedor` |
| Tests | `test_clientes_sin_ventas_relay.py` |

### 8.3 Oleada 3 — Relay ventas-netas (completada)

**Estado:** implementado en PR 3 (Oleada 3).

| Elemento | Implementación |
|----------|----------------|
| Servicio | `get_ventas_netas(..., sucursales=None, punto_venta=None)` con cláusulas `cc.CodSucursal IN` y `cc.id_pv IN` |
| Compat escalar | `punto_venta_id` (deprecado) se une a `punto_venta` en una sola cláusula `IN` sin duplicar |
| Relay gerencia | Query params `sucursales` / `puntoVenta` / `punto_venta` (CSV o repetibles) → servicio |
| Relay vendedor | Mismos params de lista en GET operativo |
| Whitelist | **No** se agregó `sucursales` a `_append_filtros_cuentacliente` (semántica distinta de `filtrarPor`) |
| Tests | `test_ventas_netas_relay.py` (`TestVentasNetasFiltrosSucursalPv`, `test_relay_acepta_listas_sucursales_pv`) |

### 8.4 Oleada 4 — Paneles gerenciales (completada PR 4)

#### 8.4.A Resumen ejecutivo (ventas)

| Elemento | Implementación |
|----------|----------------|
| SQL | `_cc_scope_sql(scope, puntos_venta)` inyecta `cc.id_pv IN` además de `CodSucursal` |
| Servicio | `run_executive_summary(..., puntos_venta_filtro=)` → meta `punto_venta_filtrados` |
| API | `_parse_puntos_venta_filtro` + query `punto_venta` repetible |
| UI | Tags `exec_punto_venta` junto a `exec_sucursales`; JS carga `/api/reports/filters/?type=puntos_venta` |
| Tests | `test_executive_summary_contract.py::ExecutiveSummaryPuntoVentaTests` |

#### 8.4.B Command Center gerencial

| Elemento | Implementación |
|----------|----------------|
| Filtros | `DashboardFilters.sucursales_filtro` / `puntos_venta` (tuplas); `cod_sucursal` propiedad derivada |
| Meta | `cod_sucursal_filtro` (lista o null), `punto_venta_filtros` (lista o null) |
| Query | `sucursales` + `punto_venta` repetibles; compat `?sucursal=` |
| Ventas | `ventas_metrics.fetch_ventas_resumen` cablea PV en netas/remitos/pedidos |
| UI | Tags `sucursales` + `punto_venta` (reemplaza `#cc-sucursal`); deep-links VMM/VO con ambos filtros |
| Tests | `test_executive_dashboard_contract.py::CommandCenterMultiSelectTests` |

#### 8.4.C Cascada sucursal→PV

**Estado:** **N/A / diferida** — decisión de producto 31/08/2026: la cascada sucursal→PV en UI no es requisito para v1. No se modificaron `reports/api_views.py` ni el reload de PV en `dashboard.js`. Follow-up opcional si producto la exige.

---

Para cada informe **en alcance** (tabla §2 menos excepciones §3):

1. En pantalla hay filtro sucursal y filtro PV (tags, vacío = todas).
2. El dataset (pantalla + Excel) se recorta con AND sobre `CodSucursal` / `id_pv` de la tabla de movimiento del informe.
3. Filtrar solo sucursal o solo PV funciona.
4. Sin selección, el total coincide con el comportamiento actual (regresión).
5. IDs se normalizan a `int`; no se envían strings vacíos a DATE ni a IN.

---

## 9. Orden sugerido de merge

1. Oleada 1 (un PR chico, bajo riesgo).
2. Oleada 2.B clientes sin ventas + Oleada 3 relay (independientes, pueden ir en paralelo).
3. Oleada 2.A licenciatarios (cuidado con seed vs ANET y export a marcas).
4. Oleada 4 gerencial + cascada.

Estimación relativa: 1 ≪ 2.B ≈ 3 < 2.A < 4.
