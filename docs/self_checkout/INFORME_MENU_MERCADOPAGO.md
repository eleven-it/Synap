# Informe: Menú MercadoPago · Uso y estado de cada ítem

> **Solo referencia.** La app `mercadopago` **no está instalada** en la instalación mínima actual.

Análisis del menú del módulo MercadoPago en Synap (Self Checkout) y estado real de implementación frente al diseño actual (Checkout Pro + un SmartPoint por kiosco, sin SmartPOS en Synap).

---

## Resumen ejecutivo

| Sección              | Ítems con ruta/vista | Estado                                      |
|----------------------|----------------------|---------------------------------------------|
| **Configuration**    | 2/2                  | ✅ Implementado y en uso                    |
| **Device Management**| 0/3                  | ❌ Rutas no expuestas; vistas obsoletas    |
| **Transactions**     | 0/3                  | ❌ Rutas no definidas                       |
| **Reports & Analytics** | 0/4              | ❌ Rutas no definidas                       |

Solo **Configuration** (Settings + Add Configuration) está implementado y enlazado. El resto del menú apunta a nombres de URL que no existen en `mercadopago/urls.py` o a un `admin_urls` que no está incluido en el proyecto y que, además, usa modelos antiguos (Device/Transaction) ya no alineados con el diseño actual.

---

## 1. CONFIGURATION

### 1.1 Settings (Configuración)

- **Propósito:** Listar y acceder a las configuraciones MercadoPago (SmartPoint): credenciales por base empresa y, opcionalmente, vínculo con un kiosco (Autoservicio).
- **URL en menú:** `mercadopago:config_list` → `/mercadopago/`
- **Estado:** ✅ **Implementado**
- **Detalle:** Vista `config_list`, template `config_list.html`. Muestra tabla con nombre, base empresa, kiosco (opcional), modo Sandbox/Producción, ID caja y enlace Editar. Regla aplicada: un kiosco solo puede estar en un SmartPoint.

### 1.2 Add Configuration (Nueva configuración)

- **Propósito:** Dar de alta una nueva configuración MercadoPago (Access Token, Public Key, base empresa, kiosco opcional, Sandbox, ID caja). Respeta la regla de no duplicar asociación kiosco ↔ SmartPoint.
- **URL en menú:** `mercadopago:config_create` → `/mercadopago/config/new/`
- **Estado:** ✅ **Implementado**
- **Detalle:** Vista `config_form` (pk=None), template `config_form.html`. Validación de kiosco único por base y de Access Token obligatorio al crear.

**Conclusión Configuration:** Tiene sentido y está operativo. No falta desarrollo para el flujo actual (configuración por base/kiosco + Checkout Pro).

---

## 2. DEVICE MANAGEMENT

### 2.1 SmartPOS Devices (Dispositivos SmartPOS)

- **Propósito pensado:** Listar terminales físicos MercadoPago (SmartPOS) asociados a la integración.
- **URL en menú:** `mercadopago:device_list`
- **Estado:** ❌ **Sin funcionalidad en la app actual**
- **Detalle:**
  - En `mercadopago/urls.py` **no** existe `device_list` ni `device_create` ni `device_status`. El menú enlaza a nombres que no están definidos en las URLs activas, por lo que al pulsar se produciría error (p. ej. NoReverseMatch o 404).
  - Existe un archivo `admin_urls.py` con `device_list` → `admin_views.device_list`, pero ese módulo **no** está incluido en `django_project/urls.py` (solo se incluye `mercadopago.urls`).
  - Aun si se incluyera `admin_urls`, la vista usa el modelo `MercadoPagoDevice` y templates `device_list.html` / `device_edit.html`, que corresponden al esquema antiguo (SmartPOS, dispositivos físicos). En el diseño actual no hay modelo `MercadoPagoDevice` ni gestión de dispositivos SmartPOS en Synap.
- **¿Tiene sentido hoy?** En el diseño actual (Checkout Pro en navegador, un SmartPoint por kiosco), **no**. Solo tendría sentido si más adelante se integra gestión de SmartPOS (terminales físicos) en Synap.

### 2.2 Add Device (Agregar dispositivo)

- **Propósito pensado:** Registrar / vincular un dispositivo SmartPOS.
- **URL en menú:** `mercadopago:device_create`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida en URLs activas; vista en `admin_urls` obsoleta).
- **¿Tiene sentido hoy?** **No**, mismo motivo que SmartPOS Devices.

### 2.3 Device Status (Estado de dispositivos)

- **Propósito pensado:** Ver estado operativo de dispositivos SmartPOS (online/offline, etc.).
- **URL en menú:** `mercadopago:device_status`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida; además no existe en `admin_urls`).
- **¿Tiene sentido hoy?** **No**, sin gestión de dispositivos SmartPOS.

**Conclusión Device Management:** Los ítems corresponden a un diseño anterior con SmartPOS. En la implementación actual no hay desarrollo activo ni rutas expuestas; el menú muestra opciones que fallarían al usarse. Recomendación: **ocultar o eliminar** esta sección del menú hasta que se decida integrar SmartPOS.

---

## 3. TRANSACTIONS

### 3.1 Transaction History (Historial de transacciones)

- **Propósito pensado:** Ver listado de transacciones MercadoPago (éxito, pendiente, rechazado, etc.).
- **URL en menú:** `mercadopago:transaction_list`
- **Estado:** ❌ **Sin funcionalidad en la UI**
- **Detalle:**
  - No existe en `mercadopago/urls.py`. En `admin_urls` hay `transaction_list` que usa el modelo Django `MercadoPagoTransaction`, que ya no existe en el modelo actual.
  - En el diseño actual las transacciones se guardan en la tabla MySQL `mercadopago_transaction` (por base empresa), no en un modelo Django. No hay vista en Synap que lea esa tabla y muestre historial.
- **¿Falta desarrollo?** **Sí.** Si se quiere ver historial de pagos MP en Synap, habría que añadir una vista que consulte `mercadopago_transaction` (vía MySQL por base/sesión) y una ruta tipo `mercadopago:transaction_list`. Hoy el menú solo apunta a un nombre que no existe.

### 3.2 Failed Transactions (Transacciones fallidas)

- **Propósito pensado:** Filtro o vista de transacciones fallidas/rechazadas.
- **URL en menú:** `mercadopago:transaction_failed`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida en ningún `urls.py`).
- **¿Falta desarrollo?** Sí; podría ser una pestaña o filtro dentro de una futura vista de historial (transaction_list).

### 3.3 Transaction Reports (Informes de transacciones)

- **Propósito pensado:** Informes agregados por período, método de pago, etc.
- **URL en menú:** `mercadopago:transaction_reports`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida).
- **¿Falta desarrollo?** Sí; sería una extensión natural de un futuro módulo de transacciones/reportes.

**Conclusión Transactions:** La intención (historial, fallidas, reportes) es coherente con el producto, pero **no hay desarrollo**: ni rutas ni vistas que lean `mercadopago_transaction`. El menú queda huérfano. Recomendación: **ocultar** hasta implementar al menos una vista de historial basada en la tabla MySQL, o **implementar** esa vista y luego habilitar los ítems.

---

## 4. REPORTS & ANALYTICS

### 4.1 Sales by Device (Ventas por dispositivo)

- **Propósito pensado:** Ventas desglosadas por dispositivo o punto de venta (en el modelo antiguo, por SmartPOS).
- **URL en menú:** `mercadopago:device_sales_report`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida).
- **¿Falta desarrollo?** Sí. Con el modelo actual podría ser “ventas por kiosco” usando `mercadopago_transaction` + `kiosk_id` en MySQL.

### 4.2 Payment Methods (Métodos de pago)

- **Propósito pensado:** Análisis de uso por método de pago (tarjeta, QR, etc.).
- **URL en menú:** `mercadopago:payment_methods_report`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida).
- **¿Falta desarrollo?** Sí; los datos podrían salir de `mercadopago_transaction` o del payload de MP si se guarda método de pago.

### 4.3 Device Performance (Rendimiento de dispositivos)

- **Propósito pensado:** Métricas de dispositivos (uptime, errores, etc.).
- **URL en menú:** `mercadopago:device_performance_report`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida).
- **¿Tiene sentido hoy?** Solo si se gestionan dispositivos SmartPOS; con solo Checkout Pro en kiosco tiene menos sentido.

### 4.4 Export Data (Exportar datos)

- **Propósito pensado:** Exportar datos (transacciones, reportes) a CSV/Excel.
- **URL en menú:** `mercadopago:export_data`
- **Estado:** ❌ **Sin funcionalidad** (ruta no definida).
- **¿Falta desarrollo?** Sí; sería complemento de una futura vista de transacciones/reportes.

**Conclusión Reports & Analytics:** Todos los ítems son razonables como **roadmap**, pero hoy **no hay ninguna ruta ni vista**. Recomendación: **ocultar** la sección hasta tener al menos una fuente de datos (p. ej. historial de transacciones) y una primera pantalla de reporte/exportación.

---

## 5. Botón "Go to MercadoPago Dashboard"

- **Propósito:** Enlace al panel de MercadoPago (cuenta, movimientos, devoluciones, etc.).
- **Estado:** Depende de si está en el template. Si existe, es un enlace externo; no depende de rutas Django de MercadoPago.
- **Recomendación:** Mantenerlo; mejora la UX para operar con la cuenta MP.

---

## 6. Resumen de recomendaciones

| Acción | Sección / ítem |
|--------|-----------------|
| **Mantener** | Configuration (Settings, Add Configuration). |
| **Mantener** | Botón "Go to MercadoPago Dashboard" si está en la UI. |
| **Ocultar o quitar del menú** | Toda la sección Device Management (SmartPOS) mientras no se integre gestión de dispositivos físicos. |
| **Ocultar o quitar del menú** | Transactions y Reports & Analytics hasta tener al menos: (1) vista de historial de transacciones leyendo `mercadopago_transaction`, y (2) una ruta/vista de reporte o exportación; luego se pueden reincorporar ítems de forma progresiva. |

Si se desea **evitar enlaces rotos**, lo mínimo es reducir el menú de MercadoPago a:

- **Configuration** → Settings, Add Configuration  
- (Opcional) Enlace externo a MercadoPago Dashboard  

El resto puede volver a mostrarse cuando existan las rutas y vistas correspondientes (historial desde MySQL, reportes, y, si aplica, SmartPOS).

---

## 7. Referencia técnica rápida

- **URLs activas (mercadopago/urls.py):** `config_list`, `config_create`, `config_edit`.
- **Menú (core/utils/utils.py y mercadopago/menu_config.py):** Incluye además `device_list`, `device_create`, `device_status`, `transaction_list`, `transaction_failed`, `transaction_reports`, `device_sales_report`, `payment_methods_report`, `device_performance_report`, `export_data` — **ninguno de estos está definido en las URLs activas**.
- **admin_urls.py:** Define rutas para device y transaction usando vistas que dependen de `MercadoPagoDevice` y `MercadoPagoTransaction` (modelos del esquema antiguo); no está incluido en `django_project/urls.py` y no está alineado con el modelo actual (solo `MercadoPagoConfig` + tabla MySQL `mercadopago_transaction`).

---

*Informe generado a partir del estado del código y del diseño actual: MercadoPago con Checkout Pro, un SmartPoint por kiosco, sin gestión de SmartPOS en Synap.*
