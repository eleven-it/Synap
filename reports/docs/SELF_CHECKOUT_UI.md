# Self-Checkout UI · Epic 7

Documentación de la interfaz del kiosco autoservicio Synap.

---

## Referencia visual (cómo debe verse)

Layout objetivo de la pantalla principal:

- **Cabecera:** Logo + "SELF-CHECKOUT" + "Autoservicio"; a la derecha botón "Pantalla completa".
- **Panel izquierdo (más ancho):**
  - Input "Código de barras" + botón "Agregar producto".
  - Mensaje de estado con indicador verde: "Esperando que escanees tu próximo ítem...".
  - Sección "OPCIONES EXTRA": "Usar Gift Card", "Solicitar asistencia", "Cancelar compra".
- **Panel derecho:** "Tus productos" con badge de cantidad (ej. círculo azul con "1").
  - Lista de ítems: nombre, precio (tachado si aplica), cantidad con +/- y "Quitar", subtotal.
  - "* Ahorros membresía" (— si no aplica).
  - **Total** en grande.
  - **"¿Listo para pagar?"** seguido del **botón "Pagar $XXX.XX →"** con gradiente azul–índigo–púrpura, siempre visible (deshabilitado = gris con texto legible cuando el carrito está vacío; habilitado = gradiente cuando hay ítems).

El botón **Pagar** no debe depender solo de clases dinámicas (Tailwind JIT/CDN): debe verse siempre, con estilos estáticos o inline de respaldo.

---

## Pantallas

| Pantalla | Descripción |
|----------|-------------|
| **Principal** | 2 columnas: Scan/Entrada (izq) y Carrito/Total/CTA (der) |
| **Factura** | Modal: 1) Elegir Factura A o Consumidor Final; 2) CUIT+email (A) o solo email (CF). Email solo se pide si no se recupera del cliente; siempre editable. |
| **RFID Confirm** | Modal para confirmar ítems detectados (agrupar, editar cantidades) |
| **Pago** | UI de estados (pendiente/aprobado/rechazado) — stub |
| **Comprobante** | Modal post-venta con opciones impresión/email |
| **Conexión** | Modal genérico si falla el servidor (sin credenciales) |

---

## Estados (máquina simple)

| Estado | Descripción |
|--------|-------------|
| `idle` | Listo para escanear |
| `scanning` | Agregando producto |
| `rfid_review` | Modal RFID abierto |
| `cart_ready` | Carrito con ítems, puede continuar |
| `email_required` | Modal email abierto |
| `paying` | Pantalla de pago |
| `confirming` | Enviando confirmación al backend |
| `success` | Compra exitosa |
| `error` | Error genérico |

---

## Pantalla táctil y teclado

El kiosco está pensado para uso con **pantalla táctil** o **teclado físico**. Los botones e inputs usan `touch-manipulation` y alturas mínimas (`min-h-[2.75rem]` / `min-h-[3.5rem]`) para facilitar el toque.

- **Teclado virtual en pantalla**: es configurable. Por ahora se expone el flag `use_virtual_keyboard` desde la URL (`?virtual_keyboard=1`) para poder activar en el futuro un teclado virtual integrado cuando el dispositivo sea solo táctil. Si se usa teclado físico, no hace falta.

---

## Componentes UI

- **KioskHeader**: Cabecera con kiosk_id
- **ScanPanel**: Input siempre enfocado, feedback visual, botón agregar
- **CartPanel**: Lista ítems, +/- por ítem, quitar, total, CTA pago
- **RfidConfirmModal**: Ítems agrupados, editar cantidades, confirmar/cancelar
- **EmailCapture**: Input email con validación
- **PaymentStatus**: Badge estado (pendiente/aprobado/rechazado)
- **ReceiptOptionsModal**: Comprobante, opciones impresión/email (placeholder)
- **ConnectionErrorModal**: "Problemas de conexión con servidor \<host\>" — **sin usuarios ni claves**

---

## Cómo probar

1. **Acceso**: `/self-checkout/kiosco/<kiosk_id>/` (ej: `kiosk-01`)
2. **Requisitos**: Usuario autenticado, permiso `self_checkout.kiosk`, empresa con base MySQL
3. **Flujo**:
   - Escanear o ingresar código de artículo
   - Ver carrito a la derecha
   - +/- para cambiar cantidad, ✕ para quitar
   - "Continuar al pago" → modal email
   - Ingresar email válido → modal pago
   - "Simular aprobado" (stub) → confirmación → pantalla éxito
   - "Nueva compra" para reiniciar

4. **RFID simulado**: Botón "Simular RFID masivo" → modal con ítems → editar cantidades → Confirmar

5. **Stock**: Si un ítem excede DISPONIBLE, se muestra mensaje y se bloquea el pago

6. **Conexión**: Desconectar red para ver modal de error (solo muestra host, sin credenciales)

---

## Stack

- Tailwind CSS (build estático `styles.css`; CDN solo en desarrollo cuando `debug`).
- Alpine.js 3.x
- Plantillas Django

---

## Sin datos sensibles

Los errores de conexión muestran únicamente `window.location.host`. Nunca se exponen usuarios, contraseñas ni tokens en la UI.

---

## Checklist UX/UI (Refactor autoservicio)

| Criterio | Estado |
|----------|--------|
| Flujo usable sin explicación previa | ✓ |
| Total visible en todo momento (barra fija) | ✓ |
| CTA único y claro por pantalla | ✓ |
| Compatible con pantalla táctil (botones ≥ 44px) | ✓ |
| Sin dependencias nuevas | ✓ |
| Sin romper funcionalidad existente | ✓ |
| Mensaje scan: "Escaneá tu producto o apoyalo en el lector" | ✓ |
| Lista productos: nombre, cantidad, precio, subtotal, eliminar | ✓ |
| Placeholder imagen producto (📦) | ✓ |
| Confirmación explícita antes de eliminar ítem | ✓ |
| RFID: "Detectamos X productos" + Confirmar / Reintentar / Cancelar | ✓ |
| Email: "Te enviaremos tu factura por email" | ✓ |
| Validación visual email en tiempo real | ✓ |
| Pago: total + medios + mensaje confianza | ✓ |
| Success: ícono ✓ + comprobante + Imprimir / Finalizar | ✓ |
| Animación al agregar producto (pulse) | ✓ |
| Estado loading durante scan/confirm | ✓ |
