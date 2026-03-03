# Fase 7 — movstock_pedi (implementada)

Relación movimiento de stock ↔ pedido interno (PEDI). Paridad con VB6 CargaMovStock: por cada renglón con pedido se inserta una fila en `movstock_pedi`.

## Cambios realizados

### Backend (`core/services/administranet_stock.py`)

- **listar_renglones_temporales:** el SELECT incluye `c.codmov_nro_pedi` para que el alta reciba el id numérico del pedido por renglón.
- **agregar_renglon_temporal:** se acepta `codmov_nro_pedi` en `datos`; si no viene, se deriva de `nro_pedi` cuando es numérico. El INSERT en `cuerpostock_mstock` incluye la columna `codmov_nro_pedi`.
- **actualizar_renglon_temporal:** mismo criterio; el UPDATE actualiza `codmov_nro_pedi`.
- **alta_movimiento:** tras el bucle de INSERT en `stock` y antes de guardar series, se recorre `renglones` y por cada uno con `codmov_nro_pedi` (o `nro_pedi` numérico) se ejecuta `INSERT INTO movstock_pedi (codmov_movstock, codmov_pedi, anulado) VALUES (codigo_mov, codmov_pedi, 'No')`.

### API (`stock/api_views.py`)

- En agregar y actualizar renglón, el body acepta `nro_pedi` y `codmov_nro_pedi`; se pasan al servicio en `datos`.

### Frontend (`stock/templates/stock/alta_movimiento.html`)

- En `agregarRenglon` y `confirmarFilaBusqueda`, si `cabecera.nro_pedi` está definido, se envía `nro_pedi` en el body para que el renglón quede asociado al pedido seleccionado.

## Tablas

- **cuerpostock_mstock:** columnas `nro_pedi` (VARCHAR) y `codmov_nro_pedi` (DECIMAL) — ambas se persisten.
- **movstock_pedi:** `id_movstock_pedi`, `codmov_movstock`, `codmov_pedi`, `anulado`. Se inserta una fila por renglón con pedido.

## Referencia VB6

CargaMovStock.frm ~4419–4426: AddNew en movstock_pedi con `codmov_movstock = contador`, `codmov_pedi = CuerpoStock!codmov_nro_pedi`.
