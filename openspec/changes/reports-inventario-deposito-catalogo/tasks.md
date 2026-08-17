# Tasks: reports-inventario-deposito-catalogo

## 1. Spec / seed / runner

- [x] Spec OpenSpec del capability
- [x] `inventario_deposito_seed.py` + migración + `ensure_*`
- [x] `inventario_deposito_runner.py` + dispatch `query_runner`
- [x] Export xlsx en `export_service`
- [x] Slug en `_LEGACY_LISTADOS_SLUGS`

## 2. UI catálogo

- [x] `dashboard_inventario_deposito.html` + `filters_inventario_deposito.html`
- [x] JS query/export + KPIs + tabla jerárquica
- [x] `get_template_names` + ensure en `DashboardDetailView`

## 3. Menú / redirect / permisos

- [x] Helper permiso OR (`mpr.reportes` / `mpr.ver`)
- [x] Query/Export API respetan OR solo para este slug
- [x] Menú Reports + deep-link MPR
- [x] Redirect 302 desde hub MPR
- [x] Atajo `/reports/inventario-deposito-articulo/`

## 4. Tests / docs

- [x] Tests contrato seed/runner/permisos/redirect
- [x] `docs/reports/INVENTARIO_DEPOSITO_ARTICULO.md` + update `docs/mpr/...`
- [x] Playbook oleadas 2–4 en la misma ficha
