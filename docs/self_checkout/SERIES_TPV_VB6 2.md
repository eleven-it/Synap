# Análisis: Series (números de serie) en TPV administraNET VB6

## 1. Concepto

Artículos con **articulo.serie = 'Si'** son "seriados": cada unidad vendida debe asociarse a un **número de serie** que existe en stock (tabla `serie_entrada`). Al confirmar la venta, esos números se marcan como usados y se registra la salida.

## 2. Tablas administraNET

| Tabla | Uso |
|-------|-----|
| **serie_entrada** | Series disponibles en depósito: id_serie_entrada, id_articulo, nro_serie, desc_serie, vto_serie, disponible ('Si'/'No'), id_deposito, fecha. |
| **serie_salida_temp** | Temporal por usuario/sesión: id_usuario, tipo_comprobante='TPV', id_articulo, **orden** (igual al renglón en grid), nro_serie, desc_serie, vto_serie, id_serie_entrada, visualiza, id_deposito. Una fila por cada número de serie elegido para ese renglón. |
| **serie_movimiento** | Histórico de salidas: codigo_mov_vta, id_articulo, nro_serie, id_serie_entrada, id_cliente, comprobante, nro_comprobante, id_stock, id_deposito, etc. |
| **stock** | Por ítem: si el renglón tiene serie='Si', se graba **serie**='Si' y **desc_serie** (texto resumen de los números de serie). |

## 3. Flujo en TPV VB6

1. **Al agregar un artículo seriado** (desde grilla/búsqueda): después de agregar el renglón se abre el formulario **Serie_salida** (modal) con IDArt, Cantidad, orden, id_deposito. El usuario elige exactamente **Cantidad** números de serie desde `serie_entrada` (disponible='Si', mismo id_articulo e id_deposito). Los elegidos se insertan en **serie_salida_temp** (orden = renglón). El renglón queda con **serie**='Si' y **desc_serie** = concatenación de nro_serie (ej. "SN1 - vto1, SN2 - vto2").
2. **Botón "Series" (F10)** en la barra del TPV: si el renglón actual es de un artículo seriado, abre Serie_salida en modo edición (banderaAlta=1) con ese orden y cantidad; se borran las filas de serie_salida_temp para ese orden y se vuelven a elegir.
3. **Validación antes de guardar factura**:  
   - **ESerie**: existe al menos un renglón con artículo seriado.  
   - **ValCantSerie**: para cada renglón seriado, `count(serie_salida_temp WHERE id_articulo, orden)` debe ser igual a la cantidad del renglón. Si no, mensaje: "La cantidad de números de serie no coincide con la cantidad de artículos seriados."
4. **Al guardar factura**:  
   - Por cada renglón se escribe en **stock** (serie, desc_serie).  
   - **GuardarSerie**: INSERT de serie_salida_temp en **serie_movimiento** (con codigo_mov, id_stock, id_cliente, comprobante, nro_comprobante, etc.), luego UPDATE **serie_entrada** SET disponible='No' WHERE id_serie_entrada IN (los usados en esta venta).

## 4. Réplica en Synap TPV

- **Cart item**: columnas **serie** ('Si'/'No'), **desc_serie** (texto). Tabla **self_checkout_cart_item_serie** (cart_item_id, id_serie_entrada, nro_serie, desc_serie, vto_serie) para la lista de series elegidas.
- **Al agregar** artículo con serie='Si': el backend puede devolver `requiere_series: true`; el front abre modal "Selección de números de serie", pide N disponibles (GET por id_articulo, id_deposito) y el usuario elige N; POST asigna esas series al ítem.
- **Botón "Series"** en la fila del carrito (solo si ítem es seriado): abre el mismo modal para ver/editar las series de ese ítem.
- **Validación antes de pagar**: si hay ítems con serie='Si', validar que cada uno tenga exactamente cantidad series asignadas.
- **Confirmación**: al escribir stock, setear serie y desc_serie; luego INSERT serie_movimiento y UPDATE serie_entrada.disponible='No' para las series del carrito.
