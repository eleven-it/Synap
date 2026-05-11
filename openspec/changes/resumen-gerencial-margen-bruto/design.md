# Diseño técnico — Margen bruto (resumen ejecutivo)

**Fecha:** 11/05/2026

## 1. Ubicación en código

| Capa | Archivo |
|------|---------|
| Agregados SQL | `reports/services/executive_sales_summary.py` (nuevas funciones internas + ampliación de `run_executive_summary`) |
| API | `reports/executive_summary_api_views.py` (sin ruta nueva; mismo `ExecutiveSummaryAPIView`) |
| UI | `reports/templates/reports/executive_summary.html`, `reports/static/reports/js/executive_summary.js` |
| Tests | `reports/tests/test_executive_summary_contract.py` |

## 2. Universo de renglones (paridad con Top 10 / unidades)

- **Join:** `stock st` → `cuentacliente cc` on `CodigoMovimiento`.
- **Filtros `cc`:** mismos que `_base_cc_where`, `cc.Fecha = día`, sucursal opcional en `cc.CodSucursal`.
- **Filtros `st`:** `st.Anulado = 'No'`, `st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')`.
- **Signo FA vs NC:** para **`PrecioNetoxR`** y **`PrecioCostoxR`**, misma expresión `CASE` que en `_top_productos_ventas_dia` (facturas suman, notas de crédito restan).

## 3. Shape JSON (fragmento nuevo)

```json
{
  "margen_bruto": {
    "venta_neta_lineas": 120000.5,
    "costo_neto_lineas": 78000.0,
    "margen_absoluto": 42000.5,
    "pct_sobre_venta_lineas": 35.0
  },
  "margen_por_rubro": [
    {
      "codigo_rubro": 3,
      "nombre_rubro": "Perfumería",
      "venta_neta": 50000.0,
      "costo_neto": 31000.0,
      "margen_absoluto": 19000.0,
      "pct_sobre_venta": 38.0
    }
  ],
  "margen_por_subrubro": [
    {
      "id_subrubro": 12,
      "codigo_rubro": 3,
      "nombre_rubro": "Perfumería",
      "nombre_subrubro": "Capilar",
      "venta_neta": 20000.0,
      "costo_neto": 12000.0,
      "margen_absoluto": 8000.0,
      "pct_sobre_venta": 40.0
    }
  ],
  "meta": {
    "margen_costo_criterio": "precio_costoxr_linea",
    "margen_venta_criterio": "precio_netoxr_linea"
  }
}
```

- **`pct_sobre_venta` / `pct_sobre_venta_lineas`:** `NULL` o omisión en JSON como `null` cuando el denominador (venta neta del grupo) es 0.
- **Orden:** listas ordenadas por **`venta_neta`** descendente (empate arbitrario estable por nombre).

## 4. SQL — total del día

Pseudo-expresión (reutilizar parámetros del día y sucursal):

```sql
SELECT
  SUM(CASE ... THEN COALESCE(st.PrecioNetoxR,0) ... END) AS venta_neta_lineas,
  SUM(CASE ... THEN COALESCE(st.PrecioCostoxR,0) ... END) AS costo_neto_lineas
FROM stock st
INNER JOIN cuentacliente cc ON ...
WHERE ...
```

**Post-cálculo en Python:** `margen_absoluto = venta_neta_lineas - costo_neto_lineas`; `pct = margen / venta_neta_lineas` si `venta_neta_lineas != 0`.

## 5. SQL — por rubro

- **Join:** `LEFT JOIN articulo a ON a.IDArt = st.IDArt` → `LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro`.
- **Grupo:** `COALESCE(a.CodigoRubro, -1)` (o constante sentinela acordada) + nombre mostrable `COALESCE(r.NombreRubro, 'Sin clasificar')`.
- Renglones sin `IDArt` válido entran en bucket «Sin clasificar».

## 6. SQL — por subrubro

- **Join:** `LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro` (y opcional `rubro` para nombre de rubro padre).
- **Grupo:** `COALESCE(sr.IDSubRubro, -1)`, nombres `NombreSubRubro` / `NombreRubro`.

## 7. UI (directrices)

- Bloque titulado p. ej. **«Rentabilidad del día»**: tarjeta(s) con margen absoluto y % sobre venta de líneas; texto de ayuda breve en español sobre criterio (costo y venta **por renglón de facturación**).
- Tablas **Rubros** y **Subrubros** (desktop); en móvil, mismo patrón responsive que Top 10 (tarjetas o scroll horizontal).
- Formato monetario y porcentajes `es-AR`, coherente con KPIs existentes.

## 8. Metadatos y trazabilidad

- Ampliar **`meta.definicion`** a versión nueva (p. ej. `executive-sales-v2`) o mantener v1 y añadir solo claves nuevas; preferible **bump** de versión en `meta` para que front y pruebas detecten contrato extendido.
