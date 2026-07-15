# Spec — Analítica histórico de precios

## REQ-1 Historial por artículo

**Given** usuario con `ventas.precios_historial.ver` o `ventas.precios_terminados.editar`  
**When** GET `/ventas/precios-terminados/api/historial/<id_articulo>/` con `lista`, `fecha_desde`, `fecha_hasta`  
**Then** respuesta JSON con filas ordenadas, neto/final/util/costo, `delta_neto`, `delta_pct`, `tipo_modificacion`, `fecha`

## REQ-2 Modal en precios terminados

**Given** tabla precios terminados  
**When** usuario pulsa «Historial» en una fila  
**Then** modal muestra serie temporal del artículo para listas visibles en pantalla

## REQ-3 Ranking agregado

**Given** filtros fecha, lista, rubro, marca opcionales  
**When** GET `/ventas/evolucion-precios/`  
**Then** tabla ranking con variación % en período, código, nombre, rubro

## REQ-4 Reports

**Given** slug `evolucion-precios` en Reports  
**When** ejecutar informe con mismos filtros  
**Then** mismos datos que ranking SSR (vía runner)
