# Design: Margen ejecutivo — costo Display/Bulto

**Cambio:** `margen-ejecutivo-costo-display-bulto`  
**Base:** propuesta Engram `sdd/margen-ejecutivo-costo-display-bulto/proposal`, spec delta `reports-ejecutivo-ventas` (REQ-EXEC-MARG-01/05).

## Technical Approach

Reemplazar en `executive_sales_summary.py` la suma cruda de `PrecioCostoxR` por un **costo normalizado por renglón** alineado a VB6: `stock.Cantidad` ya está en **unidad base** (`cantidad_ingresada × cantidad_dividir`), pero `PrecioCostoxR` suele reflejar la **cantidad comercial** (displays/bultos). El agregado correcto es **costo unitario base × Cantidad**, con matriz `tipo_unidad` × `precio_unidad` y fallback a escalado desde `PrecioCostoxR` cuando `PrecioCostoxU` es 0.

**Sin cambios:** venta (`PrecioNetoxR`), KPI `ventas_netas_dia`, universo de joins/filtros, signo FA/NC.

## Architecture Decisions

| Decisión | Elección | Alternativa rechazada | Rationale |
|----------|----------|----------------------|-----------|
| Ubicación reglas | Módulo `reports/services/margen_costo_linea.py` + SQL embebido | Solo inline en `executive_sales_summary` | Reutilizable en tests y futuros agregados; un solo lugar para matriz VB6 |
| Fórmula principal | `PrecioCostoxU × Cantidad` (base) con matriz | `PrecioCostoxR × cantidad_dividir` ciego | Evita doble escala en Bulto; `Cantidad` ya incluye `cantidad_dividir` |
| Excepción Display | `tipo_unidad=Display` + `articulo.precio_unidad='Unidad'` → `PrecioCostoxR` | Siempre escalar | Paridad TPV: `cantidad_dividir=1` y costo ya en base comercial |
| Bulto | Mismo núcleo `PrecioCostoxU × Cantidad`; validar que U = costo artículo base | `× multiplicador_comp` extra en SQL | `Cantidad` ya es unidades base; factor `multiplicador_comp` solo si U fuera por bulto (no es el caso TPV estándar) |
| `precio_unidad` | `LEFT JOIN articulo a`; `COALESCE(NULLIF(TRIM(a.precio_unidad),''),'Unidad')` | Sin join | VB6 lee dato de artículo/lista; si columna ausente en BD, tratar como `'Unidad'` |
| Meta | `margen_costo_criterio`: `costo_unidad_base_cantidad` | Mantener `precio_costoxr_linea` | Trazabilidad del cambio; nota histórica en meta |
| Alcance v1 | Solo panel ejecutivo (`_margen_*`) | `query_runner` global | Propuesta acota riesgo; otros informes siguen crudo hasta decisión OQ#1 |

## Matriz costo por renglón

`Cantidad` = unidades **base** en `stock`. `qty_comercial` = `Cantidad / GREATEST(cantidad_dividir, 1)`.

| tipo_unidad | precio_unidad (artículo) | Costo línea (antes signo FA/NC) | Notas VB6 |
|-------------|--------------------------|-----------------------------------|-----------|
| Unidad / vacío | cualquiera | `COALESCE(PrecioCostoxU,0) × Cantidad`; si U=0 → `PrecioCostoxR` | Paridad con TPV `costo×cant` en base |
| Display | Unidad | `PrecioCostoxR` | `cantidad_dividir=1`; no inflar |
| Display | Display / otro | `PrecioCostoxU × Cantidad`; fallback U=0: `PrecioCostoxR × GREATEST(cantidad_dividir,1)` | Corrige costo×qty display vs base |
| Bulto | cualquiera | `PrecioCostoxU × Cantidad`; fallback U=0: `PrecioCostoxR × GREATEST(cantidad_dividir,1)` | `cantidad_dividir ≈ cantidad_unidad_display × multiplicador_comp` |

**Signo:** envolver con el mismo `CASE` FA/NC que `_signed_precio_costoxr_sql()` (facturas +, NC −).

## Data Flow

```
run_executive_summary
  └─ _margen_bruto_totales_dia / _margen_por_rubro_dia / _margen_por_subrubro_dia
        └─ SUM( _signed_costo_neto_linea_sql() )   ← nuevo
        └─ SUM( _signed_precio_netoxr_sql() )      ← sin cambio
```

## Interfaces / Contracts

### `reports/services/margen_costo_linea.py`

```python
def costo_linea_sin_signo_sql(
    *,
    stock_alias: str = "st",
    articulo_alias: str = "a",
) -> str:
    """Expresión SQL del costo absoluto del renglón (sin signo comprobante)."""

def signed_costo_neto_linea_sql(
    *,
    stock_alias: str = "st",
    articulo_alias: str = "a",
    cc_alias: str = "cc",
) -> str:
    """CASE FA/NC × costo_linea_sin_signo_sql()."""

def costo_linea_normalizado_python(
    *,
    precio_costoxu: float,
    precio_costoxr: float,
    cantidad: float,
    tipo_unidad: str,
    precio_unidad: str,
    cantidad_dividir: float,
) -> float:
    """Espejo Python para tests unitarios (sin MySQL)."""
```

### `executive_sales_summary.py`

- Importar `signed_costo_neto_linea_sql` (alias público `_signed_costo_neto_linea_sql` si se mantiene convención privada del módulo padre).
- Sustituir `costo = _signed_precio_costoxr_sql()` en `_margen_bruto_totales_dia`, `_margen_por_rubro_dia`, `_margen_por_subrubro_dia`.
- En subconsultas rubro/subrubro: asegurar `LEFT JOIN articulo a` (ya existe) para `precio_unidad`.
- `meta.margen_costo_criterio` → `costo_unidad_base_cantidad`.
- Añadir `meta.nota_margen_costo_historico`: totales previos usaban `precio_costoxr_linea` sin normalizar Display.

## File Changes

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `reports/services/margen_costo_linea.py` | Crear | Matriz SQL + helper Python |
| `reports/services/executive_sales_summary.py` | Modificar | Usar nuevo costo en 3 agregados margen |
| `reports/tests/test_margen_costo_linea.py` | Crear | Matriz Unidad/Display/Bulto + excepción precio_unidad |
| `reports/tests/test_executive_summary_contract.py` | Modificar | Assert nuevo `margen_costo_criterio`; mock margen |
| `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` | Modificar | Criterio costo y validación |
| `openspec/changes/.../specs/reports-ejecutivo-ventas/spec.md` | Modificar (spec phase) | REQ-EXEC-MARG-05 valor nuevo |
| `reports/static/reports/js/executive_summary.js` | Modificar | Tooltip si referencia criterio costo |

## Testing Strategy

| Capa | Qué | Cómo |
|------|-----|------|
| Unit | `costo_linea_normalizado_python` | Tabla parametrizada: Display×6, Bulto×mult, Unidad, Display+precio_unidad=Unidad |
| Contract | `run_executive_summary` | Actualizar `margen_costo_criterio`; caso margen con costo normalizado mockeado |
| SQL manual | Piloto empresa | Scripts § Validación |

## SQL validación pre/post

**Pre (detectar distorsión):** renglones día con margen línea negativo espurio.

```sql
SELECT st.id_stock, st.tipo_unidad, st.cantidad_unidad_display, st.cantidad_dividir,
       st.Cantidad, st.PrecioCostoxU, st.PrecioCostoxR, st.PrecioNetoxR,
       (COALESCE(st.PrecioNetoxR,0) - COALESCE(st.PrecioCostoxR,0)) AS margen_crudo,
       (COALESCE(st.PrecioNetoxR,0) - /* pegar costo_linea_sin_signo_sql */) AS margen_norm
FROM stock st
INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
LEFT JOIN articulo a ON a.IDArt = st.IDArt
WHERE cc.Fecha = %s AND st.tipo_unidad = 'Display'
  AND COALESCE(st.cantidad_unidad_display,0) > 1
  AND st.Anulado = 'No' AND st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC');
```

**Post:** comparar `SUM(costo)` panel vs `SUM(costo_linea_sin_signo)` mismo día; delta Bulto/Unidad &lt; umbral piloto; Display mejora margen negativo.

**Regresión día completo:**

```sql
SELECT
  SUM(/* costo crudo firmado */) AS costo_viejo,
  SUM(/* signed_costo_neto_linea_sql */) AS costo_nuevo
FROM stock st ...;
```

## Migration / Rollout

Sin migración MySQL. Despliegue = cambio código. Rollback: revertir helper + restaurar `_signed_precio_costoxr_sql` y `meta.margen_costo_criterio=precio_costoxr_linea`. Piloto recomendado en empresa con alto % Display (OQ#3 flag opcional).

## Open Questions

- [ ] OQ#1: ¿Extender a otros informes con `PrecioCostoxR`?
- [ ] OQ#2: ¿Columna `articulo.precio_unidad` en todas las bases? Si no, ¿lista mayorista?
- [ ] OQ#3: ¿Feature flag por empresa hasta piloto?
- [ ] OQ#5: ¿Mismas reglas en `Devol - Cliente` / `ND Anul NC`? (diseño: sí, mismo universo)
