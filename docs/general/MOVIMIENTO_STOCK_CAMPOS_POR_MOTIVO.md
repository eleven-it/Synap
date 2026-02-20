# Movimiento de stock: campos por motivo y paridad VB6–Synap

**Objetivo:** Documentar el comportamiento del motivo en movimiento de stock (AdministraNET VB6), el seteo de campos “movimiento en artículo” y por motivo, y los cambios realizados en Synap para alcanzar paridad.

**Referencias:** `CargaMovStock.frm`, `core/services/administranet_stock.py`, [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md), [ESQUEMA_TABLAS_STOCK_MIGRACION.md](ESQUEMA_TABLAS_STOCK_MIGRACION.md).

---

## 1. Correspondencia de motivos (VB6 ↔ Synap)

En VB6 el combo **Motivo** usa **ListIndex** 0..9 (y 10/11 si `pedidos_parte_produccion = "Si"`). En Synap se usan **códigos numéricos 1..12** definidos en `MOTIVOS_MOVIMIENTO` (`core/services/administranet_stock.py`).

| VB6 ListIndex | Synap código | Nombre |
|---------------|--------------|--------|
| 0 | 1 | Stock Inicial |
| 1 | 2 | Ajuste |
| 2 | 3 | Faltante |
| 3 | 4 | Sobrante |
| 4 | 5 | Rotura |
| 5 | 6 | Transferencia |
| 6 | 7 | Mov. Interno Salida |
| 7 | 8 | Mov. Interno Entrada |
| 8 | 9 | Armado |
| 9 | 10 | Desarmado |
| 10 | 11 | Pedido producción |
| 11 | 12 | Parte producción |

---

## 2. “Movimiento en artículo” (tabla `stock`)

En AdministraNET, al guardar un movimiento, **cada renglón de la tabla `stock`** recibe el tipo de movimiento seleccionado. Eso es el “movimiento en artículo”: el motivo queda grabado por línea para informes y filtros.

### 2.1 Comportamiento en VB6 (CargaMovStock.frm)

Al confirmar (Aceptar), por cada renglón de CuerpoStock se hace `rs_stock.AddNew` y se asignan:

- **`Tipo`** = `"Movimiento Stock"` (fijo)
- **`TipoComp`** = **`Motivo.Text`** (texto del motivo: "Stock Inicial", "Ajuste", "Transferencia", etc.)
- **`Comprobante`** = `"MSTOCK"`
- **`NroComprobante`** = número del comprobante del movimiento
- **`anulado`** = `"No"`

Referencia en código VB6 (aprox. líneas 4032–4036, 4289–4293):

```vb
rs_stock.Fields!Tipo = "Movimiento Stock"
rs_stock.Fields!TipoComp = Motivo.Text
rs_stock.Fields!anulado = "No"
rs_stock.Fields!Comprobante = "MSTOCK"
rs_stock.Fields!NroComprobante = Nro
```

### 2.2 Brecha inicial en Synap

En el alta de movimiento, Synap **no** escribía en `stock` los campos `Tipo`, `TipoComp`, `Comprobante` ni `NroComprobante`, por lo que el “movimiento en artículo” no quedaba alineado con VB6.

### 2.3 Cambio realizado en Synap

En `core/services/administranet_stock.py`, en la función `alta_movimiento`, cada `INSERT` en `stock` ahora incluye:

- **`Tipo`** = `'Movimiento Stock'`
- **`TipoComp`** = texto del motivo (mapeo código → nombre vía `MOTIVO_CODIGO_A_NOMBRE`)
- **`Comprobante`** = `'MSTOCK'`
- **`NroComprobante`** = número del comprobante del movimiento
- **`anulado`** = `'No'`

Además, **`movimiento_stock.motivo_movimiento`** se persiste en **texto** (igual que `Motivo.Text` en VB6), no en código numérico.

---

## 3. Campos de cabecera que dependen del motivo (`movimiento_stock`)

En VB6 estos campos se setean según el motivo elegido al grabar la cabecera.

| Motivo (VB6 / Synap) | Campo | Comportamiento VB6 | Implementación Synap |
|----------------------|--------|--------------------|------------------------|
| Todos | `motivo_movimiento` | Texto del combo (Motivo.Text) | Texto según código (mapa MOTIVO_CODIGO_A_NOMBRE) |
| Todos | `deposito_destino` | Si **Transferencia (5)** → DepositoDestino; **resto** → DepositoOrigen | Si motivo ≠ 6 se usa `deposito_origen`; si es 6 se usa `deposito_destino` enviado (fallback: origen) |
| Mov. Interno S/E (6, 7) | `id_cliente` | Lista_entidad o 0 | Cabecera envía `id_cliente`; se persiste tal cual |
| Transferencia (5), Mov. Interno (6, 7) | `id_vendedor` | ListaVendedor o 0 | Cabecera envía `id_vendedor`; se persiste tal cual |
| Desarmado (9) | `cant_desarme` | cantDesarme.Text | Cabecera envía `valor_variable` / `cant_desarme`; ya se persistía |
| Pedido producción (10) | `tipo_mov` | `"OPT"` | Se escribe `tipo_mov = "OPT"` en INSERT |
| Parte producción (11) | `tipo_mov` | `"OPP"` | Se escribe `tipo_mov = "OPP"` en INSERT |

**Cambios realizados en Synap:**

1. **`deposito_destino`:** Si el motivo no es Transferencia (código 6), se asigna `deposito_destino = deposito_origen`. Si es Transferencia y no se envía destino, se usa `deposito_origen` como respaldo.
2. **`tipo_mov`:** Se agregó al `INSERT` en `movimiento_stock`: motivo 10 → `"OPT"`, motivo 11 → `"OPP"`, resto → `NULL`.  
   **Requisito:** La tabla `movimiento_stock` debe tener la columna `tipo_mov` (usada en VB6 y en Lista_Pedidos_OPT). Si no existe, debe agregarse en la base.

---

## 4. Campos por renglón que dependen del motivo (`stock`)

| Motivo | Campo | Comportamiento VB6 | Implementación Synap |
|--------|--------|--------------------|------------------------|
| Todos | Tipo, TipoComp, Comprobante, NroComprobante, anulado | Ver §2 | Implementado (§2.3) |
| Transferencia (5), Mov. Interno S/E (6, 7) | `CodViajante` | Desde CuerpoStock (ListaVendedor por renglón) | Se usa `id_vendedor` de cabecera para motivos 6, 7, 8; opcionalmente `CodViajante` del renglón si se envía |
| Armado/Desarmado (8, 9) | `CodDeposito` | Por renglón (IdDeposito) | Se usa `CodDeposito` del renglón o cabecera |

**Cambio realizado en Synap:** En cada `INSERT` en `stock` se incluye **`CodViajante`** cuando el motivo es 6, 7 u 8 (Transferencia, Mov. Interno Salida, Mov. Interno Entrada), tomando `reng.get("CodViajante")` o `cabecera.get("id_vendedor")`.

---

## 5. Resumen de cambios en `core/services/administranet_stock.py`

1. **Mapa código → nombre:** Se agregó `MOTIVO_CODIGO_A_NOMBRE` y comentarios sobre paridad con VB6 (motivo_movimiento y TipoComp).
2. **Cálculo de variables por motivo:**
   - `motivo_texto`: texto del motivo para cabecera y renglones.
   - `deposito_destino`: si motivo ≠ 6, igual a `deposito_origen`; si motivo = 6, valor enviado o `deposito_origen`.
   - `tipo_mov`: motivo 10 → `"OPT"`, 11 → `"OPP"`, resto `None`.
3. **INSERT `movimiento_stock`:** Se usa `motivo_texto` en `motivo_movimiento`, `deposito_origen`/`deposito_destino` calculados, y se agrega la columna `tipo_mov`.
4. **INSERT `stock`:** Se agregan columnas `Tipo`, `TipoComp`, `Comprobante`, `NroComprobante`, `anulado` y `CodViajante`; `CodViajante` se setea para motivos 6, 7, 8.

---

## 6. UI del formulario (Synap)

Orden de bloques en la pantalla "Ingreso Mov. Stock" (paridad con CargaMovStock):

1. **Fecha**
2. **Motivo | Depósito origen | Depósito destino** (si aplica) **| Vendedor** (para Transferencia y Mov. Interno Salida/Entrada, motivos 6, 7, 8)
3. **Cliente | Referencia** — Cliente solo visible para **Mov. Interno Salida** (7) y **Mov. Interno Entrada** (8); Referencia siempre visible
4. Operario | Máquina (solo Parte producción, motivo 12)
5. Valor variable, Pedidos, Proyecto (según motivo)
6. **Detalle**

El campo **Cliente** se alimenta con la lista de clientes de AdministraNET (tabla `cliente`); se persiste en `movimiento_stock.id_cliente` al confirmar.

### 6.1 Entrada/Salida (E/S) por renglón según motivo

En AdministraNET (CargaMovStock) el campo **Entrada/Salida** por artículo se comporta así:

- **Siempre Entrada (campo deshabilitado):** Stock Inicial (1), Sobrante (4), Mov. Interno Entrada (8).
- **Siempre Salida (campo deshabilitado):** Faltante (3), Rotura (5), Transferencia (6), Mov. Interno Salida (7), Parte producción (12).
- **Editable:** Solo **Ajuste** (2); el usuario puede elegir Entrada o Salida.

En Synap está migrado: getters `esEntradaFija`, `esSalidaFija`, `puedeCambiarES` y `getDefaultES()`; al cambiar el motivo se llama `setDefaultESDesdeMotivo()`. El desplegable E/S en el bloque "Agregar artículo" y en la edición de renglón se deshabilita cuando el motivo fija E/S, con tooltip "Según motivo del movimiento". Al guardar un renglón editado, si el motivo no es Ajuste se envía el valor fijo (getDefaultES()).

---

## 7. Campos no migrados (solo VB6)

- **Lote por renglón** (`id_lote`, `stock_lote_deposito`, `cod_lote`, `vto_lote`): lógica completa de lotes en CargaMovStock no migrada.
- **Series** (`serie`, `desc_serie`, etc.): no migrado.
- **OPT/OPP** (`codigo_mov_ped_opt`, `id_en_abm`, `lista_produccion_*`, `stockp`): para motivos 10/11 solo se setea `tipo_mov` en cabecera; el resto de la lógica de producción no está replicada en Synap.

---

## 8. Referencias en código VB6

- **Cabecera motivo y deposito_destino:** CargaMovStock.frm aprox. 4330–4340.
- **id_cliente / id_vendedor / tipo_mov:** CargaMovStock.frm aprox. 4367–4392.
- **stock Tipo/TipoComp/Comprobante/NroComprobante:** CargaMovStock.frm aprox. 4032–4036, 4289–4293.
- **CodViajante en renglón:** CargaMovStock.frm 3800, 4217; asignación en CuerpoStock 5058–5062 (motivos 5, 6, 7).

---

*Documento generado a partir del análisis de CargaMovStock.frm y de los cambios aplicados en `core/services/administranet_stock.py` para paridad con AdministraNET.*
