# Proposal: Descuento al pie en facturación VMM

## Intent

El informe **Ventas marcas mensual** (`ventas-marcas-mensual`) calcula facturación y regalías con `SUM(signo × stock.PrecioNetoxR)`, neto de renglón **sin** el descuento al pie de factura. En AdministraNET el dto al pie vive en cabecera (`cuentacliente.PorDesc1`/`ImpDesc1` → `SubtotalDesc`); las líneas en `stock` quedan pre-pie. La base imponible correcta para facturación/regalías es el neto **post-pie** (`SubtotalDesc` repartido proporcionalmente por línea). Producto cerró el bug: alinear VMM con AdministraNET y con el patrón ya validado en DABRA.

## Scope

### In Scope
- Factor dto pie en expresión SQL de importe: `ventas_marcas_mensual_rules.py`, `ventas_marcas_mensual_runner.py`, `ventas_marcas_mensual_export.py` (Matriz, Detalle, comparar)
- KPIs derivados (facturación, precio medio, regalías, regalías/TC), proyección `$` sobre facturación post-pie
- Extraer helper compartido desde DABRA (`factor_descuento_cabecera`) sin cambiar comportamiento DABRA
- Tests unitarios del factor + escenario integrado FA con `PorDesc1`
- Actualizar `docs/reports/SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md`, nota en `MAPEO_PUW_PUM_ADMINISTRANET.md`, una frase en `MANUAL_USUARIO_REPORTES.md`

### Out of Scope
- Export completo VML (Monthly Reporting)
- Cambiar otros informes salvo import del helper extraído
- UI nueva de filtros

## Capabilities

### New Capabilities
- `reports-ventas-marcas-mensual`: informe pivot mensual — requisitos de facturación post-pie, KPIs/regalías y export Matriz/Detalle (no existe spec OpenSpec previa; docs en `docs/reports/`)

### Modified Capabilities
- Ninguna (sin spec OpenSpec existente para VMM)

## Approach

1. **Helper compartido:** mover `factor_descuento_cabecera(subtotal1, subtotal_desc)` a `reports/services/comprobante_descuento_cabecera.py`; re-exportar desde `dabra_consolidado_remitos.py` (import) para no romper tests DABRA.
2. **SQL:** nueva `sql_signo_imp_post_pie_expr()` en `ventas_marcas_mensual_rules.py`:
   - `signo × PrecioNetoxR × factor`, con `factor = SubtotalDesc/SubTotal1` si `SubTotal1 ≠ 0`, si no `1`; `SubtotalDesc` nulo → `SubTotal1`.
3. **Runner/export:** sustituir `sql_signo_imp_expr()` por la variante post-pie en agregados matriz y detalle; unidades sin cambio.
4. **KPIs/regalías:** sin lógica nueva — recalculan sobre `facturacion` ya corregida (`regalías = facturación × tasa`).
5. **Tests:** casos helper (0%, 20%, `SubTotal1=0`, null); runner mock/SQL fixture FA pie 20% → Σ líneas × 0,8; regresión sin pie → factor 1.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `reports/services/comprobante_descuento_cabecera.py` | New | Helper Python + expr SQL reutilizable |
| `reports/services/ventas_marcas_mensual_rules.py` | Modified | Expr importe post-pie |
| `reports/services/ventas_marcas_mensual_runner.py` | Modified | Matriz, KPIs, comparar |
| `reports/services/ventas_marcas_mensual_export.py` | Modified | Detalle Excel |
| `reports/services/dabra_consolidado_remitos.py` | Modified | Import helper (sin cambio funcional) |
| `reports/tests/test_ventas_marcas_mensual.py` | Modified | Escenarios dto pie |
| `docs/reports/SPEC_INFORME_VENTAS_MARCAS_MENSUAL.md` | Modified | § KPIs / motor importe |
| `docs/reports/MANUAL_USUARIO_REPORTES.md` | Modified | Frase: facturación incluye dto al pie |
| `docs/reports/MAPEO_PUW_PUM_ADMINISTRANET.md` | Modified | Nota factor cabecera |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Filtro parcial de líneas (marca) vs factor cabecera | Med | Factor por `CodigoMovimiento` (todas las líneas FA); documentar paridad AdministraNET |
| Redondeo Σ líneas × factor ≠ `SubtotalDesc` | Low | Mismo criterio DABRA; tests tolerancia razonable |
| Regresión DABRA al mover helper | Low | Mantener tests `test_dabra_consolidado_remitos.py` verdes |

## Rollback Plan

Revertir el merge/commit del change. Sin migraciones DB. Comportamiento anterior (`PrecioNetoxR` sin factor) queda restaurado al deshacer cambios en rules/runner/export.

## Dependencies

- Patrón validado: `reports/services/dabra_consolidado_remitos.py` (`factor_descuento_cabecera`)
- Tipos: `core.utils.administranet_types` (`to_decimal_or_none`)
- Tests: `docker exec Synap_app python manage.py test reports.tests.test_ventas_marcas_mensual reports.tests.test_dabra_consolidado_remitos`

## Success Criteria

- [ ] FA con dto pie 20%: Σ líneas filtradas × 0,8 = facturación del informe
- [ ] Sin dto pie: factor 1 (paridad con comportamiento actual)
- [ ] Regalías = facturación_post_pie × tasa; regalías/TC coherente
- [ ] Export Matriz/Detalle y modo comparar usan la misma base
- [ ] Tests verdes en contenedor Synap
