# Design: filtros Punto de venta y Sucursal en informes de ventas

Propuesta: `openspec/changes/filtros-pv-sucursal-ventas/proposal.md` · Plan: `docs/reports/PLAN_FILTROS_PV_SUCURSAL_VENTAS.md`.

## Technical Approach

Contrato único: `filters.sucursales` y `filters.punto_venta` como `list[int]`; vacío = todas; ambos presentes = AND. No se crea ningún componente nuevo: se amplían los *seams* que ya existen (`QueryRunnerService._parse_sucursales_pv`, `_cc_scope_sql`, `ventas_metrics`, los dos includes canónicos y `GET /api/reports/filters/`). Cuatro oleadas = cuatro PRs independientes.

## Architecture Decisions

| # | Decisión (elegido) | Alternativa descartada | Motivo |
|---|--------------------|------------------------|--------|
| D1 | Whitelist de slugs con PV en **Python**: `SLUGS_VENTAS_CON_PUNTO_VENTA: frozenset` en `reports/views.py` (patrón `BUILDER_HYBRID_SLUGS`, línea 26) → flag de contexto `mostrar_filtro_punto_venta` en `DashboardDetailView.get_context_data`; el include BO usa `{% if mostrar_filtro_punto_venta %}` | Cadena `{% if slug == ... or ... %}` en el template; include nuevo | Una sola fuente de verdad, testeable sin renderizar. `bo-stock-facturacion` queda excluido por omisión, no por negación. Include nuevo está prohibido por la fuente de verdad UI |
| D2 | Gatear **solo** el include BO. `filters_sucursal_punto_venta.html` sigue mostrando PV sin condición | Gatear los dos includes | Sus tres consumidores (`ventas-netas`, `uninvoiced_remitos`, `total-consolidado-operativo`) ya muestran PV y `bo-stock-facturacion` no usa ese include: gatearlo solo agrega riesgo de regresión |
| D3 | `dashboard.js`: `loadPuntoVentaOptions = !isBoReport \|\| isVentasMarcasMensualSlug(slug) \|\| SLUGS_VENTAS_PV.has(slug)`, con `SLUGS_VENTAS_PV` **sin** `bo-stock-facturacion` | Quitar el gate `isBoReport` | El gate existe justamente para BO vs stock (ADR ~línea 6685). No se toca el borrado de filtros de `pedidos-pendientes` (líneas 5959 y 5977) ni ningún `collectFilters` de pedidos/remitos |
| D4 | Reusar `filters_sucursal_punto_venta.html` con flag `{% if not ocultar_clientes_excluidos %}` sobre su bloque «Clientes a excluir» | Include nuevo sin ese bloque | El include arrastra `id="clientes_excluidos"`, id que **ya existe** en `filters_ventas_mensuales_licenciatarios.html` (línea 73): duplicarlo rompe `initializeTagsFilter`. El flag ausente = comportamiento actual |
| D5 | Licenciatarios: filtrar **solo** el tramo ANET dentro de `build_anet_sales_sql` (`cc.CodSucursal` / `cc.id_pv`), pasando las listas por `merge_pack_year(...)` → `fetch_anet_fn`. Seed sin filtrar. Meta `filtros_aplicados_solo_tramo_anet: True` cuando hay selección | Filtrar también el seed; o rechazar el filtro | El seed pre-cutover (22/07/2026) no tiene columnas de sucursal/PV: filtrarlo inventaría datos. La meta hace explícito el recorte parcial en pantalla y en la hoja QA |
| D6 | `clientes-sin-ventas`: los filtros se agregan al **`ON`** del `LEFT JOIN cuentacliente AS cc_periodo`, nunca al `WHERE` | Agregarlos al `WHERE` | El informe es un anti-join (`WHERE cc_periodo.Codigo IS NULL`): en el `WHERE` el filtro anularía el anti-join y devolvería 0 filas |
| D7 | Relay `ventas_netas`: parámetros explícitos `sucursales` y `punto_venta` (listas). El escalar `punto_venta_id` se normaliza a `[id]` y se une a `punto_venta` | Agregar `sucursales` a la whitelist `_append_filtros_cuentacliente` | Esa whitelist traduce `filtrarPor` (cliente/vendedor), semántica distinta. Parámetros explícitos conservan la compat del escalar sin ambigüedad |
| D8 | Ejecutivo: extender `_cc_scope_sql(scope_sucursales, puntos_venta)` | Añadir PV helper por helper | `_cc_scope_sql` es el único inyector de alcance y ya lo consumen KPIs, series horaria/7 días, margen por rubro/subrubro y top productos: un cambio, cobertura completa |
| D9 | Command Center: `DashboardFilters` suma `sucursales_filtro` y `puntos_venta` (tuplas); `cod_sucursal` pasa a **propiedad derivada** (`sucursales_filtro[0]` si hay exactamente una) | Reemplazar `cod_sucursal` | `build_meta` publica `cod_sucursal_filtro` en el contrato `executive-dashboard-v1`; derivarlo mantiene el contrato y el deep-link `?sucursal=` |
| D10 | Cascada (opcional): `GET /api/reports/filters/?type=puntos_venta&sucursales=1,2` filtra por `punto_venta.id_sucursal`; el recargado del `<select>` vive en `dashboard.js` | Cambiar la firma de `tags_filter.mjs` | `initializeTagsFilter` es genérico y compartido con presupuesto/MPR: la lógica de dominio no entra ahí |

## Data Flow

```
UI tags (sucursales / punto_venta)
   │  filters JSON (list[int]; vacío = todas)
   ├─ dashboard.js collectFilters ──→ POST /api/reports/.../query/ ──→ runner
   │                                     └─ _parse_sucursales_pv() → AND cc.CodSucursal IN (%s) / cc.id_pv IN (%s)
   ├─ executive_summary.js ─── GET ?sucursales=&punto_venta= ──→ _cc_scope_sql() → KPIs · series · margen
   ├─ command_center.js ────── GET ?sucursales=&puntos_venta= (compat ?sucursal=) ──→ DashboardFilters → ventas_metrics
   └─ relay GET ventas-netas / clientes-sin-ventas ──→ servicio → mismo SQL con placeholders
                                                          │
GET /api/reports/filters/?type=puntos_venta[&sucursales=] ─┘  (opciones + cascada)
```

## File Changes

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `reports/views.py` | Modify | `SLUGS_VENTAS_CON_PUNTO_VENTA` (frozenset, sin `bo-stock-facturacion`) + `mostrar_filtro_punto_venta` en el contexto de `DashboardDetailView` (línea 219) |
| `reports/templates/reports/includes/filters_bo_punto_venta_sucursales_depositos_clientes.html` | Modify | O1: el `{% if report.slug == 'ventas-marcas-mensual' %}` del bloque PV pasa a `{% if mostrar_filtro_punto_venta %}`; hint «Vacío = todos los puntos de venta» |
| `reports/templates/reports/includes/filters_sucursal_punto_venta.html` | Modify | O2: envolver el bloque «Clientes a excluir» en `{% if not ocultar_clientes_excluidos %}` |
| `reports/templates/reports/dashboard_detail.html` | Modify | O2: incluir el include simple con `with ocultar_clientes_excluidos=True` para `ventas-mensuales-licenciatarios` (tras el bloque pack/período, línea ~393) |
| `reports/templates/reports/dashboard_clientes_sin_ventas_vendedor.html` | Modify | O2.B: tags sucursal/PV junto a período y vendedor; envío al relay |
| `reports/static/reports/js/dashboard.js` | Modify | O1: `SLUGS_VENTAS_PV` + gate de `loadPuntoVentaOptions` (línea 6685). O2.A: incluir el slug de licenciatarios en el gate y en `collectFilters`. O4.C (opcional): recargar PV al `change` de `sucursales` |
| `reports/services/ventas_mensuales_licenciatarios_query.py` | Modify | `build_anet_sales_sql(..., sucursales, puntos_venta)` y `fetch_anet_sales(...)` con placeholders `%s` |
| `reports/services/ventas_mensuales_licenciatarios_merger.py` | Modify | `merge_pack_year(..., sucursales, puntos_venta)` → `fetch_anet_fn` (solo tramo ANET) |
| `reports/services/ventas_mensuales_licenciatarios_runner.py` | Modify | Parseo de filtros, `meta["filters_applied"]` y `filtros_aplicados_solo_tramo_anet` |
| `reports/services/clientes_sin_ventas.py` | Modify | `get_clientes_sin_ventas(..., sucursales, puntos_venta)`: filtros en el `ON` de `cc_periodo`, en la subconsulta `UltimaCompra` y en `_resumen_por_vendedor` |
| `reports/clientes_sin_ventas_relay_views.py` | Modify | Query params `sucursales` / `puntoVenta` (repetibles o CSV) → servicio; sin cambio de permisos |
| `reports/services/ventas_netas.py` | Modify | `get_ventas_netas(..., sucursales=None, punto_venta=None)`; `punto_venta_id` → `[id]` (deprecado, aceptado) |
| `reports/services/executive_sales_summary.py` | Modify | `_cc_scope_sql(scope, puntos_venta)`; `run_executive_summary(..., puntos_venta_filtro)`; meta `puntos_venta_filtro` |
| `reports/executive_summary_api_views.py` | Modify | `_parse_puntos_venta_filtro(qp)` (espejo de `_parse_sucursales_filtro`, línea 76) |
| `reports/templates/reports/executive_summary.html` | Modify | Tags `punto_venta` junto a `exec_sucursales` (línea 133) |
| `reports/static/reports/js/executive_summary.js` | Modify | Carga de opciones PV y `qs.append("punto_venta", id)` (línea 1099) |
| `reports/services/executive_dashboard/base.py` | Modify | `DashboardFilters.sucursales_filtro` / `.puntos_venta`; `cod_sucursal` derivado; `resolve_filters_from_query_params` con compat `?sucursal=` |
| `reports/services/executive_dashboard/ventas_metrics.py` | Modify | Cablear `filters.puntos_venta` en los helpers que ya aceptan `puntos_venta` (líneas 27, 71, 111) y en las cláusulas `filters.sucursales` (líneas 158, 174) |
| `reports/templates/reports/command_center.html` | Modify | `#cc-sucursal` (select simple) → tags `sucursales` + tags `punto_venta` |
| `reports/static/reports/js/command_center.js` | Modify | `readFilters` multi, persistencia, querystring y deep-links a VMM/VO con `sucursales` + `punto_venta` |
| `reports/api_views.py` | Modify | O4.C (opcional): `?sucursales=` en `type=puntos_venta` (`punto_venta.id_sucursal IN`) |
| `reports/tests/test_filtros_pv_sucursal_ventas.py` | Create | Tests de template/whitelist y de contrato del payload por slug |
| `reports/tests/test_ventas_mensuales_licenciatarios.py`, `test_clientes_sin_ventas_relay.py`, `test_ventas_netas_relay.py`, `test_executive_summary_contract.py`, `test_executive_dashboard_contract.py` | Modify | Casos por oleada |
| `docs/reports/PLAN_FILTROS_PV_SUCURSAL_VENTAS.md`, `docs/reports/MANUAL_USUARIO_REPORTES.md`, specs VML / clientes sin ventas / ejecutivo / Command Center | Modify | Documentación obligatoria (`.cursorrules`) |

## Interfaces / Contracts

```python
# reports/services/executive_dashboard/base.py
@dataclass(frozen=True)
class DashboardFilters:
    sucursales_filtro: tuple[int, ...] = ()   # vacío = todas
    puntos_venta: tuple[int, ...] = ()        # vacío = todos

    @property
    def cod_sucursal(self) -> int | None:     # compat contrato executive-dashboard-v1
        return self.sucursales_filtro[0] if len(self.sucursales_filtro) == 1 else None

    @property
    def sucursales(self) -> list[int] | None:
        return list(self.sucursales_filtro) or None
```

Semántica de «tiene ventas» (`clientes-sin-ventas`): un cliente **tiene ventas** si existe `cuentacliente` no anulado, `TipoComprobante NOT IN ('NCA','NCB')`, en el período **y** en las sucursales/PV seleccionados. Corolario aceptado: un cliente que facturó solo en otra sucursal aparece como «sin ventas» al filtrar. `UltimaCompra` respeta el mismo recorte para que la columna no contradiga la fila.

## Testing Strategy

| Capa | Qué se prueba | Cómo |
|------|---------------|------|
| Template | VO/VPV/VPA/VMSA/BOM/VMM renderizan `id="punto_venta"`; `bo-stock-facturacion` **no**; licenciatarios no duplica `id="clientes_excluidos"` | `Client().get()` sobre `/reports/dashboard/<slug>/` + `assertContains` / `assertNotContains` |
| Unit SQL | `sucursales=[]` y `punto_venta=[]` → SQL sin cláusula (paridad con hoy); listas → `IN (%s,...)` con params `int`; seed de licenciatarios sin filtrar | Inspección del SQL/params con cursor falso, patrón de `test_ventas_marcas_mensual.py` |
| Unit servicio | Relay: `punto_venta_id=3` ≡ `punto_venta=[3]`; unión sin duplicar cláusula | `test_ventas_netas_relay.py` |
| Integración | Anti-join de `clientes-sin-ventas`: cliente con venta en otra sucursal aparece como «sin ventas» al filtrar; PV recorta KPIs del ejecutivo dentro de clasificadas; CC acepta `?sucursal=` y `?sucursales=` | Relay/API con doble de cursor |
| Regresión | Sin selección, totales idénticos por slug; `pedidos-pendientes` y `remitos-no-facturados` sin cambios de payload | Snapshot de `filters` enviados |

Comando: `docker exec Synap_app python manage.py test reports.tests.<modulo>`.

## Threat Matrix

N/A — el cambio no toca routing/shell, subprocesos, automatización VCS/PR, clasificación de archivos ejecutables ni integración de procesos. Riesgo de seguridad relevante y ya cubierto por el contrato: **SQL injection** — todos los IN usan placeholders `%s` con IDs normalizados a `int` (`core.utils.administranet_types`); prohibido concatenar. AdministraNET: solo `SELECT`. Los relays no relajan `OperationalReportsPermission` / `ManagerialReportsPermission` ni el anti-bypass de vendedor.

## Migration / Rollout

Sin migraciones de datos ni de esquema. Cuatro PRs en el orden del plan §9 (O1 → O2.B + O3 → O2.A → O4). Cada PR es revertible con `git revert`: la UI vuelve a ocultar PV y el backend deja de aplicar las listas recibidas.

## Open Questions

- [ ] `clientes-sin-ventas`: ¿`UltimaCompra` debe respetar el filtro (elegido) o quedar global? Confirmar con producto antes de O2.B.
- [ ] Command Center: ¿los deep-links a VMM/VO deben propagar PV además de sucursal desde el primer PR o en un follow-up?
- [ ] O4.C (cascada) queda como opcional; si producto la exige, deja de ser no bloqueante.
