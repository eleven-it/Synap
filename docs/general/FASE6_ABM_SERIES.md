# Fase 6: ABMSeries (números de serie) — Ingreso movimiento de stock

## Alcance

Gestión de **números de serie** por renglón en el alta de movimiento de stock (paridad con CargaMovStock.frm / ABMSerie_Click y GuardarSerie en VB6).

## Implementación

### Backend (`core/services/administranet_stock.py`)

- **Renglones:** `listar_renglones_temporales` incluye `serie_articulo` ('Si'/'No') por renglón (LEFT JOIN articulo).
- **Limpieza:** En alta y en `limpiar_temporales_usuario` se borran `serie_entrada_temp` y `serie_salida_temp` para el usuario y tipo 'Mstock'.
- **Series por renglón:**
  - `listar_series_renglon(base_empresa, id_usuario, orden, id_articulo, es_entrada)` — listado desde temp (entrada o salida).
  - `listar_series_disponibles_deposito(base_empresa, id_articulo, id_deposito)` — series con `disponible='Si'` para salida.
- **Alta/Baja en temp:**
  - `agregar_serie_entrada_temp(..., nro_serie, vto_serie opcional)`.
  - `agregar_serie_salida_temp(..., id_serie_entrada)`.
  - `quitar_serie_entrada_temp` / `quitar_serie_salida_temp`.
- **Validación al confirmar:** `_validar_series_renglones`: para cada renglón con `serie_articulo == 'Si'`, la cantidad de registros en temp debe coincidir con `Cantidad`.
- **GuardarSerie:** `_guardar_series_movimiento` (misma transacción que el alta):
  - **Entrada:** INSERT `serie_entrada` desde `serie_entrada_temp`; luego INSERT `serie_movimiento` desde `serie_entrada` JOIN stock.
  - **Salida:** INSERT `serie_movimiento` desde `serie_salida_temp` JOIN stock; UPDATE `serie_entrada` SET `disponible = 'No'` para las series usadas.

### API (`stock/api_views.py`)

- **GET** `api/ingreso/series-renglon/?orden=&id_articulo=&es_entrada=0|1` — series del renglón.
- **GET** `api/ingreso/series-disponibles/?id_articulo=&id_deposito=` — series disponibles en depósito (salida).
- **POST** `api/ingreso/serie-add/` — agrega serie (entrada: nro_serie, vto_serie?; salida: id_serie_entrada).
- **POST** `api/ingreso/serie-remove/` — quita serie (tipo 'entrada'|'salida', id_temp).

### Frontend (`stock/templates/stock/alta_movimiento.html`)

- **Columna Series:** Si `r.serie_articulo === 'Si'` se muestra botón (ícono layers) que abre el modal; si no, ícono deshabilitado “no seriado”.
- **Modal "Números de serie":**
  - Lista de series del renglón con opción de quitar.
  - **Entrada (ES === 'E'):** inputs nro_serie y vto_serie + botón Agregar.
  - **Salida (ES === 'S'):** select de series disponibles en el depósito + botón Agregar.
  - Aviso cuando la cantidad de series ≠ Cantidad del renglón.

### Confirmación del movimiento

- Antes de grabar, el backend valida que todo renglón con artículo seriado tenga cantidad de series en temp igual a Cantidad; si no, devuelve error y no confirma.
- Al confirmar, se ejecuta GuardarSerie dentro de la misma transacción y luego se eliminan los temporales (cuerpo y series).

## Documentación relacionada

- **docs/general/ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md** — eventos ABMSerie_Click, GuardarSerie, AgregarRenglonSerie y atajo F7 actualizados como implementados.
- Tablas: `docs/general/tablas/serie_entrada_temp.md`, `serie_salida_temp.md`, `serie_entrada.md`, `serie_movimiento.md`.
