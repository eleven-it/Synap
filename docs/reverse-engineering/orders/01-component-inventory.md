# Inventario de componentes — ABM Pedidos eCom (AS-IS)

**Fuente:** `administraNET-ecom/`  
**Convención de confianza:** CONFIRMADO | INFERIDO | NO VERIFICADO

---

## 1. Pantallas PHP (entrada / salida)

| Archivo | Rol | Actor | Confianza |
|---------|-----|-------|-----------|
| `listado-clientes.php` | Selección de cliente previa al pedido | Vendedor | CONFIRMADO |
| `alta_pedido.php` | Pantalla principal alta: búsqueda productos + carrito jCart | Vendedor / Cliente | CONFIRMADO |
| `alta_pedido_resumen.php` | Resumen intermedio (móvil) | Cliente | INFERIDO |
| `alta_pedido_confirmado.php` | Commit transaccional del pedido | Vendedor | CONFIRMADO |
| `alta_pedido_confirmado_cliente.php` | Commit transaccional + confirmación POST `confOperacion` | Cliente | CONFIRMADO |
| `lista-pedidos-vendedor.php` | Listado grilla vendedor (últimos 60) | Vendedor | CONFIRMADO |
| `lista-pedidos-total.php` | Listado gerencial (todos_clientes) | Gerencia | CONFIRMADO |
| `ver_pedido.php` | Detalle modal AJAX (desktop) | Ambos | CONFIRMADO |
| `ver_pedido-movil.php` | Detalle modal AJAX (móvil) | Ambos | CONFIRMADO |
| `fin-comprobante.php` | Pantalla envío mail post-comprobante | Vendedor | CONFIRMADO |
| `relay-comprobante-a-mail.php` | Relay a `fin-comprobante` con params base64 | Sistema | CONFIRMADO |

**Ausentes (CONFIRMADO):** `mod_pedido.php`, `editar_pedido.php`, `baja_pedido.php` con UI.

---

## 2. Endpoints AJAX / Relay

| Archivo | Método | Función pedidos |
|---------|--------|-----------------|
| `ajax-articulos.php` | POST/AJAX | Catálogo, precios, stock para carrito |
| `ajax-pedido-lista.php` | POST | Variante listado (legacy) | INFERIDO |
| `relay-pedidos.php` | POST `ajax=true` | Filtros avanzados listado vendedor | CONFIRMADO |
| `ajax-comprobante.php` | GET/POST `tipoComp=PED` | Anulación pedido | CONFIRMADO |
| `jcart/jcart.php` | POST acciones carrito | add/update/remove/checkout | CONFIRMADO |

---

## 3. Motor de carrito (jCart)

| Archivo | Responsabilidad |
|---------|-----------------|
| `jcart/jcart.php` | Clase principal: items, `update_subtotal()`, `muestra_pedido()`, `display_carrito_pedido_*` |
| `jcart/config.php` | Config checkout path → `alta_pedido_confirmado.php` |
| `jcart/numero_a_letra.php` | `ImporteVentaL` en `comp_ped` |
| `tmobile/jcart/*` | Variante móvil (paridad funcional) | INFERIDO |

---

## 4. JavaScript

| Archivo | Uso en pedidos |
|---------|----------------|
| `_scripts/carrito.js` | Validación stock cliente-side, unidad/display/bulto |
| `_scripts/jcart.js` | Acciones carrito (comentado parcialmente) |
| `_scripts/busqueda-rapida.js` | Búsqueda productos en `alta_pedido.php` |
| `lista-pedidos-vendedor.php` (inline) | DataTables, AJAX `ver_pedido`, filtros `relay-pedidos` |

**Validación stock (CONFIRMADO):** `carrito.js` L500-513 compara `cantidadMinimaContada` vs `saldoP`; respeta `permiso-sin-stock`.

---

## 5. Includes / sesión

| Archivo | Rol |
|---------|-----|
| `sesion.inc.php` | Sesión, `$objVendedor`, `$arrCliente`, flags empresa |
| `conexion-vendedor-empresa.inc.php` | Conexión MySQL por empresa |
| `header-vendedor.inc.php` / `header-cliente.inc.php` | Barra navegación |
| `_scripts/php/funciones.php` | `calculaPrecioCostoUnidad`, mail, PDF helpers |

---

## 6. Variables de sesión relevantes (CONFIRMADO)

| Variable sesión | Uso en pedido |
|-----------------|---------------|
| `$_SESSION['cliente']` | Cliente activo (objeto o array) |
| `$_SESSION['vendedor']` | Datos vendedor (`CodViajante`, `id_punto_venta`) |
| `$_SESSION['tipousuario']` | `vendedor` \| `cliente` — bifurca confirmación |
| `$_SESSION['deposito']` | Depósito despacho / `stock_deposito` |
| `$_SESSION['jcart']` / `$jcart` | Carrito en sesión |
| `$_SESSION['todos_clientes']` | Filtro listado gerencial |
| `$_SESSION['activ_logistica']` | Muestra hoja de ruta |
| `$_SESSION['utiliza_bulto_cerrado']` | Unidad display/bulto |
| `$_SESSION['agente_percep']` | Cálculo percepciones en jCart |
| `$_SESSION['cant_dias_entrega']` | Fecha entrega calculada |
| `$_SESSION['arr_dias_no_laborables']` | Ajuste fecha entrega |

---

## 7. Tablas MySQL tocadas (resumen)

Ver detalle en `05-data-model.md` y `06-persistence-matrix.md`.

`codmov`, `talonarios`, `cliente_datos_adicionales`, `percep_cli`, `comp_ped`, `stockp`, `stock_deposito`, `articulo`, `articulo_prov`, `cotizacion`, `percep_cli_param`, `percep_cli_tipo`.

---

## 8. Componentes Synap equivalentes (referencia TO-BE)

| PHP legacy | Synap |
|------------|-------|
| `alta_pedido.php` | `ecom/templates/ecom/compra_mayorista.html` + `/venta/` |
| `alta_pedido_confirmado.php` | `ecom/services/mayorista_checkout_service.py` |
| `lista-pedidos-vendedor.php` | `pedidos_vendedor.html` + API v1 |
| `ajax-comprobante.php` | `anular_pedido_relay` |
| `jcart/jcart.php` | `mayorista_cart_service` + Postgres `EcomCart` |

---

## 9. Componentes explícitamente fuera de alcance eCom PHP

| Componente | Motivo |
|------------|--------|
| VB6 `Pedido_prep.frm` | Cambia `Estado` post-alta |
| VB6 `Remito.frm` / facturación | `rem_ped`, `ped_fact` |
| Synap MPR / reports | Solo referencia en matriz §14 |
