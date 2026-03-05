# Configuración TPV: Mercado Pago y Factura Electrónica

Resumen de **dónde** y **cómo** se configuran Mercado Pago y la Factura Electrónica AFIP para el TPV / Self-Checkout en Synap.

---

## 1. Mercado Pago

### Dónde se configura

- **Módulo:** `mercadopago` (app Django).
- **URL en Synap:** `/mercadopago/` (listado de configuraciones).  
  **Nota:** En la instalación actual la ruta puede estar deshabilitada en `django_project/urls.py` (línea comentada). Si el módulo está activo en el registro de módulos, hay que **descomentar** `path("mercadopago/", include("mercadopago.urls"))` para acceder a la configuración.
- **Menú:** En el dashboard, entrada **MercadoPago** (o **Pagos**) → **Configuraciones** (y opcionalmente **Nueva configuración**).

### Qué configurar

Cada **configuración** (`MercadoPagoConfig`) es por **base empresa** (base de datos administraNET). Campos principales:

| Campo | Descripción |
|-------|-------------|
| **Base empresa (DB)** | Se toma de la **empresa activa en la sesión** (selector en la barra superior). No se edita en el formulario. |
| **Nombre** | Etiqueta (ej: "Sucursal Centro", "Kiosco 01"). |
| **Kiosco (Autoservicio)** | ID del kiosco que usará esta configuración (ej: `kiosk-01`). **Un kiosco solo puede estar en una configuración.** |
| **Access Token** | Credencial de Mercado Pago (obligatoria para pagar). Obtenerla en [Tus integraciones](https://www.mercadopago.com.ar/developers/panel/app) → tu app → **Pruebas** o **Producción** → Credenciales → Access Token. **No exponer en el frontend.** |
| **Public Key** | Opcional; se usa sobre todo el Access Token en backend (Checkout Pro). |
| **Sandbox** | **Activado** = credenciales de prueba (no cobra real). **Desactivado** = producción. |
| **ID Caja (administraNET)** | Opcional. `id_caja` de `caja_abm` para registrar el ingreso del pago en caja (compatible con VB6). |

### Regla importante

- **Un autoservicio (kiosco)** se vincula a **una sola** configuración Mercado Pago (SmartPoint).
- No se puede usar el mismo `kiosk_id` en dos configuraciones.

### Documentación detallada

- **Credenciales y campos:** `docs/MERCADOPAGO_CONFIG_UX.md` (o `docs/self_checkout/MERCADOPAGO_CONFIG_UX.md` si existe en esa ruta).
- **Flujo de pago y diseño:** `docs/PROPUESTA_SALES_DEPRECADO_MERCADOPAGO_SELF_CHECKOUT.md` y `docs/self_checkout/PROPUESTA_SALES_DEPRECADO_MERCADOPAGO_SELF_CHECKOUT.md`.
- **README Self-Checkout:** `self_checkout/README.md` (sección configuración Mercado Pago).

---

## 2. Factura Electrónica (AFIP)

### Dónde se configura

- **Módulo:** `fe_afip` (app Django).
- **URL en Synap:** `/fe_afip/` (listado) y `/fe_afip/config/` (formulario de configuración).  
  Las rutas se cargan por **registro dinámico de módulos**: si `fe_afip` está activo, la URL es `https://<tu-dominio>/fe_afip/`.
- **Menú:** Entrada **Facturación electrónica** o **FE AFIP** (según menú configurado en el core).

### Qué configurar

Cada **configuración** (`AFIPConfig`) es por **base empresa** (una config por base administraNET). Campos principales:

| Campo | Descripción |
|-------|-------------|
| **Base empresa (DB)** | Nombre de la base de datos administraNET. Debe coincidir con la empresa activa en sesión. |
| **CUIT contribuyente** | CUIT de 11 dígitos (con o sin guiones). Puede obtenerse desde administraNET (tabla DatosEmpresa) si está cargado allí. |
| **Ruta certificado** | Ruta absoluta en el **servidor** al archivo `.crt` o `.pem` del certificado AFIP. |
| **Ruta clave privada** | Ruta absoluta al archivo `.key` o `.pem` de la clave privada. **No subir la clave a la base de datos.** |
| **Modo homologación** | **Activado** = ambiente de prueba AFIP (wsaahomo, wswhomo). **Desactivado** = producción (solo cuando esté validado). |
| **Directorio caché** | Opcional; directorio para caché de tickets WSAA (ej: `/tmp/pyafipws_cache`). |

### Requisitos previos

- Certificado y clave privada AFIP generados (proceso ARCA/AFIP). Ver `docs/CERTIFICADOS_AFIP_ARCA.md` si existe.
- En administraNET (DatosEmpresa) tener el CUIT cargado para que Synap pueda sugerirlo en la configuración.

### Documentación detallada

- **Propuesta FE y pyafipws:** `docs/PROPUESTA_FACTURA_ELECTRONICA_PYAFIPWS.md` y `docs/self_checkout/PROPUESTA_FACTURA_ELECTRONICA_PYAFIPWS.md`.
- **CAE/CAEA en Self-Checkout:** `docs/CAE_CAEA_ARCA_SELF_CHECKOUT.md` (o `.txt`).

---

## 3. Orden recomendado para el TPV

1. **Empresa activa:** En Synap, seleccionar la **empresa/sucursal** (base administraNET) con la que se va a operar el TPV.
2. **Factura electrónica:** Ir a **FE AFIP** (`/fe_afip/`), crear o editar la configuración para esa base: certificado, clave, CUIT, modo homologación/producción.
3. **Mercado Pago:** Ir a **MercadoPago** (`/mercadopago/` una vez habilitada la ruta), crear o editar la configuración para esa base: Access Token, Sandbox sí/no, opcionalmente Kiosco y ID Caja.
4. **Autoservicio:** En el selector de kiosco (pantalla de autoservicios), el kiosco debe existir y, si se usa pago con Mercado Pago, su ID debe coincidir con el campo **Kiosco** de alguna MercadoPagoConfig.

---

## 4. Si no ves el menú o la URL

- **Mercado Pago:** Comprobar en `django_project/urls.py` que la línea `path("mercadopago/", include("mercadopago.urls"))` esté **descomentada**. Ver también `core/module_registry.py` y que el módulo `mercadopago` esté entre los activos.
- **FE AFIP:** Comprobar que el módulo `fe_afip` esté activo en el registro de módulos (`core/module_manager.py` / `module_registry`). Las URLs se montan bajo `/fe_afip/` automáticamente para módulos activos.
- **Permisos:** El usuario debe tener permisos de tipo `fe_afip.view_afipconfig`, `mercadopago.view_mercadopagoconfig`, etc., según lo definido en cada app.
