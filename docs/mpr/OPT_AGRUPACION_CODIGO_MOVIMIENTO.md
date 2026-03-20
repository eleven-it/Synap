# Agrupación de líneas OPT sin `id_opt`

## Objetivo

Dejar de **escribir** `lista_produccion_agrupada.id_opt` en Synap: el identificador de la OPT para el usuario sigue siendo el **`id_lista_produccion` de la línea principal** (la que se devuelve al confirmar «Generar OPT»).

## Mecanismo

- Tras **Generar OPT** (`crear_opt_multiples_articulos`), todas las filas del lote reciben el mismo **`codigo_movimiento_opt` negativo**: `-id_lista_principal`. Ese valor no es un movimiento de stock; solo agrupa filas en MySQL.
- Tras **Liberar OPT** (`ejecutar_liberar_opt`), ese campo pasa a ser el **CodigoMovimiento** real del MSTOCK (**> 0**) en **todas** las líneas del lote (no solo en la principal).
- **`get_opt_detalle`** y afines listan las líneas con `WHERE codigo_movimiento_opt = <valor común>` (negativo o positivo).
- Los listados que debían mostrar solo OPT ya liberadas filtran **`codigo_movimiento_opt > 0`** (no basta con `IS NOT NULL`, para excluir el placeholder).

## Cierre de OPT

En **`cerrar_opt`**, si el valor sigue siendo placeholder negativo, se pone **`NULL`** al cerrar; si ya es MSTOCK positivo, se conserva para trazabilidad.

## Datos heredados

Bases que aún tienen **`id_opt`** informado y **`codigo_movimiento_opt`** nulo en líneas antiguas: Synap sigue leyendo **`id_opt`** solo como **compatibilidad** para agrupar esas filas. No es obligatorio migrar SQL salvo que se quiera unificar todo al esquema nuevo.

## Referencias

- `mpr/services.py`: `_mpr_codigo_opt_placeholder_desde_principal`, `get_opt_detalle`, `crear_opt_multiples_articulos`, `ejecutar_liberar_opt`, `cerrar_opt`, `listar_opt_listado`.
- Esquema: `docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md`.
