# Self-Checkout UI · Epic 7

Documentación de la interfaz del kiosco autoservicio Synap.

---

## Pantallas

| Pantalla | Descripción |
|----------|-------------|
| **Principal** | 2 columnas: Scan/Entrada (izq) y Carrito/Total/CTA (der) |
| **Email** | Modal obligatorio antes de pago |
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

- Tailwind CSS (CDN)
- Alpine.js 3.x
- Plantillas Django

---

## Sin datos sensibles

Los errores de conexión muestran únicamente `window.location.host`. Nunca se exponen usuarios, contraseñas ni tokens en la UI.
