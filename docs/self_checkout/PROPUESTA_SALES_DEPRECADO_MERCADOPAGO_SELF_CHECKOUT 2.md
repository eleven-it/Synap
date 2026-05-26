# Propuesta: Sales deprecado + MercadoPago 100% Self Checkout y administraNET (DB)

> **Referencia de diseño.** Las apps `sales` y `mercadopago` **no están instaladas** actualmente. Este doc describe la arquitectura prevista si se integran.

## Resumen

1. **Sales**: Módulo deprecado. Se eliminó toda integración con Sales (menú, registro de módulos, dependencias, permisos, URLs).
2. **MercadoPago**: Reimplementado sin dependencia de Sales. Integración 100% con **Self Checkout** y procesos de pago de **administraNET en VB6**, siempre a nivel de **base de datos** (cuentacliente, caja, mercadopago_transaction).

---

## 1. Limpieza de Sales (realizada)

### 1.1 Eliminado o comentado

- **APPS_MENU** (`core/utils/utils.py`): Eliminado el bloque completo del menú "Sales" (dashboard, clientes, TPV, pedidos, facturas, pagos, etc.).
- **module_registry.py**: Eliminada la entrada del módulo `sales` (permisos, hooks, dependencias). Comentario: "Sales deprecado; ventas vía self_checkout".
- **url_mapping** (`core/utils/utils.py`): Eliminadas todas las rutas `sales:*` del mapeo hardcodeado.
- **constantes_permisos.py**: Eliminado `"sales.*"` del rol Gerente; añadidos `self_checkout.*`, `mercadopago.*`.
- **menu_tags.py**: Eliminado `sales` de la lista de apps y del mapeo de permisos; añadidos `self_checkout`, `mercadopago`.
- **module_list.html**: Eliminado `sales` de la categoría business y del filtro de categorías.
- **hook_admin.py**: Eliminado `sales` de las categorías de hooks; añadidos `self_checkout`, `mercadopago`.
- **crud_subheader.html**: Ejemplo de uso actualizado (sin URL `/sales/`).

### 1.2 Dependencias actualizadas

- **TiendaNube**: `dependencies: ['core', 'inventory']` (quitado `sales`).
- **Clover**: `dependencies: ['core', 'self_checkout']` (quitado `sales`).
- **MercadoPago**: `dependencies: ['core', 'self_checkout']` (quitado `sales`).

### 1.3 Settings y URLs

- **settings.py**: `sales` sigue comentado en `INSTALLED_APPS` (no se instala).
- **urls.py**: Rutas `sales/` y `api/sales/` siguen comentadas.

---

## 2. Reimplementación de MercadoPago

### 2.1 Diseño

- **Sin Sales**: No hay dependencia de la app Django `sales`. Métodos de pago y procesadores viven en administraNET (VB6) y en Self Checkout (payment_intent).
- **Con Self Checkout**: El flujo de pago es: carrito en kiosco → crear `self_checkout_payment_intent` → llamar a MercadoPago (preferencia) → usuario paga en MP → webhook/callback actualiza `payment_intent` y `self_checkout_cart` a `pago_aprobado` → confirmación (ConfirmationService) escribe en **cuentacliente**, **stock**, **stock_deposito**, **codmov**, **talonarios** (igual que hoy).
- **Con administraNET (DB)**:
  - **mercadopago_transaction** (tabla en base_empresa): vincula cart_id, payment_intent_id, id_mp (payment id MP), status, monto, codigo_movimiento, id_cuentacliente, id_caja (opcional).
  - **caja** (tabla administraNET): opcionalmente se escribe un ingreso cuando el pago MP está aprobado, usando `id_caja_abm` configurado en MercadoPagoConfig (compatible con VB6: tipo "Tarjeta" o el que use la empresa).

### 2.2 Estructura de la app `mercadopago`

```
mercadopago/
  __init__.py
  apps.py
  models.py          # MercadoPagoConfig (Django: access_token, public_key, base_empresa, id_caja_abm, sandbox)
  db.py              # get_mysql_connection(base_empresa), mysql_cursor
  sql/
    001_mercadopago_tables.sql   # mercadopago_transaction en base_empresa
  services/
    mp_api.py        # create_preference, get_payment (API MP)
    payment_service.py  # create_mp_payment, update_payment_status, write_caja_ingreso
  api_views.py       # create_payment (POST), webhook (POST)
  api_urls.py
  views.py           # config_list, config_form
  urls.py
  admin.py           # MercadoPagoConfigAdmin
  management/commands/
    create_mercadopago_tables.py  # --base-empresa <NOMBRE>
  templates/mercadopago/
    config_list.html, config_form.html
```

### 2.3 Tablas en base_empresa (MySQL)

- **mercadopago_transaction**: id, cart_id, payment_intent_id, id_mp, status, monto, metodo, codigo_movimiento, id_cuentacliente, id_caja, id_sucursal, id_punto_venta, kiosk_id, request_payload, response_payload, error_msg, created_at, updated_at.  
  Creación: `python manage.py create_mercadopago_tables --base-empresa <NOMBRE>`.

### 2.4 Configuración (Django)

- **MercadoPagoConfig**: por empresa (base_empresa = nombre de la base administraNET). Campos: name, access_token, public_key, sandbox, id_caja_abm (opcional; para escribir en caja), base_empresa (único).

### 2.5 Flujo de pago (Self Checkout + MP)

1. Usuario en kiosco termina carrito y elige "Pagar con MercadoPago".
2. Frontend (kiosco) crea o reutiliza `self_checkout_payment_intent` (cart_id, monto, estado pendiente).
3. Frontend llama `POST /api/mercadopago/create-payment/` con: cart_id, payment_intent_id, total, id_sucursal, id_punto_venta, kiosk_id, back_url_success, back_url_failure.
4. Backend crea preferencia MP, inserta fila en `mercadopago_transaction` (pendiente) y devuelve `init_point` (URL de pago MP).
5. Usuario es redirigido a MP, paga; MP redirige a back_url_success o envía webhook.
6. Webhook `POST /api/mercadopago/webhook/`: actualiza `mercadopago_transaction` (status, id_mp); si status aprobado, actualiza `self_checkout_payment_intent` (estado aprobado) y `self_checkout_cart` (estado pago_aprobado).
7. En kiosco, tras volver de MP o al detectar pago_aprobado, se llama al flujo de confirmación existente: `ConfirmationService.confirmar(cart_id)` → escribe cuentacliente, stock, codmov, talonarios, audit_log (igual que hoy).
8. Opcional: tras confirmar, si el pago fue MP y hay id_caja_abm configurado, llamar `write_caja_ingreso` y actualizar `mercadopago_transaction` con codigo_movimiento e id_cuentacliente.

### 2.6 Vinculación carrito–pago MP (external_reference)

La relación carrito–pago en MercadoPago se establece mediante **external_reference** con el formato:

```
cart_{cart_id}_pi_{payment_intent_id}
```

Ejemplo: `cart_42_pi_15` → carrito 42, payment_intent 15.

**Dónde se arma:**

| Integración | Archivo | Función |
|-------------|---------|---------|
| Checkout (Preference) | `mercadopago/services/payment_service.py` | `create_mp_payment` → `mp_api.create_preference` |
| Point (Order) | `mercadopago/services/payment_service.py` | `create_point_order` → `point_api.create_point_order` |

En ambos casos se usa el mismo string; en Point se trunca a 64 caracteres (límite de MP).

**Parseo inverso:** En `payment_service.py`, `_parse_external_reference(ref)` retorna `(cart_id, payment_intent_id)` si `ref` coincide con el patrón `cart_(\d+)_pi_(\d+)`. Se usa en `sincronizar_pagos_desde_mp` para vincular pagos aprobados en MP con el carrito correspondiente.

Cada pago en MP queda asociado a un único carrito.

### 2.7 Carritos borrador y recuperación

- **Borrador abandonado:** Un carrito en estado `borrador` puede ser abandonado (cliente se fue sin pagar). En el panel supervisor debe poder **eliminarse** (cancelar carrito).
- **Borrador recuperable:** Un borrador puede **recuperarse en el autoservicio** para modificar, eliminar o agregar ítems. El proceso continúa desde el mismo autoservicio (sin crear un carrito nuevo).
- **En el listado unificado:** Para carritos `borrador` se ofrece "Buscar pago en MP" (si hubo intento de pago) y **"Eliminar"** para abandonados.

### 2.8 URLs

- Web: `/mercadopago/` (config list), `/mercadopago/config/new/`, `/mercadopago/config/<pk>/edit/`.
- API: `POST /api/mercadopago/create-payment/`, `POST /api/mercadopago/webhook/`.

### 2.9 Permisos y menú

- El menú MercadoPago en `core/utils/utils.py` (APPS_MENU) se mantiene; permisos: `mercadopago.view_mercadopagoconfig`, etc. El módulo depende de `self_checkout` en `module_registry`.

---

## 3. Integración opcional en Self Checkout (frontend)

Para que el kiosco ofrezca "Pagar con MercadoPago":

1. En `kiosco.html`, añadir botón/opción "MercadoPago" en el paso de pago.
2. Al elegir MercadoPago: asegurar que existe `self_checkout_payment_intent` para el cart (crear uno si no existe), luego `fetch('/api/mercadopago/create-payment/', { method: 'POST', body: JSON.stringify({ cart_id, payment_intent_id, total, id_sucursal, id_punto_venta, kiosk_id, back_url_success: window.location.href, back_url_failure: ... }) })`, y redirigir a `response.init_point`.
3. Página de vuelta (back_url_success): comprobar estado del cart (pago_aprobado); si es así, mostrar "Confirmar compra" y llamar al endpoint de confirmación existente del self_checkout.

La API de MercadoPago ya está lista; la UI del kiosco para disparar este flujo es opcional y se puede implementar en un siguiente paso.

---

## 4. Opción B: Preservar datos de configuración MercadoPago

Si ya tenías la app MercadoPago instalada con el esquema antiguo (empresa_id, client_id, client_secret, etc.) y querés conservar esas configuraciones:

### Pasos manuales (en este orden)

1. **Base default (PostgreSQL)**  
   Borrar las filas de migraciones de MercadoPago para que Django vuelva a aplicar migraciones:
   ```sql
   DELETE FROM django_migrations WHERE app = 'mercadopago';
   ```

2. **Renombrar la tabla antigua** (solo si existe `mercadopago_mercadopagoconfig` con el esquema viejo):
   ```sql
   ALTER TABLE mercadopago_mercadopagoconfig RENAME TO mercadopago_mercadopagoconfig_old;
   ```
   Si no tenés tabla antigua (instalación nueva), omití este paso.

3. **Aplicar migraciones**:
   ```bash
   python manage.py migrate mercadopago
   ```
   - La migración `0001_initial` crea la nueva tabla `mercadopago_mercadopagoconfig`.
   - La migración `0002_preserve_old_config_data`:
     - Si existe `mercadopago_mercadopagoconfig_old`, copia cada fila al nuevo esquema (client_secret → access_token, client_id → public_key, empresa_id → base_empresa vía tabla `empresas` en MySQL si está disponible).
     - Si no se puede resolver `base_empresa` (p. ej. no hay MySQL `empresas` o el id no coincide), se usa un valor tipo `migrated_old_<id>`; en ese caso editá la configuración en `/mercadopago/` y asigná el **Base empresa (DB)** correcto (nombre de la base administraNET).
     - Al final elimina la tabla `mercadopago_mercadopagoconfig_old`.

4. **Revisar configuraciones**  
   Entrá a `/mercadopago/`, verificá que cada fila tenga el **Base empresa (DB)** correcto y, si hace falta, completá **Access Token** / **Public Key** (MercadoPago ahora usa access_token en lugar de client_id/client_secret).

### Comandos concretos (Docker: Synap_app + Synap_db)

Desde la raíz del proyecto (`Synap/`), con los contenedores levantados (`docker compose up -d`):

**1. En PostgreSQL** (reemplazá `synap_user` y `synap_db` si en tu `.env` tenés otros `POSTGRES_USER` / `POSTGRES_DB`):

```bash
docker compose exec db psql -U synap_user -d synap_db -c "DELETE FROM django_migrations WHERE app = 'mercadopago';"
```

**2. Si tenés tabla antigua de MercadoPago** (mismo usuario y base):

```bash
docker compose exec db psql -U synap_user -d synap_db -c "ALTER TABLE mercadopago_mercadopagoconfig RENAME TO mercadopago_mercadopagoconfig_old;"
```

**3. Aplicar migraciones** (dentro del contenedor de la app):

```bash
docker compose exec app python manage.py migrate mercadopago
```

**4. Revisar**  
Abrir en el navegador `http://localhost:8000/mercadopago/` y, si hace falta, editar cada configuración (Base empresa (DB) y credenciales).

### Requisitos para resolver base_empresa automáticamente

- En `settings.py` debe existir la base `mysql` en `DATABASES` (misma que usa el login).
- La base MySQL `empresas` debe tener la tabla `empresas` con columnas `id_empresa` y `base_empresa`.
- En la tabla antigua, el campo que almacenaba el id de empresa (p. ej. `empresa_id`) debe coincidir con `id_empresa` de esa tabla MySQL. Si no, `base_empresa` quedará como `migrated_old_<id>` y deberás corregirlo a mano.

---

## 5. Resumen de archivos tocados

| Acción | Archivo(s) |
|--------|------------|
| Eliminado menú Sales | core/utils/utils.py |
| Eliminado registro sales | core/module_registry.py |
| Eliminado url_mapping sales | core/utils/utils.py |
| Dependencias tiendanube/clover/mercadopago | core/module_registry.py |
| Permisos y menú tags | core/constantes_permisos.py, core/templatetags/menu_tags.py |
| Filtros módulos/hooks | core/templates/core/module_list.html, core/views/hook_admin.py |
| Ejemplo crud_subheader | core/templates/core/partials/crud_subheader.html |
| Nueva app | mercadopago/* (models, db, sql, services, api_views, views, urls, admin, management, templates) |
| Settings y URLs proyecto | django_project/settings.py, django_project/urls.py |

---

*Documento generado como propuesta e implementación de referencia. Ajustar según convenciones de proyecto y pruebas E2E.*
