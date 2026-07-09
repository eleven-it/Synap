# Propuesta — Analítica histórico de precios

**Change:** `ventas-analitica-precios-historial`  
**Fecha:** 09/07/2026

## Intención

Exponer en Synap la lectura y analítica de `precios_historial` (MySQL legacy): evolución por artículo con variaciones calculadas y ranking agregado por rubro/marca, paridad con VB6 (`HistoPrecio` / pestaña en `CargaArticulo`).

## Alcance P0

- Servicio `ventas/services/precios_historial.py` (listado, resumen, ranking)
- API GET historial por artículo + modal desde precios terminados
- Página `/ventas/evolucion-precios/` (ranking variaciones en período)
- Runner Reports `evolucion-precios` reutilizando el servicio
- Permiso `ventas.precios_historial.ver`, tests y docs

## Fuera de alcance

- Gráficos Chart.js (fase posterior)
- Ponderación por ventas en índices
- Estandarización completa de `tipo_modificacion` VB6
