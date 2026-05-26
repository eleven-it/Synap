# Análisis: Módulo MercadoPago e integración con Sales

> **Solo referencia.** Las apps `mercadopago` y `sales` **no están instaladas** en la instalación mínima actual. Este documento es útil si se reinstalan o se integran en el futuro.

## Resumen ejecutivo

En el workspace actual **no existen las aplicaciones Django `mercadopago` ni `sales`**: están comentadas en `INSTALLED_APPS` y sus rutas en `urls.py`, y las carpetas de código de ambas apps **no están presentes** en el proyecto (instalación mínima para Reportes).  
Sí se conserva la **metadatos de integración** en `core` (registro de módulos, menús, permisos y hooks), lo que permite describir la **integración prevista** entre MercadoPago y Sales y qué habría que recuperar o implementar para tenerla operativa.

---

## 1. Estado actual en el proyecto

### 1.1 Aplicaciones no instaladas

| Componente | Ubicación | Estado |
|------------|-----------|--------|
| App `sales` | `sales/` | No existe en el árbol del proyecto; comentada en `settings.INSTALLED_APPS` |
| App `mercadopago` | `mercadopago/` | No existe en el árbol del proyecto; comentada en `settings.INSTALLED_APPS` |
| URLs `sales` | `django_project/urls.py` | Comentadas (`path('sales/', ...)`, `path('api/sales/', ...)`) |
| URLs `mercadopago` | `django_project/urls.py` | Comentada `path("mercadopago/", include("mercadopago.urls"))` |

Referencias en configuración:

- **`django_project/settings.py`** (aprox. líneas 48 y 52):
  - `# 'mercadopago',  # Requiere app 'sales' (no instalada). Descomentar al integrar ventas.`
  - `# 'sales',`
- **`django_project/urls.py`** (aprox. líneas 36 y 44–45):
  - `# path("mercadopago/", include("mercadopago.urls")),`
  - `# path('sales/', include('sales.urls', namespace='sales')),`
  - `# path('api/sales/', include('sales.api.urls')),`

### 1.2 Carga dinámica de módulos

- Los módulos “activos” se leen de la base de datos (`ModuleConfig.objects.filter(is_active=True)`), vía `core.module_manager`.
- El **URL registry** (`core.url_registry`) solo añade rutas para módulos activos; si `mercadopago` o `sales` se activaran en BD pero las apps no están en `INSTALLED_APPS` o no existen las carpetas, el `include()` fallaría al importar.
- Con la instalación mínima actual, ni `sales` ni `mercadopago` están en `INSTALLED_APPS`, por lo que no se cargan como apps Django ni sus URLs.

---

## 2. Diseño del módulo Sales (según registro y menú)

Definido en **`core/module_registry.py`** y **`core/utils/utils.py`** (menú y rutas nombradas).

### 2.1 Registro del módulo (`module_registry.py`)

- **Nombre:** `sales`, display "Sales Management".
- **Dependencias:** `core`.
- **Dependencias opcionales:** `inventory`, `accounting`.
- **Permisos:** CRUD para client, order, invoice, payment; `view_report`, `export_data`.
- **Hooks (puntos de extensión):**
  - `sales.pre_order_create` / `sales.post_order_create`
  - `sales.pre_invoice_create` / `sales.post_invoice_create`
  - `sales.pre_payment_create` / `sales.post_payment_create`
  - `sales.client_created` / `sales.client_updated`

### 2.2 Menú y rutas esperadas (`utils.py` → `APPS_MENU` y `url_mapping`)

- **Dashboard:** `sales:dashboard` → `/sales/`
- **Clientes:** `sales:client_list`, `sales:client_create` → `/sales/clients/`, `/sales/clients/create/`
- **TPV:** `sales:pos_dashboard` → punto de venta
- **Pedidos:** `sales:sales_order_list`, `sales:sales_order_create` → `/sales/orders/`
- **Facturas / Pagos:** `sales:invoice_list`, `sales:payment_list` → `/sales/invoices/`, `/sales/payments/`
- **Entregas / Devoluciones / Notas de crédito:** `sales:delivery_order_list`, `sales:return_delivery_list`, `sales:credit_note_list`
- **Configuración de pagos:**
  - **Métodos de pago:** `sales:payment_method_list` → `/sales/payment-methods/`
  - **Procesadores de pago:** `sales:payment_processor_list` → `/sales/payment-processors/`
- **Reportes y parámetros:** `sales:reports_dashboard`, listas de precios, condiciones de pago, terminales POS.

La integración con MercadoPago está pensada justamente sobre **métodos de pago** y **procesadores de pago** de Sales (MercadoPago como procesador y método asociado).

---

## 3. Diseño del módulo MercadoPago (según registro y menú)

### 3.1 Registro del módulo (`module_registry.py`)

- **Nombre:** `mercadopago`, display "MercadoPago Integration".
- **Descripción:** Integración con MercadoPago para procesamiento de pagos y dispositivos SmartPOS.
- **Dependencias obligatorias:** `core`, **`sales`**.
- **Dependencias opcionales:** `accounting`.
- **Configuración prevista:**
  - SmartPOS, gestión de dispositivos, logging de transacciones, webhooks, sincronización de dispositivos.
  - Moneda por defecto ARS, cuotas, impresión de comprobantes, modo offline.

### 3.2 Permisos (modelos implícitos por nombres de permisos)

- **MercadoPagoConfig:** `view/add/change/delete_mercadopagoconfig`
- **MercadoPagoDevice:** `view/add/change/delete_mercadopagodevice`, `manage_devices`
- **MercadoPagoTransaction:** `view/add/change/delete_mercadopagotransaction`, `process_payment`
- **Reportes y exportación:** `view_reports`, `export_data`

### 3.3 Hooks (eventos que el módulo podría emitir/consumir)

- Dispositivos: `device_registered`, `device_activated`, `device_deactivated`, `device_sync_completed`, `offline_transaction_synced`
- Transacciones: `transaction_created`, `transaction_completed`, `transaction_failed`, `payment_processed`, `webhook_received`

Estos hooks permitirían a Sales (u otros módulos) reaccionar cuando MercadoPago registra un pago o un fallo (por ejemplo, actualizar facturación o estado del pedido).

### 3.4 Menú MercadoPago (`utils.py` → `APPS_MENU`)

- **Configuración:** `mercadopago:config_list`, `mercadopago:config_create`
- **Dispositivos:** `mercadopago:device_list`, `mercadopago:device_create`, `mercadopago:device_status`
- **Transacciones:** `mercadopago:transaction_list`, `mercadopago:transaction_failed`, `mercadopago:transaction_reports`
- **Reportes:** `mercadopago:device_sales_report`, `mercadopago:payment_methods_report`, `mercadopago:device_performance_report`, `mercadopago:export_data`

No hay mapeo explícito `mercadopago:*` → path en `url_mapping` de `utils.py`; cuando la app exista, las URLs se resolverían por `reverse()` o habría que añadir entradas similares a las de `sales`.

---

## 4. Integración MercadoPago ↔ Sales (diseño previsto)

### 4.1 Dependencia explícita

- MercadoPago **depende de Sales** en `module_registry`: `'dependencies': ['core', 'sales']`.
- Implica: sin módulo Sales activo (y sin app `sales` instalada), MercadoPago no debería activarse; el `module_manager.can_activate_module('mercadopago')` comprueba que `sales` esté activo.

### 4.2 Puntos de enlace esperados

1. **Métodos de pago en Sales**
   - En `core/management/commands/load_initial_data.py` (código deshabilitado) se define un método de pago "MercadoPago" (`code='MERCADOPAGO'`, `payment_type='digital_wallet'`, `processor_name='MercadoPago'`) asociado a la empresa.
   - Eso indica que el modelo de Sales (p. ej. `PaymentMethod` y/o `PaymentProcessor`) debería poder tener un método/procesador “MercadoPago” y que el flujo de venta (TPV, órdenes, facturación) elegiría ese método al cobrar con MercadoPago.

2. **Hooks de pagos**
   - Sales define `sales.pre_payment_create` y `sales.post_payment_create`.
   - MercadoPago define `mercadopago.payment_processed`, `mercadopago.transaction_completed`, `mercadopago.transaction_failed`.
   - Flujo esperable: el TPV o el flujo de facturación de Sales inicia un pago con “MercadoPago”; el módulo `mercadopago` habla con la API de MercadoPago, y al recibir resultado dispara sus hooks; Sales (u otro suscriptor) podría crear/actualizar el registro de pago en Sales vía `post_payment_create` o lógica equivalente.

3. **Dispositivos SmartPOS**
   - MercadoPago gestiona dispositivos (lista, alta, estado) y transacciones por dispositivo; los reportes “Sales by Device” y “Device Performance” tienen sentido en un flujo donde cada terminal POS (o SmartPOS) está registrado en `mercadopago` y las ventas de Sales se vinculan a ese dispositivo/terminal.

4. **Contabilidad (opcional)**
   - Con `accounting` como dependencia opcional, el módulo MercadoPago podría registrar asientos o movimientos cuando hay transacciones completadas/fallidas.

### 4.3 Flujo de pago resumido (cuando existan ambas apps)

1. Usuario en TPV/POS de Sales elige “MercadoPago” como método de pago.
2. Sales llama al procesador MercadoPago (servicio/API dentro de la app `mercadopago`).
3. La app `mercadopago` comunica con la API de MercadoPago (o con el dispositivo SmartPOS), recibe éxito/error y actualiza su modelo de transacciones.
4. MercadoPago dispara hooks (`payment_processed`, `transaction_completed`/`transaction_failed`).
5. Sales crea o actualiza el `Payment` (y posiblemente el estado de la orden/factura) en sus modelos, de forma directa o suscribiéndose a esos hooks.

---

## 5. Otros módulos que referencian Sales o MercadoPago

- **TiendaNube:** `dependencies: ['core', 'inventory', 'sales']`; sincroniza pedidos que luego se facturarían/cobrarían en Sales; sin Sales no tiene dónde mapear órdenes de pago.
- **Clover:** igual que MercadoPago, `dependencies: ['core', 'sales']`; mismo patrón de “procesador de pagos” para Sales.
- **Reports:** el informe `sales_summary` y filtros por sucursal/punto de venta usan “sales” como concepto de negocio (ventas, facturación); no dependen de la app Django `sales` para ejecutar queries contra la base legacy, pero el nombre del reporte y los filtros están alineados con el dominio Sales.

---

## 6. Permisos y constantes

- En **`core/constantes_permisos.py`** aparece el patrón `"sales.*"` (junto con `purchases.*`, etc.) para agrupar permisos de módulos.
- En **`core/templatetags/menu_tags.py`** se trata `sales` como app de menú con permiso `sales.ver`.
- No hay referencias a modelos reales de `sales` o `mercadopago` en el código actual porque las apps no están instaladas.

---

## 7. Qué falta para tener la integración operativa

1. **Recuperar o implementar la app Django `sales`:**
   - Modelos: clientes, órdenes, facturas, pagos, métodos de pago, procesadores de pago, terminales, entregas, devoluciones, notas de crédito, listas de precios, condiciones de pago.
   - Vistas y URLs que cumplan los nombres del menú (`sales:dashboard`, `sales:payment_method_list`, etc.).
   - API si se usa `path('api/sales/', ...)` para TPV o frontend.

2. **Recuperar o implementar la app Django `mercadopago`:**
   - Modelos: configuración (tokens/credenciales), dispositivos SmartPOS, transacciones.
   - Integración con la API de MercadoPago (y/o SDK) para crear pagos, consultar estado, recibir webhooks.
   - Servicio que desde Sales se invoque al elegir “MercadoPago” como método de pago (o que escuche eventos de dispositivo).
   - Vistas y URLs para configuración, dispositivos, transacciones y reportes listados en el menú.
   - Opcional: suscripción a hooks de Sales (`post_payment_create`) o emisión de hooks propios para que Sales actualice el pago.

3. **Configuración del proyecto:**
   - Descomentar `'sales'` y `'mercadopago'` en `INSTALLED_APPS` (en ese orden: primero `sales`, luego `mercadopago`).
   - Descomentar en `urls.py` las rutas de `sales`, `api/sales` y `mercadopago`.
   - Si se usa registro dinámico de URLs, asegurar que al activar los módulos en `ModuleConfig` las apps existan y estén en `INSTALLED_APPS`.

4. **Datos iniciales:**
   - Reactivar (y adaptar) la creación de métodos de pago en `load_initial_data.py` o en un comando equivalente, creando el método “MercadoPago” y asociándolo al procesador/processor de MercadoPago en Sales.

5. **Documentación y pruebas:**
   - Credenciales y webhooks de MercadoPago (producción/sandbox).
   - Flujo E2E: venta en TPV → pago con MercadoPago → registro de pago en Sales y, si aplica, en contabilidad.

---

## 8. Referencias de código utilizadas

| Archivo | Uso |
|---------|-----|
| `core/module_registry.py` | Definición de módulos `sales` y `mercadopago`, dependencias, permisos y hooks |
| `core/utils/utils.py` | `APPS_MENU` (menú Sales y MercadoPago), `url_mapping` para rutas de Sales |
| `core/module_manager.py` | Activación de módulos y comprobación de dependencias |
| `core/url_registry.py` | Carga de URLs por módulo activo |
| `django_project/settings.py` | `INSTALLED_APPS` (sales y mercadopago comentados) |
| `django_project/urls.py` | Rutas de sales y mercadopago comentadas |
| `core/management/commands/load_initial_data.py` | Creación de método de pago "MercadoPago" (bloque deshabilitado) |
| `core/constantes_permisos.py` | Patrón `sales.*` |
| `core/templatetags/menu_tags.py` | Permiso `sales.ver` para menú |
| `core/templates/core/module_list.html` | Categoría "payment" para `mercadopago` y `clover` |

---

*Documento generado a partir del análisis del código existente en el repositorio. Las apps `sales` y `mercadopago` no están presentes en el workspace; la integración descrita corresponde al diseño definido en el registro de módulos y menús de `core`.*
