# Diseño — Analítica histórico de precios

## Arquitectura

```
precios_historial (MySQL)
    → ventas/services/precios_historial.py
        → API JSON (drill-down)
        → evolucion_precios_view (ranking SSR)
        → reports/services/evolucion_precios_runner.py
```

## Cálculo de variaciones

Snapshots ordenados por `fecha_control`, `id_precios_historial`. Deltas en Python (sin `LAG` SQL) para compatibilidad MariaDB/MySQL legacy.

- `delta_neto = neto_actual - neto_anterior`
- `delta_pct = delta / anterior * 100` si anterior > 0

Ranking período: por `id_articulo`, primer vs último snapshot dentro del rango de fechas.

## Permisos

- `ventas.precios_historial.ver` — consulta historial y ranking
- `ventas.precios_terminados.editar` — sigue permitiendo edición; historial visible con cualquiera de los dos
