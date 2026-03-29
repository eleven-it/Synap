# Extender self_checkout como TPV (un solo flujo, dos modos)

## Estrategia: una app, dos modos

- **No** construir un TPV separado. **Extender la aplicación self_checkout** para que pueda usarse como:
  - **Modo self-checkout** (actual): autoservicio, cliente final, medios de pago ya resueltos (ej. Mercado Pago).
  - **Modo TPV**: mismo flujo base, pero al abrir en "modo TPV" se **extienden**:
    - **Medios de pago**: además de los actuales (QR, dispositivo físico), ofrecer efectivo, tarjeta, otros según configuración.
    - **Resto de funciones**: cliente ocasional, descuentos por renglón, promociones, etc., manteniendo factura electrónica y Mercado Pago ya implementados.
- Ventaja: factura electrónica y medios de pago electrónicos (Mercado Pago) quedan resueltos una sola vez; el TPV solo amplía capacidades en el mismo código.

## Objetivos de diseño

- **Pantalla táctil**: diseño tipo Odoo (grid de productos, carrito lateral, targets grandes).
- **Imágenes de artículos**: soporte en grid de productos y en líneas del carrito.
- **Medios de pago**: ofrecerlos **solo después de finalizar la compra** (igual que hoy en self_checkout); en modo TPV, la pantalla de pago muestra **más** opciones (efectivo, tarjeta, MP, etc.).
- **Grilla del carrito**: extender cada línea para mostrar en una sola fila todos los datos del renglón (ver sección siguiente).

---

## 1. Grilla del carrito extendida (una línea = todos los datos del renglón)

Cada línea del carrito debe poder mostrar en **una sola fila** (o fila expandible) todos estos datos, como en el TPV actual:

- **Código de barra**
- **Nombre del artículo**
- **Cantidad**
- **% Alicuota** (IVA u otro)
- **Precio unitario**
- **% descuento del renglón**
- **Subtotal** (del renglón)
- **Promoción** (si aplica)
- **Detalle** (observaciones, ítem modificado, etc.)

Implementación:

- En **vista compacta** (móvil/tablet): fila resumida (nombre, cantidad, subtotal) con opción de expandir para ver el resto de columnas.
- En **vista TPV / pantalla grande**: grilla con columnas fijas para todos los campos (scroll horizontal si hace falta), táctil y legible.
- El backend/API del carrito expone por ítem: `codigo_barras`, `descripcion`, `cantidad`, `alicuota_porcentaje`, `precio_unitario`, `porcentaje_descuento`, `subtotal`, `promocion`, `detalle`.

---

## 2. Diseño táctil (estilo Odoo)

- **Layout principal**: dos zonas claras:
  - **Izquierda (~65%)**: búsqueda + **grid de productos en tiles**.
  - **Derecha (~35%)**: carrito actual (líneas del ticket) + total + **un solo botón principal**: "Finalizar compra" / "Cobrar".
- **Targets táctiles**: mínimo 44–48px; sin dependencia de hover; `touch-manipulation` en botones.
- **Navegación**: categorías (opcional); búsqueda por código o nombre siempre visible.

---

## 3. Imágenes de artículos

- **Grid de productos**: cada tile con imagen (o placeholder), nombre/código, precio; tap = añadir al carrito.
- **Carrito**: cada línea puede mostrar miniatura del artículo.
- **Backend**: artículo con campo imagen (URL); reutilizar `media/products/` si existe.

---

## 4. Flujo de pago (igual en ambos modos; en TPV más medios)

- **Pantalla principal**: sin zona de medios de pago; un único CTA: "Finalizar compra" / "Cobrar".
- **Al pulsar "Finalizar compra"**: paso opcional cliente/facturación → **pantalla/modal de pago** con total.
  - **Modo self-checkout**: QR MP, dispositivo físico.
  - **Modo TPV**: Efectivo, Tarjeta, Mercado Pago, etc., como botones grandes y táctiles; pago mixto si se desea.

---

## 5. Resumen

- **Una app**: self_checkout extendido; modo kiosk y modo TPV.
- **Factura electrónica y Mercado Pago**: reutilizados desde self_checkout.
- **Carrito**: grilla extendida (Cod. barra, Nombre, Cantidad, % Alicuota, Precio unit., % desc. renglón, Subtotal, Promoción, Detalle).
- **Pago**: siempre después de "Finalizar compra"; en modo TPV más medios.
- **UI**: táctil (estilo Odoo), imágenes en productos y en líneas del carrito.
