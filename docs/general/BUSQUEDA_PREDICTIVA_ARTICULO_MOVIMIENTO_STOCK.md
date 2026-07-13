# Búsqueda predictiva y por código de barras en Ingreso Mov. Stock

Flujo de búsqueda de artículos en el ingreso de renglón de movimiento de stock, con detalle de precios, stock por depósito y stock por lote integrado en el mismo campo (paridad con el formulario "Selección de artículo" de AdministraNET). El mismo campo admite **búsqueda predictiva** (tecleo) y **ingreso rápido por código de barras** (lector + Enter), con la misma lógica que el TPV.

## Objetivo

En AdministraNET, el ingreso de renglón abre un modal "Selección de artículo" que muestra Artículos y Precios, Stock por depósito y Stock por lote. En Synap esa información se integra en la **búsqueda predictiva** del campo de búsqueda, sin abrir un segundo formulario. Además, al escanear un código (o pegar código y pulsar Enter), se hace **búsqueda directa por código** (exacta): si existe un artículo se agrega a la línea; si no existe se muestra "Código inexistente".

## Tablas utilizadas

| Tabla | Uso |
|-------|-----|
| `articulo` | Búsqueda por nombre, código, código de barras; campos de precios (id_manual, PrecioCosto, Precio1V, PNOficial, Alicuota, Moneda). |
| `stock_deposito` | Saldo por depósito para cada artículo. |
| `deposito` | Nombre del depósito (JOIN con stock_deposito: id_deposito = CodDeposito). |
| `lote` | Lotes del artículo (id_articulo, cod_lote, fecha_vto_lote). |
| `lote_stock` | Stock por lote y depósito (id_lote, id_deposito, stock_lote). |

## Backend

- **Servicio:** `core/services/administranet_stock.py`
  - `get_stock_por_deposito(base_empresa, id_articulo)`: lista depósitos con saldo para el artículo.
  - `get_stock_por_lote(base_empresa, id_articulo, id_deposito=None)`: lista lotes con cod_lote, fecha_vto_lote, stock_lote (opcionalmente filtrado por depósito).
  - `_buscar_articulos_con_precios(base_empresa, q, limit, lista_precio=2, tipo_art_fab=None)`: búsqueda con campos de precios; `tipo_art_fab` opcional filtra por tipo de fabricación.
  - `buscar_articulos_para_movimiento(base_empresa, q, limit, id_deposito=None)`: orquesta búsqueda + stock por depósito + stock por lote por cada resultado.
  - `buscar_articulo_por_codigo_exacto(base_empresa, codigo, id_deposito=None)`: búsqueda exacta por id_manual, IDArt, NroCodBarra, NroCodBarraF, CodigoArticuloT, CodArtProv; devuelve un único artículo con stock_depositos y stock_lotes o None.

- **API:** `stock/api_views.py`
  - **api_ingreso_articulos** — **GET** `?q=...&detalle=1&id_deposito=...` (opcionales)
    - Sin `detalle`: devuelve solo IDArt, CodigoArticulo, Descripcion (comportamiento anterior).
    - Con `detalle=1`: devuelve por cada artículo precios, `stock_depositos` y `stock_lotes`. Si se envía `id_deposito`, los lotes se filtran por ese depósito.
  - **api_ingreso_articulos_por_codigo** — **GET** `?codigo=...&id_deposito=...` (opcional)
    - Búsqueda **exacta** por código (id_manual, IDArt, NroCodBarra, NroCodBarraF, CodigoArticuloT, CodArtProv), misma lógica que TPV (`self_checkout.api_views._buscar_articulo`).
    - Devuelve `{ "articulos": [item] }` con un único artículo en el mismo formato que la búsqueda con detalle (precios, stock_depositos, stock_lotes), o `{ "articulos": [] }` si no hay coincidencia.
    - Usado por el front al pulsar **Enter** en el input de búsqueda cuando hay texto: si hay un resultado se asigna a la fila y se agrega el renglón; si no hay resultado se muestra "Código inexistente".

## Frontend

- **Vista:** Ingreso Mov. Stock (`stock/templates/stock/alta_movimiento.html`).
- **Dos flujos en el mismo input:**
  - **Búsqueda predictiva:** Al escribir (sin Enter), se llama a `api_ingreso_articulos` con `detalle=1` y, si hay depósito origen, con `id_deposito`. El dropdown de sugerencias muestra por cada ítem: línea principal (código y descripción), precios, stock por depósito, stock por lote. El usuario elige un artículo y pulsa Enter o "Agregar" para confirmar.
  - **Ingreso por código de barras:** Al pulsar **Enter** con texto en el input, se llama primero a `api_ingreso_articulos_por_codigo?codigo=...`. Si hay un resultado se asigna a la fila y se agrega el renglón (mismo flujo que confirmar fila); si no hay resultado se muestra el mensaje "Código inexistente" (texto bajo el input, temporal) y no se abre el dropdown.
- Placeholder del input: "Buscar por nombre o escanear código de barras (Enter)".

## Referencias

- [MODULO_STOCK_SYNAP.md](MODULO_STOCK_SYNAP.md): módulo Stock y APIs.
- [tablas/articulo.md](tablas/articulo.md), [tablas/stock_deposito.md](tablas/stock_deposito.md), [tablas/lote.md](tablas/lote.md), [tablas/lote_stock.md](tablas/lote_stock.md): esquema de tablas.
- Formulario VB6: `ABMArticulo_seleccion.frm` (Data_Stock, data_lote, busqueda_articulo).
