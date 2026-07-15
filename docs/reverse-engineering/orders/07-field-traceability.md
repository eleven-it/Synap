# Trazabilidad de campos — UI → jCart → PHP → MySQL

**Confianza:** CONFIRMADO salvo marcado INFERIDO

---

## 1. Cabecera `comp_ped`

| # | UI / origen | jCart / POST | PHP variable | MySQL `comp_ped` |
|---|-------------|--------------|--------------|------------------|
| 1 | — | — | `date('Y/m/d')` | `Fecha` |
| 2 | — | — | literal | `Tipocomprobante='PED'` |
| 3 | — | talonario | `$numeroPedido` | `NroComprobante` |
| 4 | — | talonario | `$nroCompBusqPedido` | `NroCompBusq` |
| 5 | Sesión cliente | — | `$clienteObj->Codigo` | `Codigo` |
| 6 | Sesión cliente | — | `$clienteObj->id_sucursal` | `CodSucursal` |
| 7 | Sesión | — | `$_SESSION['idusuario']` | `IdUsuario` |
| 8 | Sesión vendedor | — | `$idPuntoVenta` | `id_pv` |
| 9 | OC + detalle carrito | `jcart-orden-compra`, `jcart-detalle` | `$detalle` | `Detalle` |
| 10 | Totales carrito | — | `$pedidoArr['subtotal']` | `ImporteVenta` |
| 11 | — | — | `num2letras(...)` | `ImporteVentaL` |
| 12 | — | `muestra_pedido()` | `subtotalIva21` | `Iva1` |
| 13 | — | idem | `subtotalIva105` | `Iva2` |
| 14 | — | idem | literals | `Alicuota1='21'`, `Alicuota2='10.5'` |
| 15 | — | idem | `subtotalExento` | `Exento`, `exento_interes` |
| 16 | — | — | literal | `anulado='No'` |
| 17 | — | idem | `subtotalNetoIva21` | `Subtotal1` |
| 18 | — | idem | `subtotalNetoIva105` | `Subtotal2` |
| 19 | — | idem | suma netos | `SubtotalGral` |
| 20 | — | idem | `porDescPie` | `PorDesc1`, `PorDesc2` |
| 21 | — | idem | `importeDesc21/105` | `ImpDesc1`, `ImpDesc2` |
| 22 | — | idem | `subtotalDesc*` | `SubTotalDesc1/2`, `SubtotalDesc` |
| 23 | Sesión cliente | — | `condVenta`, `id_cv` | `CondVenta`, `id_condventa` |
| 24 | — | — | `$codMov` | `CodigoMovimiento` |
| 25 | — | — | literal | `Estado='Pendiente'` |
| 26 | — | — | `+1 mes` | `Vencimiento` |
| 27 | Sesión | — | `$codViajante` | `CodViajante` |
| 28 | — | — | `$tipoPedido` | `TipoPedido` |
| 29 | — | idem | `subtotalImpInt` | `impuesto_interno_total`, `impuesto_interno_interes` |
| 30 | Crédito cliente | — | `$autorizaPedido` | `autorizacion_sistema` |
| 31 | Forma entrega | `formaEntrega` | POST | `formaentrega` |
| 32 | — | — | `date('d/m/Y H:i')` | `fecha_control` |
| 33 | Sesión depósito | — | `$_SESSION['deposito']` | `id_deposito_despacho` |
| 34 | — | — | `$fechaEntregaH` | `FechaEntrega` |
| 35 | — | idem | `percepcionesT` | `total_percep` |
| 36 | cotización | — | `$cotiDolar` | `CotiDolar` |
| 37 | GPS sesión | — | `$geo_lat`, `$geo_long` | `geo_latitud`, `geo_longitud` |
| 38 | Listado | SELECT | — | `autorizacion_web` (**no trace alta**) |

---

## 2. `cliente_datos_adicionales`

| UI | POST | PHP | MySQL |
|----|------|-----|-------|
| Fecha entrega calculada | — | `$fechaEntrega` | `fechaEntrega` |
| Depósito sesión | — | `$_SESSION['deposito']` | `id_deposito_despacho` |
| Forma entrega | `formaEntrega` | POST | `Fentrega` |
| — | — | `'Web'` | `origen_pedido` |
| — | — | `'PED'` | `TipoComprobante` |
| Cliente | — | `$clienteObj->Codigo` | `id_cliente` |
| — | — | `$codMov` | `CodigoMovimiento` |
| Domicilio | `domicilio_entrega` | explode `\|` | `id_cliente_domicilio` |
| Ruta logística | `hoja_ruta` | POST | `id_ruta` |

---

## 3. Renglón `stockp` (por ítem jCart)

| jCart key | Transformación PHP | `stockp` |
|-----------|-------------------|----------|
| `id` | `str_replace('p','',id)` | `IDArt` |
| `qty` | directo | base cantidad |
| `cantidadMinimaContada` | directo | `Cantidad`, `Salida`, `cantidad_*` |
| `neto` | descuentos | `PrecioNetoxU`, `PrecioVentaxU` |
| `netoN`, `impIva` | suma | `PrecioBrutoxU` |
| `subtotalNeto`, `subtotalIva` | × cantidades | `PrecioNetoxR`, `PrecioIVAxR`, `PrecioBrutoxR` |
| `iva`, `alicuota`, `tipoIva` | directo | `Alicuota`, `imp_alicuota_iva`, `TipoIVA` |
| `descPor` / promo | lógica promo | `PorDesc`, `ImpDesc`, `promocion*` |
| `comoCuento` | Unidad/Display/Bulto | `tipo_unidad` |
| `cantidadUnidadDisplay`, `divisorCantidad` | directo | `cantidad_unidad_display`, `cantidad_dividir` |
| `url` | peso artículo | `detalle`, `unidad_art_peso` |
| artículo DB | JOIN query | `CodigoArticulo`, `Descripcion`, `CodLaboratorio`, etc. |
| costo | `calculaPrecioCostoUnidad` | `PrecioCostoxU/R` |
| — | `$codMov` | `CodigoMovimiento` |
| sesión | `deposito` | `CodDeposito` |
| — | `$numeroPedido` | `NroComprobante` |
| cliente | `Codigo` | `CodigoCP` |
| — | `'No'` | `anulado` |

---

## 4. `stock_deposito`

| jCart | PHP | MySQL |
|-------|-----|-------|
| `qty` | `$saldoArt += $articulo['qty']` | `saldo_pedido_cliente` |
| sesión `deposito` | `$idDeposito` | `id_deposito` |
| `id` artículo | `$idArt` | `id_articulo` |

---

## 5. `percep_cli`

| Origen | MySQL |
|--------|-------|
| `pedidoArr['percepciones']['detalle'][*]['id']` | `id_percep_cli_tipo` |
| `['alic']` | `alicuota_percep_cli` |
| `['monto']` | `importe_percep_cli` |
| `$codMov` | `codigo_movimiento` |
| cliente | `id_cliente` |
| literal | `tipo_comp='PED'` |

---

## 6. Trazabilidad inversa (consulta → UI)

| MySQL campo | Listado columna | Detalle modal |
|-------------|-----------------|---------------|
| `NroComprobante` | N° Comprob. | Título |
| `TipoPedido` | Tipo | INFERIDO |
| `autorizacion_sistema` | Autorizado | INFERIDO |
| `Estado` | Estado (color) | INFERIDO |
| `stockp.*` | — | Renglones `ver_pedido` |

---

## 7. Campos huérfanos (NO VERIFICADO en eCom)

Campos de `comp_ped` usados en VB6 pero no escritos en alta eCom PHP:

- `autorizacion_web`
- Campos de workflow preparación (`id_usuario_preparacion`, etc.) — INFERIDO
