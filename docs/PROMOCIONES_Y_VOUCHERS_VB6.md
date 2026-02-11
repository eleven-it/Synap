# Análisis: Promociones y Vouchers en administraNET VB6

Documento extraído del análisis del código VB6 (Formularios y Modulos) para entender la funcionalidad completa de promociones y vouchers y su uso en TPV, Factura A/B y Programa de Descuentos.

---

## 1. Promociones por artículo (tabla `articulo`)

### 1.1 Campos en `articulo`

La promoción se define **por artículo** y **por lista de precio**:

| Campo | Descripción |
|-------|-------------|
| `promocion` | 'Si' / 'No' — si el artículo tiene promoción activa |
| `promocion_por` | Porcentaje de descuento o monto fijo según tipo |
| `promocion_tipo` | Tipo de promoción (ver abajo) |
| `promocion_cant` | Cantidad mínima (para tipos Cantidad / Cantidad - Unidad) |
| `promocion_vigencia_desde` | Fecha desde |
| `promocion_vigencia_hasta` | Fecha hasta |
| `promocion_listaoficial` | 'Si'/'No' — aplica a Lista Oficial (id_lista=0) |
| `promocion_lista1` … `promocion_lista5` | 'Si'/'No' — aplica a Lista 1 … Lista 5 |

### 1.2 Lógica de vigencia (Funciones.bas)

- **Obtener_Promo_Articulo(id_articulo, Lista_Precio)**  
  - Lee `articulo` y comprueba que para la **lista** indicada (0…5) el flag correspondiente sea 'Si'.  
  - Comprueba que `promocion = 'Si'` y que **Principal.Fecha** esté entre `promocion_vigencia_desde` y `promocion_vigencia_hasta`.  
  - Devuelve True/False.

- **Obtener_Promo_Articulo_Datos(id_articulo, Lista_Precio, tipo_dato)**  
  - Misma vigencia y lista.  
  - Devuelve según `tipo_dato`: `promocion_tipo`, `promocion_por` o `promocion_cant`.

### 1.3 Tipos de promoción (`promocion_tipo`)

| Tipo | Uso |
|------|-----|
| **Monto fijo** | Precio final del ítem = valor en `promocion_por` (precio fijo promocional). No se usa % descuento. |
| **Importe descuento** | Descuento por renglón: `promocion_por` es el **porcentaje** de descuento. Se calcula ImpDescRenglon y se aplica al neto. |
| **Cantidad** | Descuento % (`promocion_por`) si la cantidad comprada es >= `promocion_cant` (ej. “20% comprando 6 o más”). Opción 2x1 según `Principal.cantidad2x1_desc_cant`. |
| **Cantidad - Unidad** | Variante por unidad; el renglón no se puede editar en TPV_Modifica_Renglon. |
| **Cantidad - Intervalo** | Similar a Cantidad con intervalo (TPV_Modifica_Renglon muestra promocion_por, promocion_cant). |

En TPV, al **agregar** un artículo al renglón (desde grilla/búsqueda), se consulta el artículo y si aplica promoción para la lista actual se rellenan en **data_renglon_tpv** (y luego en **stock**):

- `promocion` = 'Si'/'No'
- `promocion_por`, `promocion_tipo`, `promocion_cant`

El precio/descuento del renglón se calcula según el tipo (monto fijo, % descuento, o regla por cantidad).

---

## 2. Programa de descuentos (PD) — Puntos y canje

### 2.1 Activación

- **Principal.mod_pd** = 'Si' — módulo de programa de descuentos activo.  
- **Principal.activ_pd** = 'Si' — programa activado.

### 2.2 Flujo en facturación (TPV, FacturaA, FacturaB)

Después de confirmar la venta:

1. **Actualiza_Puntos_PD**(contador, id_cliente, TipoFactura, NroComp, SubtotalDesc, ImporteTotal, Fecha)  
   - Actualiza puntos/saldo del cliente según el comprobante (acumulación por venta).  
   - Retorna array con datos (ej. saldo); se usa para imprimir en detalle y para envío de mail.

2. **Descuenta_Canje_Puntos_PD**(contador, id_cliente, Puntos_tipo_programa_PD, Fecha, Puntos_tipo_sp_desc_PD, Puntos_ID_Descuento_PD)  
   - Si el cliente canjeó puntos por un descuento en esta venta, descuenta ese canje.  
   - Si retorna True se llama **Envia_Mail_Canje_PD**.

3. En impresión de factura: si **voucher_usado** = 'Si', se imprime algo adicional (voucher usado).

### 2.3 Formularios del programa

- **Programa_Descuentos** — Menú/lista del programa.
- **Programa_Descuentos_Carga** — Carga de “programa de descuentos, vouchers y cupones” (combo `proceso` con tipos de proceso).
- **Programa_Descuentos_Canje** — “Descuentos y voucher disponibles”: canje de puntos por descuentos.  
  - Se abre desde TPV y Factura con: `Programa_Descuentos_Canje.id_cliente`, `tipo_comprobante` ('TPV' o 'FA'), `Cliente` (caption).  
  - Grilla con: id_sp_desc, nombre programa, tipo descuento, tipo programa, % desc, puntos consumidos, desde/hasta, cod. voucher, artículo, marca, proveedor, rubro, subrubro, categoría, nro voucher seriado, anulado.
- **Programa_Descuentos_Configuracion** — Configuración del programa.
- **Programa_Descuentos_Info** — Información.

### 2.4 Tablas involucradas (por código)

- **sp_desc_programa** — Programas de descuento: `id_sp_desc`, `nro_actual_cupon`, `tipo_programa` ('Voucher', 'Cupon sorteo', 'Puntos', etc.), `tipo_voucher` ('Serie' u otro).
- **sp_cupon_cliente** — Cupones/vouchers por cliente: `id_sp_cupon`, `id_sp_desc`, `nro_voucher_serie`, `voucher_usado` ('Si'/'No'), etc.

---

## 3. Vouchers

### 3.1 Tipos de voucher en `sp_desc_programa`

- **tipo_programa** = 'Voucher' y **tipo_voucher** = 'Serie': vouchers numerados en serie.  
- **tipo_programa** = 'Cupon sorteo': cupones para sorteo.

### 3.2 Numeración e impresión

- **Guardar_sp_cupon_cliente(id_sp_desc)** (en FacturaA, TPV, FacturaB):  
  - Para “Cupon sorteo”: lee `nro_actual_cupon` de `sp_desc_programa`, incrementa y genera cupón.  
  - Para “Voucher” + “Serie”: lee `nro_actual_cupon` (como serie), incrementa, forma número tipo `"91133-" & id_sp_desc & "-" & voucher_serie_actual`, graba en `sp_cupon_cliente` (ej. `nro_voucher_serie`, `voucher_usado = 'No'`).  
  - Devuelve el código/cupón actual.

- Al **usar** un voucher en la venta:  
  - Se marca en BD: `UPDATE sp_cupon_cliente SET voucher_usado = 'Si' WHERE id_sp_cupon = ...`

- **voucher_usado** (variable en formulario): 'Si' si en esa factura se usó un voucher; en impresión se muestra mensaje o detalle de voucher usado.

### 3.3 Botón “Descuentos y voucher” en TPV

- Caption: “Descuentos y voucher:” (ToolTip: “Lista de programa de descuentos y voucher”).  
- Al hacer clic se abre **Programa_Descuentos_Canje** con el cliente y tipo comprobante 'TPV', para canjear puntos o usar vouchers disponibles.

---

## 4. Resumen por flujo

| Funcionalidad | Dónde se usa | Tablas / Origen |
|---------------|--------------|------------------|
| Promoción por artículo (vigencia, lista, tipo) | TPV, Factura A/B, Pedido, Remito, Presupuesto, Lista_Comp_Gral | `articulo`: promocion, promocion_por, promocion_tipo, promocion_cant, promocion_lista*, promocion_vigencia_* |
| Precio/descuento según tipo promo | Al agregar renglón; Obtener_Precio_Articulo / cálculo en TPV | data_renglon_tpv → stock (promocion, promocion_por, promocion_tipo, promocion_cant) |
| Programa de descuentos (puntos) | TPV, Factura A/B (después de confirmar) | Actualiza_Puntos_PD, Descuenta_Canje_Puntos_PD; Principal.mod_pd, activ_pd |
| Canje puntos / vouchers disponibles | TPV, Factura A/B (botón “Descuentos y voucher”) | Programa_Descuentos_Canje; sp_desc_programa, sp_cupon_cliente |
| Voucher seriado / cupón | Al emitir factura con canje o cupón | Guardar_sp_cupon_cliente; sp_desc_programa (tipo Voucher/Serie o Cupon sorteo), sp_cupon_cliente |
| Marcar voucher usado | Al aplicar voucher en la venta | UPDATE sp_cupon_cliente SET voucher_usado = 'Si' |
| Impresión “voucher usado” | Factura / TPV (impresión) | Variable voucher_usado = 'Si' |

---

## 5. Referencias en código VB6

- **Modulos/Funciones.bas**: `Obtener_Promo_Articulo`, `Obtener_Promo_Articulo_Datos`, `Obtener_Precio_Articulo` (aplican promoción al precio), `Actualiza_Puntos_PD`, `Descuenta_Canje_Puntos_PD`.
- **TPV.frm**: asignación de promocion/promocion_por/promocion_tipo/promocion_cant al renglón al agregar artículo; persistencia a stock; Programa de descuentos y voucher al confirmar; botón Descuentos y voucher; `Guardar_sp_cupon_cliente`.
- **FacturaA.frm / FacturaB.frm**: mismo flujo de Programa de descuentos y voucher; `Guardar_sp_cupon_cliente`; impresión si voucher_usado.
- **Lista_Comp_Gral.frm**: copia de promocion, promocion_por, promocion_tipo, promocion_cant desde stock o Data_Renglon a CuerpoStock / data_renglon_tpv (FacturaA, FacturaB, Remito, Presupuesto, Pedido, TPV).
- **Programa_Descuentos_Canje.frm**: “Descuentos y voucher disponibles”; canje de puntos por descuentos; grilla con id_sp_desc, nombre, tipo, monto_descuento, puntos, voucher, artículo, etc.
- **Programa_Descuentos_Carga.frm**: carga de programas (descuentos, vouchers, cupones).
- **ConsultaComprobante.frm**: comentarios “Programa de descuentos y voucher”; copia de promocion/promocion_por/promocion_cant/promocion_tipo desde stock a cuerpostock al consultar comprobante.
- **Articulo.frm / CargaArticulo.frm**: mantenimiento de campos de promoción en artículo.
- **Exportacion.frm**: uso de articulo.promocion y promocion_vigencia para precios ecom con descuento.

Este documento sirve como referencia para replicar o integrar promociones y vouchers en Synap / self-checkout.
