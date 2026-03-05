# Configuración MercadoPago · Datos para UX/UI

Referencia según [Mercado Pago Developers – Credentials](https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/additional-content/credentials) y uso en Synap (Self Checkout + administraNET).

---

## Credenciales API

| Campo en Synap | Nombre en MP | Uso | Dónde obtenerlo |
|----------------|--------------|-----|------------------|
| **Access Token** | Access Token | Backend: crear preferencias, consultar pagos, webhooks. **No exponer en frontend.** | [Tus integraciones](https://www.mercadopago.com.ar/developers/panel/app) → tu aplicación → **Pruebas** o **Producción** → **Credenciales** → Access Token |
| **Public Key** | Public Key | Frontend (opcional): métodos de pago, encriptar tarjeta. En Synap se usa sobre todo el Access Token en backend. | Mismo panel → Public Key |

- **Pruebas (test)**: credenciales de prueba; no generan cobros reales.
- **Producción**: credenciales de producción; cobros reales.

En Synap el modo se controla con el campo **Sandbox** (activado = pruebas, desactivado = producción).

---

## Regla: Autoservicio ↔ SmartPoint única

- **Cada Autoservicio (kiosco)** puede estar vinculado a **un solo SmartPoint** (configuración MercadoPago).
- **Un kiosco no puede duplicarse**: no se puede dar de alta más de una vez ni estar asociado a más de una configuración.
- En la práctica: por cada `base_empresa`, el mismo `kiosk_id` no puede aparecer en dos configuraciones.

---

## Campos de configuración en Synap (`MercadoPagoConfig`)

| Campo | Tipo | Obligatorio | Descripción para la UI |
|-------|------|-------------|-------------------------|
| **Nombre** | texto | No (default: "Default") | Etiqueta de la configuración (ej: "Sucursal Centro"). |
| **Base empresa (DB)** | — | **Desde sesión** | No se pregunta en el formulario: se usa la empresa activa en la sesión del usuario. |
| **Kiosco (Autoservicio)** | texto | No | ID del kiosco vinculado a este SmartPoint (ej: `kiosk-01`). Un kiosco solo puede estar en una configuración. |
| **Access Token** | texto (password) | **Sí** para pagos | Access Token de MercadoPago (Pruebas o Producción). No mostrar completo al editar; permitir reemplazar. |
| **Public Key** | texto | No | Public Key de MercadoPago. Opcional para el flujo actual (Checkout Pro vía backend). |
| **Sandbox** | sí/no | No (default: sí) | Si está activado, se usan credenciales de prueba; si no, producción. |
| **ID Caja (administraNET)** | número | No | `id_caja` de `caja_abm` en la base administraNET para registrar el ingreso del pago MP en caja (opcional). |

---

## Flujo de datos

1. **Configuración** (esta pantalla): el usuario carga Access Token (y opcionalmente Public Key), elige Sandbox sí/no, indica Base empresa e ID Caja si aplica.
2. **Self Checkout**: al pagar con MercadoPago, el backend usa el Access Token para crear la preferencia (`POST /checkout/preferences`) y redirigir al `init_point` (o `sandbox_init_point` si Sandbox está activado).
3. **Webhook**: MP notifica al backend; se usa el mismo Access Token para consultar el pago y actualizar estado y, si está configurado, escribir en caja.

---

## Enlaces útiles

- [Credenciales (test y producción)](https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/additional-content/credentials)
- [Tus integraciones](https://www.mercadopago.com.ar/developers/panel/app)
- [Crear preferencia (API)](https://www.mercadopago.com.ar/developers/en/reference/preferences/_checkout_preferences/post)
- [Seguridad: enviar Access Token por header](https://www.mercadopago.com.ar/developers/en/docs/checkout-api/best-practices/credentials-best-practices/secure-credentials)
