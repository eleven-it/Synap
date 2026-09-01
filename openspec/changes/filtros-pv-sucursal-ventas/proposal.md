# Propuesta: filtros Punto de venta y Sucursal en informes de ventas

Plan: `docs/reports/PLAN_FILTROS_PV_SUCURSAL_VENTAS.md`.

## Intent

Todo informe de ventas de `/reports/` debe acotarse por sucursal, por punto de venta (PV) o por ambos. Hoy varios runners filtran PV pero la UI lo oculta, otros informes no tienen filtro y el relay `ventas_netas.py` sólo acepta un PV escalar; gerencia no puede comparar bocas de venta sin recortar a mano.

## Scope

### In Scope

- **Oleada 1** — PV visible en familia BO (VO, VPV, VPA, VMSA, BOM): sólo UI + gate JS, el SQL ya filtra.
- **Oleada 2.A** — `ventas-mensuales-licenciatarios`: filtrar sólo el tramo AdministraNET post-cutover; seed global, meta `filtros_aplicados_solo_tramo_anet`.
- **Oleada 2.B** — `clientes-sin-ventas-vendedor`: UI + SQL.
- **Oleada 3** — Relay `ventas_netas.py`: listas `sucursales` y `punto_venta`; compat del escalar `punto_venta_id`.
- **Oleada 4** — `resumen-ejecutivo-ventas` y `command-center-gerencial` suman PV; cascada sucursal→PV opcional vía `sucursal_id`.

### Out of Scope (confirmado 31/08/2026)

- `bo-stock-facturacion`: el include BO es compartido y **MUST NOT** mostrar PV allí.
- `pedidos-pendientes`, `remitos-no-facturados`, `uninvoiced_remitos`.
- `documento-presupuesto-ventas`, `evolucion-precios`; tampoco un tercer include.

## Capabilities

### New Capabilities

- `reports-filtros-sucursal-punto-venta`: contrato transversal (payload, AND, columnas MySQL, includes, whitelist de slugs) e informes sin capacidad propia (familia BO, licenciatarios, relay Ventas Netas).

### Modified Capabilities

- `reports-clientes-sin-ventas`: el universo «sin ventas» se recorta por sucursal/PV.
- `reports-ejecutivo-ventas`: PV dentro del alcance de sucursales clasificadas.
- `reports-executive-dashboard`: sucursal multiselección + PV, con compat de `?sucursal=`.

## Approach

`filters.sucursales` y `filters.punto_venta` como `list[int]`; vacío = todas; ambos = AND. SQL con placeholders `%s` sobre `CodSucursal`/`id_pv` de `cuentacliente` o `comp_ped`, normalizado con `_parse_sucursales_pv()` y `core.utils.administranet_types`. UI reutiliza los dos includes canónicos y `GET /api/reports/filters/`.

## Affected Areas (todo Modified)

- `reports/templates/reports/includes/filters_*` (BO y simple): whitelist de slugs de ventas para el bloque PV.
- `reports/static/reports/js/dashboard.js`: `loadFilterOptions` carga PV en slugs de ventas.
- `reports/services/{ventas_mensuales_licenciatarios_query,clientes_sin_ventas,ventas_netas}.py`: filtros en SQL y relay.
- `reports/services/{executive_sales_summary,executive_dashboard/base,ventas_metrics}.py`: PV en KPIs, series y payload gerencial.

## Risks

- PV visible en `bo-stock-facturacion` por el include compartido (media) — test de ausencia de `id="punto_venta"`.
- Regresión de totales sin selección (media) — test por slug: `[]` = total actual.
- Seed de licenciatarios sin PV distorsiona el merge (media) — no filtrar seed.

## Rollback Plan

Cada oleada es un PR independiente revertible con `git revert`. Sin migraciones de datos ni esquema: revertir devuelve la UI sin PV y deja de aplicar los filtros recibidos.

## Success Criteria

- [ ] Cada informe en alcance ofrece tags de sucursal y PV; vacío = todas.
- [ ] Pantalla y export Excel aplican el mismo recorte AND.
- [ ] `bo-stock-facturacion` no muestra PV.
- [ ] Sin selección, los totales coinciden con el comportamiento actual.
