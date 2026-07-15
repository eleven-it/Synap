# Mapeo UI ↔ campos — Alta y listado pedidos (AS-IS)

**Pantallas:** `alta_pedido.php` (jCart) + `lista-pedidos-vendedor.php`  
**Confianza:** CONFIRMADO (código fuente)

---

## 1. Carrito / checkout (`jcart` display)

| Etiqueta UI | Control HTML / name | Destino persistencia | Tabla.campo | Confianza |
|-------------|---------------------|----------------------|-------------|-----------|
| Productos / búsqueda | `#nombreBuscaRapido` | — (solo consulta) | — | CONFIRMADO |
| Categoría / Rubro / Marca | `#buscaCategoria`, `#buscaRubro` | — | — | CONFIRMADO |
| Promociones | `#buscaPromo` | Flag búsqueda | — | CONFIRMADO |
| Mis consumos | `#buscaMisConsumos` | Flag búsqueda | — | CONFIRMADO |
| Cantidad ítem | `my-item-qty` / qty carrito | `stockp.Cantidad`, `Salida` | stockp | CONFIRMADO |
| Unidad (Unidad/Display/Bulto) | `my-item-como-cuento` | `stockp.tipo_unidad` | stockp | CONFIRMADO |
| Forma de entrega | `formaEntrega` (select POST) | `comp_ped.formaentrega`, `cliente_datos_adicionales.Fentrega` | ambas | CONFIRMADO |
| Domicilio entrega | `domicilio_entrega` (`id\|texto`) | `cliente_datos_adicionales.id_cliente_domicilio` | cda | CONFIRMADO |
| Hoja de ruta | `hoja_ruta` (si logística) | `cliente_datos_adicionales.id_ruta` | cda | CONFIRMADO |
| Orden de compra | `jcart-orden-compra` | Prefijo en `comp_ped.Detalle` | comp_ped | CONFIRMADO |
| Detalle / observaciones | `jcart-detalle` | `comp_ped.Detalle` | comp_ped | CONFIRMADO |
| Descuento al pie | `jcart-desc-pie` (si permiso) | Totales vía `muestra_pedido()` | comp_ped | CONFIRMADO |
| Punto de venta | Sesión `vendedor.id_punto_venta` | `comp_ped.id_pv`, talonario | comp_ped | CONFIRMADO |
| Depósito | Sesión `deposito` | `stockp.CodDeposito`, `id_deposito_despacho` | varias | CONFIRMADO |

---

## 2. Campos calculados (solo lectura en UI carrito)

| Etiqueta UI | Origen jCart | Destino DB |
|-------------|--------------|------------|
| Subtotal | `muestra_pedido()['subtotal']` | `comp_ped.ImporteVenta` |
| IVA 21 % | `subtotalIva21` | `comp_ped.Iva1` |
| IVA 10,5 % | `subtotalIva105` | `comp_ped.Iva2` |
| Exento | `subtotalExento` | `comp_ped.Exento` |
| Imp. interno | `subtotalImpInt` | `comp_ped.impuesto_interno_total` |
| Percepciones | `percepcionesT` | `comp_ped.total_percep` |
| Total ítems badge | `totalCarrito()` | — (sesión) |

---

## 3. Listado `lista-pedidos-vendedor.php`

| Columna UI | Campo SQL | Notas |
|------------|-----------|-------|
| Fecha | `DATE_FORMAT(Fecha,'%d/%m/%Y')` | CONFIRMADO |
| N° Comprob. | `NroComprobante` | CONFIRMADO |
| Cliente | `nombre_cliente` + `Codigo` / `id_manual_cli` | CONFIRMADO |
| Cond. Vta | `CondVenta` | CONFIRMADO |
| SubTotal | `SubTotalDesc` | CONFIRMADO |
| IVA | `IVA1+IVA2` calculado | CONFIRMADO |
| Total | `SubTotalDesc+IVA` | CONFIRMADO |
| Tipo | `TipoPedido` | Valores: `Ecom vendedor`, `Web cliente`, legacy `Sistema`, `Web` |
| Estado | `Estado` | Colores por switch PHP | CONFIRMADO |
| Autorizado | `autorizacion_sistema` | CONFIRMADO |
| Entrega | `FechaEntrega` + `FormaEntrega` | CONFIRMADO |
| Anul. | `Anulado` | CONFIRMADO |
| Acción Ver | `.verComprobante` → AJAX | CONFIRMADO |

---

## 4. Filtros listado (relay-pedidos)

| Filtro UI | Request param | SQL |
|-----------|---------------|-----|
| Buscar por Fecha | `campoBusca=Fecha` | `BETWEEN fechaDesde/Hasta` | CONFIRMADO |
| Buscar por Número | `NroComprobante` | `LIKE numeroComp` | CONFIRMADO |
| Tipo pedido | `tipoPedido` | `TipoPedido='{valor}'` | CONFIRMADO |
| Estado | `estadoPedido` | `Estado='{valor}'` | INFERIDO |
| Lista cliente | `listaPed=cliente` | `Codigo=idcliente sesión` | CONFIRMADO |

### Desalineación filtro Tipo (CONFIRMADO)

| Opción UI | value HTML | Valor real en DB (alta eCom actual) |
|-----------|------------|-------------------------------------|
| Web Vendedor | `Web` | **`Ecom vendedor`** |
| Web Cliente | `Web cliente` | `Web cliente` ✅ |
| Sistema | `Sistema` | Pedidos VB6/desktop |

---

## 5. Campos sesión → cabecera (sin control UI directo)

| Dato | Sesión / objeto | `comp_ped` |
|------|-----------------|------------|
| Cliente | `cliente.Codigo` | `Codigo` |
| Sucursal cliente | `cliente.id_sucursal` | `CodSucursal` |
| Viajante | `vendedor.CodViajante` o cliente | `CodViajante` |
| Condición venta | `cliente.condVenta` | `CondVenta`, `id_condventa` |
| Usuario | `idusuario` | `IdUsuario` |
| Geolocalización | `latitud/longitud` | `geo_latitud`, `geo_longitud` |
| Cotización USD | `cotizacion id=1` | `CotiDolar` |

---

## 6. Campos leídos pero no escritos en alta eCom

| Campo | Lectura | Escritura alta |
|-------|---------|----------------|
| `autorizacion_web` | Listado SELECT | ❌ NO |
| `autorizacion_sistema` | Listado | ✅ INSERT |

---

## 7. Mapeo renglón artículo → `stockp` (resumen)

| jCart item key | stockp campo |
|----------------|--------------|
| `id` (sin prefijo p) | `IDArt` |
| `qty` / `cantidadMinimaContada` | `Cantidad`, `Salida`, `cantidad_entregada`, `cantidad_pendiente` |
| `neto`, `subtotalNeto` | `PrecioNetoxU/R` |
| `impIva`, `subtotalIva` | `PrecioIVAxU/R` |
| `iva`, `alicuota` | `Alicuota`, `imp_alicuota_iva` |
| `descPor` / promo | `PorDesc`, `ImpDesc`, `promocion*` |
| `comoCuento` | `tipo_unidad` |
| `url` (peso) | `detalle`, `unidad_art_peso` |

Detalle completo en `07-field-traceability.md`.
