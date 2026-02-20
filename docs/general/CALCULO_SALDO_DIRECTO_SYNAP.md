# Cálculo de saldo directo (Fase 2 – Ingreso Mov. Stock)

Implementación del **calculo_saldo_directo** en el formulario de ingreso de movimiento de stock: el usuario puede ingresar el saldo que desea dejar en depósito; el sistema obtiene el saldo actual, calcula la diferencia y propone Entrada o Salida con la cantidad correspondiente.

## Condición de visibilidad

- El campo **Saldo deseado** solo se muestra cuando se cumplen **todas** estas condiciones:
  - La empresa tiene `calculo_stock_saldo = "Si"` (parámetro en `configuracion.calculo_stock_saldo` o equivalente).
  - El motivo del movimiento es **Ajuste** (código 2).
  - Hay **depósito origen** seleccionado.
  - Hay un **artículo seleccionado** en la fila de búsqueda (fila de agregar).

Si en la base no existe la columna `calculo_stock_saldo` en `configuracion`, el backend devuelve `"No"` y el campo no se muestra.

## Backend

- **Servicio** `core/services/administranet_stock.py`:
  - **get_calculo_stock_saldo(base_empresa):** Lee `COALESCE(calculo_stock_saldo, 'No')` desde `configuracion` (una fila). Si la columna no existe, captura el error y devuelve `"No"`.

- **API** `stock/api_views.py` — **api_ingreso_datos_iniciales**  
  Incluye en la respuesta el campo **calculo_stock_saldo** (`"Si"` o `"No"`).

- **API existente** **api_ingreso_saldo** (`?id_articulo=&id_deposito=`): se usa para obtener el saldo actual del artículo en el depósito antes de aplicar la fórmula.

## Fórmula (frontend)

Con **saldo_actual** (api_ingreso_saldo) y **saldo_deseado** (valor del input):

- Si `saldo_deseado > saldo_actual` → **Entrada**, `cantidad = saldo_deseado - saldo_actual`.
- Si `saldo_deseado < saldo_actual` → **Salida**, `cantidad = saldo_actual - saldo_deseado`.
- Si `saldo_deseado = saldo_actual` → `cantidad = saldo_deseado`, se mantiene el ES actual de la fila.

Tras el cálculo se actualizan **filaBusqueda.cantidad** y **filaBusqueda.ES**; el usuario puede pulsar Enter o "Agregar" para agregar el renglón.

## UX/UI

- **Ubicación:** Panel Artículos, bloque opcional **encima de la tabla**, solo visible cuando `mostrarSaldoDeseado` es verdadero.
- **Campo:** Input numérico "Saldo deseado", placeholder "Saldo que desea dejar en depósito". Solo números; mínimo 0.
- **Disparo:** Al **salir del campo (blur)** o al pulsar **Enter** se ejecuta `ejecutarCalculoSaldoDirecto()`: se valida artículo/depósito y valor, se llama a api_ingreso_saldo, se aplica la fórmula y se rellenan cantidad y ES en la fila de búsqueda.
- **Validación:** Si no hay artículo o depósito: "Seleccione primero un artículo y depósito origen." Si el valor está vacío o no es válido: "Debe ingresar una cantidad (válida)."

## Referencias

- VB6: `CargaMovStock.frm` — `calculo_saldo_directo_LostFocus`, `Motivo.ListIndex = 1` (Ajuste), `Principal.calculo_stock_saldo`.
- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md): actualizar calculo_saldo_directo → Sí.
