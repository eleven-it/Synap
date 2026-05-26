# Diseño técnico — Gap $ + Top 10 (resumen ejecutivo)

**Fecha:** 11/05/2026

## 1. Shape JSON (respuesta `GET .../executive-summary/`)

Fragmento añadido o extendido sobre el payload actual:

```json
{
  "fecha_referencia": "2026-05-11",
  "kpis": {
    "ventas_netas_dia": 125000.5,
    "ventas_ayer_monto": 98000.0,
    "gap_vs_ayer_monto": 27000.5,
    "pct_vs_ayer": 27.55,
    "pct_vs_misma_semana_anterior": null,
    "tickets": 42,
    "ticket_promedio": 2976.2,
    "unidades_vendidas": 150.25,
    "ventas_misma_semana_anterior_monto": 0
  },
  "top_productos": [
    {
      "id_art": 1234,
      "codigo_articulo": "ART-01",
      "descripcion": "Producto ejemplo",
      "unidades": 12.0,
      "importe_neto": 45000.0
    }
  ],
  "meta": {
    "definicion": "executive-sales-v1",
    "hora_eje": "FechaControl",
    "dia_contable": "Fecha",
    "top_productos_criterio": "importe_neto_linea"
  }
}
```

## 2. Consulta SQL propuesta (MySQL empresa)

**Objetivo:** agregar por `st.IDArt` el neto de renglón (`PrecioNetoxR` con signo FA/NC) y unidades con la misma paridad que `_unidades_dia`.

**Filtros:** `cc.Fecha = %s`, `_base_cc_where(cc)`, `st.Anulado = 'No'`, `st.TipoComp IN ('Venta','Venta TPV','Devol - Cliente','ND Anul NC')`, `st.IDArt` no nulo y distinto de 0.

**Orden:** `importe_neto DESC`.

**Pseudo-SQL:**

```sql
SELECT z.id_art, z.codigo_articulo, z.descripcion, z.unidades, z.importe_neto
FROM (
  SELECT
    st.IDArt AS id_art,
    COALESCE(MAX(a.CodigoArticulo), '') AS codigo_articulo,
    COALESCE(MAX(a.NombreArticulo), '-') AS descripcion,
    SUM(CASE WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.Cantidad,0)
             WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.Cantidad,0)
             ELSE 0 END) AS unidades,
    SUM(CASE WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.PrecioNetoxR,0)
             WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.PrecioNetoxR,0)
             ELSE 0 END) AS importe_neto
  FROM stock st
  INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
  LEFT JOIN articulo a ON a.IDArt = st.IDArt
  WHERE cc.Fecha = %s
    AND (condición base cuentacliente)
    AND st.Anulado = 'No'
    AND st.TipoComp IN (...)
    AND st.IDArt IS NOT NULL AND st.IDArt <> 0
  GROUP BY st.IDArt
) z
WHERE ABS(z.importe_neto) > 0.000001
ORDER BY z.importe_neto DESC
LIMIT 10
```

**Nota:** alineado conceptualmente con `reports/services/ventas_netas.py` — `_sum_monto_sql_stock_line` / `_sum_unidades_sql_stock_line`.

## 3. Wireframe móvil (Top 10, ≤ 640 px)

```
┌─────────────────────────────────────┐
│  Top 10 productos (por $ neto)      │  ← misma jerarquía tipográfica que gráficos
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ ART-01          +12 u           │ │  ← fila tipo tarjeta / banda
│ │ Producto ejemplo                │ │
│ │ $ 45.000,00                     │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ ...                             │ │
│ └─────────────────────────────────┘ │
│ (scroll vertical; ancho 100%)      │
└─────────────────────────────────────┘
```

**Desktop (≥ lg):** misma información en `<table class="w-full text-sm">` con columnas Código | Descripción | Unidades | Importe neto; `overflow-x-auto` por si descripciones largas.

## 4. Archivos tocados

| Capa | Ruta |
|------|------|
| Servicio | `reports/services/executive_sales_summary.py` |
| Contrato tests | `reports/tests/test_executive_summary_contract.py` |
| Plantilla | `reports/templates/reports/executive_summary.html` |
| JS | `reports/static/reports/js/executive_summary.js` |
| Doc producto | `docs/reports/SPEC_DASHBOARD_RESUMEN_EJECUTIVO_VENTAS.md` |

## 5. Verificación

- `docker exec Synap_app python manage.py test reports.tests.test_executive_summary_contract`
- Smoke manual: `/reports/dashboard/resumen-ejecutivo-ventas/` con fecha con datos.
