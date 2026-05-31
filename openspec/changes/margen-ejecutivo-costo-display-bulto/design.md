# Design: Margen ejecutivo — paridad informe rentabilidad AdministraNET

**Cambio:** `margen-ejecutivo-costo-display-bulto`  
**Decisión final (may. 2026):** alinear costo del panel con el informe Crystal de rentabilidad VB6, no con normalización analítica Display/Bulto.

## Contexto

Análisis VB6 (`Info_Venta.frm` → `View_Venta_Rentabilidad_*` → Crystal `ventas_vista_rentabilidad_*.rpt`):

1. Se recrea la vista MySQL `venta_rentabilidad_resumen` con fechas embebidas.
2. `total_costo = SUM(PrecioCostoxR)` con signo según `stock.TipoComp`.
3. **No hay** reproceso intermedio ni escala por `tipo_unidad`, `cantidad_dividir` ni `multiplicador_comp`.
4. `Calculo_Costo_Display_Bulto` no tiene call sites en facturación.

Un intento intermedio en Synap (escala empaque) desalineaba el panel respecto al informe legacy y producía márgenes espurios en empresas con embalaje (ej. angelita, 14/02/2026).

## Technical Approach

**Costo agregado del panel = suma firmada de `stock.PrecioCostoxR`**, con el mismo `CASE` FA/NC que `PrecioNetoxR` en el resumen ejecutivo (convención ya usada para venta neta de líneas).

**Sin cambios:** venta (`PrecioNetoxR`), KPI `ventas_netas_dia`, universo de joins/filtros, Top 10, rubro/subrubro.

## Architecture Decisions

| Decisión | Elección | Alternativa rechazada | Rationale |
|----------|----------|----------------------|-----------|
| Fórmula costo | `PrecioCostoxR` persistido | `PrecioCostoxU × Cantidad / divisor` | Paridad `venta_rentabilidad_resumen` y Crystal |
| Signo | FA/NC vía `cuentacliente.TipoComprobante` | Signo por `stock.TipoComp` | Coherencia con venta neta del mismo panel |
| Config embalaje | No consultar `configuracion` para margen | Condicionar por `utiliza_embalaje` | Informe legacy no discrimina por config |
| Meta | `margen_costo_criterio` = `precio_costoxr_linea` | `costo_empaque_escala_*` | Trazabilidad explícita |
| Alcance | Solo panel ejecutivo | `query_runner` global | Mismo alcance v1; otros informes siguen su criterio |

## Data Flow

```
run_executive_summary
  └─ _margen_bruto_totales_dia / _margen_por_rubro_dia / _margen_por_subrubro_dia
        └─ SUM( signed_costo_neto_linea_sql() )  → COALESCE(PrecioCostoxR,0) × signo FA/NC
        └─ SUM( _signed_precio_netoxr_sql() )    → sin cambio
```

## File Changes

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `reports/services/margen_costo_linea.py` | Simplificar | `PrecioCostoxR` + signo FA/NC |
| `reports/services/executive_sales_summary.py` | Modificar | Quitar lectura config embalaje |
| `reports/tests/test_margen_costo_linea.py` | Actualizar | Paridad `PrecioCostoxR` |
| `reports/tests/test_executive_summary_contract.py` | Actualizar | Meta `precio_costoxr_linea` |
| `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` | Modificar | Criterio costo documentado |

## Testing Strategy

| Capa | Qué | Cómo |
|------|-----|------|
| Unit | `costo_linea_precio_costoxr_python` | Devuelve `PrecioCostoxR` sin transformar |
| Contract | `run_executive_summary` | `meta.margen_costo_criterio` = `precio_costoxr_linea` |
| SQL manual | Piloto angelita | `SUM(PrecioCostoxR)` firmado vs panel |

## Validación angelita (14/02/2026)

Con paridad `PrecioCostoxR`, costo agregado ≈ $216 M vs venta neta ≈ $123 M (margen coherente con informe legacy). La escala Display/Bulto había colapsado costo a ~$1,4 M (−1056% margen).

## Migration / Rollout

Sin migración MySQL. Despliegue = cambio código. Comparar panel vs informe Crystal rentabilidad por cliente/vendedor en rango piloto.
