# Proposal: Margen ejecutivo — costo Display/Bulto

**Cambio:** `margen-ejecutivo-costo-display-bulto`

## Intent

El panel ejecutivo suma `PrecioCostoxR`/`PrecioNetoxR` tal cual en `stock`. Al grabar en VB6, `Cantidad` pasa a unidad base (`× cantidad_dividir`) y los importes por renglón no se reescalan. En ventas **Display** el costo del renglón suele quedar en costo unitario × cantidad de displays, mientras la venta refleja el empaque — distorsionando margen bruto y desgloses por rubro/subrubro.

**Objetivo:** alinear el **costo agregado** del dashboard a unidad base según reglas VB6 (`Calculo_Costo_Display_Bulto` + `cantidad_dividir`), sin alterar venta ni KPI de comprobante.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `reports-ejecutivo-ventas`: criterio de costo en margen (REQ-EXEC-MARG-01, REQ-EXEC-MARG-05); escenarios Display/Bulto.

## Approach

**Approach 1:** costo línea agregada = `PrecioCostoxU_efectivo × stock.Cantidad` (cantidad en unidad base), con reglas:
- **Unidad / Display:** factor costo unitario = 1.
- **Bulto:** factor = `multiplicador_comp`.
- **Excepción TPV:** `tipo_unidad=Display` y `precio_unidad=Unidad` → `cantidad_dividir=1` (no inflar costo).
- **Venta:** `SUM(PrecioNetoxR)` sin cambios. Signo FA/NC igual que hoy.

## Affected Areas

| Área | Impacto |
|------|---------|
| `reports/services/executive_sales_summary.py` | Expresión costo en margen |
| `reports/services/margen_costo_linea.py` (nuevo) | Reglas VB6 |
| `reports/tests/test_executive_summary_contract.py` | Fixtures Display/Bulto |
| `openspec/specs/reports-ejecutivo-ventas/spec.md` | Delta REQ-EXEC-MARG |
| `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` | Criterio costo |

## Success Criteria

- Tests verdes con casos Display/Bulto/Unidad/TPV.
- Spec y docs actualizados; `meta` refleja criterio nuevo.
- Sin cambio en `ventas_netas_dia` ni `PrecioNetoxR` agregado.
