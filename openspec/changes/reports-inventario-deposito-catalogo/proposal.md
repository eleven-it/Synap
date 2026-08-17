# Proposal: Inventario por depósito en catálogo Reportes

## Intent

El informe Inventario por depósito vive hoy en el hub MPR (`/mpr/reportes/?grupo=demanda&reporte=inventario_deposito`) con chrome compartido (Desde/Hasta, tabs de grupo, CTA Tablero) que no gobierna este reporte. Producto pide: **alta en el catálogo** `/reports/dashboard/<slug>/`, UI descolapsada de un solo informe, y **acceso directo desde el menú**.

El motor de negocio ya está en Desarrollo (`consultar_inventario_deposito`, docenas 12/6/4, corte a fecha). Este change **no reescribe SQL**; solo superficie de catálogo, menú, redirect y permisos.

## Scope

### In Scope

- Slug `inventario-deposito-articulo` en `ReportDefinition` (seed + migración + `ensure_*`)
- Runner / export Excel vía API de Reportes, envolviendo servicios MPR existentes
- Plantilla dedicada (sin tabs hub ni Desde/Hasta del shell MPR)
- Menú Reports (excepción por slug) + deep-link MPR
- Redirect 302 desde el hub para bookmarks
- Acceso: `reports.view_operational` **o** `mpr.reportes` / `mpr.ver`
- Docs + tests de contrato

### Out of Scope

- Migrar el resto del hub (oleadas 2–4)
- Cambiar reglas de docenas / UAT Excel BEST
- Fusionar con `stock-existencias`
- Export CSV del hub (Reportes solo xlsx)

## Capabilities

### New Capabilities

- `reports-inventario-deposito-catalogo`: alta catálogo, UI, menú, redirect, permisos OR

### Modified Capabilities

- (ninguna spec archivada; hub MPR solo redirect del slug)

## Approach

1. Seed + runner + dispatch `query_runner` / `export_service`
2. Template `dashboard_inventario_deposito.html` + filtros include + JS query/export
3. Menú + redirect hub + permiso OR en vista y API
4. Tests + docs + playbook oleadas 2–4

## Affected Areas

| Area | Impact |
|------|--------|
| `reports/` | seed, runner, migración, views, export, catalog, UI |
| `core/utils/utils.py` | ítems de menú |
| `mpr/views.py` | redirect inventario_deposito |
| `docs/reports/`, `docs/mpr/` | ficha + update ruta canónica |
