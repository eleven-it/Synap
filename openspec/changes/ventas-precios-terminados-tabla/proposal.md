# Propuesta — Precios terminados en tabla (`/ventas/precios-terminados/`)

**Change:** `ventas-precios-terminados-tabla`  
**Fecha:** 09/07/2026

## Intención

Migrar a Synap la actualización masiva de precios de **productos terminados** (y 2da selección) en modo tabla operativa, alineada al tablero MPR: filtros en dos niveles, edición inline de precios neto/final por lista, cambio masivo server-side, y persistencia en `articulo` + `precios_historial` con recálculo de `Util1-5`.

## Alcance P0

- Ruta `/ventas/precios-terminados/` con permiso `ventas.precios_terminados.editar`
- Filtro primario Terminado | 2da; catálogos dependientes; código multi tags predictivo
- Tabla paginada con columnas dinámicas por listas 1–5
- Guardado lote + cambio masivo (%, monto, establecer, redondear) + reserva
- Tests y documentación en `docs/ventas/`

## Fuera de alcance

- Relay Tiendanube automático tras cambio
- Tablas staging `precios_masivo_temp`
- Lista Oficial (solo listas 1–5 en MVP)
