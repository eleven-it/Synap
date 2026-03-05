# Mapeo de templates Stitch a Django (self_checkout)

Documentación para el refactor de los 23 templates HTML exportados de Stitch a estructura Django (base + extends + includes), con detección mobile y responsive 100%.

---

## 1. Inventario de templates Stitch

### Desktop (12 pantallas)

| Archivo Stitch | Función | Mapeo a sección kiosco |
|----------------|---------|------------------------|
| `administranet_pantalla_de_inicio_bienvenidos_1` | Inicio con ofertas del día (CTA "Toca aquí para comenzar") | Pantalla inicio / bienvenida (opcional) |
| `administranet_pantalla_de_inicio_bienvenidos_2` | Variante de bienvenida | Pantalla inicio (variante) |
| `administranet_kiosk_empty_state` | Carrito vacío: escáner + buscador + CTA asistencia/cancelar | Header + _search_scan + _cart_list (vacío) |
| `administranet_kiosk_active_cart_1` | Carrito con oferta: scan + lista + totales + "Pagar ahora" | Header + _search_scan + _cart_list + _cart_totals + _payment_keypad |
| `administranet_kiosk_active_cart_2` | Variante carrito con ítems | _cart_list + _cart_totals |
| `administranet_selecci_n_m_todo_de_pago` | Selección método de pago + resumen | _payment_keypad / modal pago |
| `administranet_pago_con_qr_mercado_pago` | Pantalla pago con QR (Mercado Pago) | Pantalla pago (estado paying) |
| `administranet_pago_exitoso_y_ticket_digital` | Post-venta: éxito + opciones ticket | _post_sale |
| `administranet_enviar_ticket_digital` | Modal/envío ticket por email | _modal_email / opciones ticket |
| `administranet_confirmaci_n_de_env_o_exitoso` | Confirmación envío exitoso | Post-venta (feedback) |
| `administranet_b_squeda_de_cliente_modal` | Modal búsqueda cliente (nombre, DNI, RUC) | _modal_cliente |
| `administranet_selecci_n_de_vendedor_modal` | Modal selección vendedor | _modal_vendedor |
| `administranet_registro_nuevo_cliente` | Formulario registro nuevo cliente | Modal/pantalla registro cliente |

### Mobile (11 pantallas)

| Archivo Stitch | Función | Mapeo a sección kiosco |
|----------------|---------|------------------------|
| `administranet_login_es` | Login (email/contraseña) | Pantalla login (si se usa) |
| `administranet_pos_checkout` | POS checkout: búsqueda, carrito, total, CTA pago | Header + _search_scan + _cart_list + _cart_totals (mobile) |
| `administranet_venta_exitosa_es_1` | Post-venta: monto + "Enviar Ticket Digital" | _post_sale (mobile) |
| `administranet_venta_exitosa_es_2` | Historial de tickets recientes | _post_sale variante |
| `administranet_pago_con_qr_es` | Pago con QR (mobile) | Pantalla pago (mobile) |
| `administranet_payment_methods_selection` | Selección método de pago mobile | _payment_keypad (mobile) |
| `administranet_cierre_de_caja_es_1` | Cierre de caja: conteo efectivo (`id="cash-counted"`) | Pantalla cierre caja (admin) |
| `administranet_cierre_de_caja_es_2` | Resumen cierre (gráficos/totales) | Pantalla cierre caja resumen |
| `administranet_gesti_n_de_inventario_es` | Gestión de inventario | Pantalla inventario (admin) |
| `administranet_ajustes_es` | Ajustes del kiosco | Pantalla ajustes |

### Mapeo Desktop ↔ Mobile por include

| Include | Stitch Desktop | Stitch Mobile |
|---------|----------------|---------------|
| _header_kiosk | kiosk_empty_state / kiosk_active_cart_1 (header) | pos_checkout (header) |
| _context_bar_tpv | kiosk_active_cart_1 (barra Cliente/Lista/Vendedor) | pos_checkout (selects vendedor/cliente) |
| _search_scan | kiosk_empty_state / kiosk_active_cart_1 | pos_checkout (input búsqueda) |
| _cart_list | kiosk_active_cart_1 / kiosk_active_cart_2 | pos_checkout (lista carrito) |
| _cart_totals | kiosk_active_cart_1 | pos_checkout (totales abajo) |
| _payment_keypad | selecci_n_m_todo_de_pago | payment_methods_selection |
| _post_sale | pago_exitoso_y_ticket_digital | venta_exitosa_es_1 / venta_exitosa_es_2 |
| _modal_cliente | b_squeda_de_cliente_modal | (mismo markup responsive) |
| _modal_vendedor | selecci_n_de_vendedor_modal | (mismo markup responsive) |
| _modal_email | enviar_ticket_digital | (mismo markup responsive) |

---

## 2. Contrato con el JavaScript existente (no modificar)

El comportamiento actual vive en `self_checkout/templates/self_checkout/kiosco.html` con Alpine.js `x-data="kioscoApp()"`. Los siguientes identificadores y atributos son **contrato obligatorio** y deben conservarse en el HTML final en cada include:

| Contrato | Uso |
|----------|-----|
| `x-ref="scanInput"` | Input escáner; focus y agregar por código |
| `id="tpv-busqueda-producto"` | Búsqueda predictiva TPV; teclado (↑↓ Enter) |
| `x-ref="busquedaDropdownList"` | Contenedor lista resultados búsqueda |
| `:data-search-index="index"` (en cada `<tr>`) | Selección por teclado en tabla búsqueda |
| `x-ref="descuentoInput"` | Descuento por ítem |
| `x-ref="descuentoPieInput"` | Descuento global al carrito |
| `x-ref="emailInputFa"` / `x-ref="emailInputCf"` | Inputs email en modales (Factura A / Consumidor Final) |
| Estructura de modales (x-show, variables Alpine) | modalSeries, modalTpvCliente, modalListaPrecio, modalVendedor, modalVouchers, modalCuentaCorriente, modalEmail, pantalla pago, post-venta |

**Regla:** Cualquier include que reemplace una sección de `kiosco.html` debe preservar o reinyectar estos refs/IDs/data-attributes en los nodos que Alpine y el flujo actual esperan. Si el diseño Stitch no trae esos atributos, se añaden en el include sin cambiar nombres.

---

## 3. Ubicación de archivos Stitch en el repo

- **Desktop:** `self_checkout/Templates Stitch/Desktop/<nombre_carpeta>/code.html`
- **Mobile:** `self_checkout/Templates Stitch/Mobile/<nombre_carpeta>/code.html`

No hay assets locales (imágenes/CSS/JS) dentro de Stitch; las imágenes son URLs externas. Tailwind y fuentes se cargan por CDN en cada code.html.
