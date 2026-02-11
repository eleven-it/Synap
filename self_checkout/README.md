# Módulo Self-Checkout (Synap)

Punto de venta autoservicio para tiendas mayoristas. Opera en paralelo al TPV VB6, sin reemplazarlo.

---

## Alcance Fase 1

- Escaneo tradicional y RFID (lectura masiva con confirmación explícita)
- Venta solo con stock DISPONIBLE
- Pago 100% online (stub; integración MercadoPago futura)
- Factura electrónica obligatoria (FA/B según cliente)
- Permisos AdministraNET reutilizados

---

## Estructura

```
self_checkout/
├── urls.py, views.py, api_views.py
├── api_urls.py
├── services/         # CartService, StockService, KioskSessionService, ConfirmationService, InvoiceService
├── templates/self_checkout/
├── static/self_checkout/
├── management/commands/
├── tests/
└── sql/
```

## Feature flag

```bash
# .env
SELF_CHECKOUT_ENABLED=true   # false para deshabilitar rutas/UI
```

---

## Instalación

### 1. Crear tablas en MySQL

Opera por `base_empresa`: cada empresa tiene su propia base. Ejecutar para cada una:

```bash
python manage.py create_self_checkout_tables --base-empresa <NOMBRE_BASE>
python manage.py create_self_checkout_tables --base-empresa <NOMBRE_BASE> --dry-run  # Solo ver SQL
```

Script SQL: `self_checkout/sql/001_self_checkout_tables.sql`

**Migración 004** (recuperación de carritos en error):
```bash
python manage.py self_checkout_apply_migration_004 --base-empresa <NOMBRE_BASE>
```
Agrega columnas `ultimo_error_confirmacion`, `ultimo_intento_confirmacion` en `self_checkout_cart`. Ver `docs/self_checkout/ESPEC_PANEL_SUPERVISOR_SYNC_RECUPERACION.md`.

### 2. Registrar en Module Management

Para que el módulo aparezca en `/core/modules/`:

```bash
python manage.py setup_modules --sync-missing
```

Luego activar el módulo Self Checkout desde la UI.

### 3. Configurar kiosco

```bash
python manage.py seed_self_checkout_kiosk kiosk-01 --sucursal 1 --pv 1 --deposito 1 [--base-empresa X]
# Valida que sucursal, pv y deposito existan. Use --skip-validate para omitir.
```

### 4. Permisos AdministraNET

Agregar en `permiso_sistema` y asignar en `permiso_sistema_puesto`:

- `self_checkout.kiosk` → operar kiosco
- `self_checkout.supervisor` → asistencia / cancelaciones
- `self_checkout.admin` → configuración

Ver `reports/docs/AUDITORIA_PERMISOS_ADMINISTRANET_SELF_CHECKOUT.md`.

---

## Rutas y API

Base: `/api/self-checkout/`. Protegido por permisos AdministraNET (`self_checkout.kiosk`).

| Método | Ruta | Uso |
|--------|------|-----|
| POST | `cart/` | Crear carrito (kiosk_id) |
| GET | `cart/<id>/` | Detalle carrito + ítems |
| POST | `cart/<id>/items/` | Agregar ítem (codigo / id_articulo) |
| DELETE | `cart/<id>/items/<item_id>/` | Quitar ítem |
| POST | `cart/<id>/email/` | Email obligatorio (antes de confirmar) |
| POST | `cart/<id>/confirm/` | Confirmar venta (transaccional) |
| GET | `articulo/por-codigo/?codigo=X` | Buscar artículo por código/barcode |

### Búsqueda de artículo por código

- **Base:** `base_empresa` (sesión del usuario, ej: administranet89).
- **Tabla:** `articulo`.
- **Campos buscados (orden):** `id_manual`, `IDArt`, `NroCodBarra`, `NroCodBarraF`, `CodigoArticuloT`, `CodArtProv`.
- Si las columnas `NroCodBarra`, `NroCodBarraF`, etc. no existen, se usa solo `id_manual` e `IDArt`.

### Ejemplos

```bash
# Crear carrito
curl -X POST /api/self-checkout/cart/ -d '{"kiosk_id": "kiosk-01"}' -H "Content-Type: application/json"
# → {"cart_id": 1}

# Detalle
curl /api/self-checkout/cart/1/
# → {"cart": {...}, "items": [...]}

# Agregar ítem (por código de barras / id_manual / IDArt)
curl -X POST /api/self-checkout/cart/1/items/ -d '{"codigo": "789123", "cantidad": 1}'
# → {"item_id": 1}

# Email (obligatorio antes de confirmar)
curl -X POST /api/self-checkout/cart/1/email/ -d '{"email": "cliente@ejemplo.com"}'
# → {"ok": true, "estado": "pago_pendiente"}

# Confirmar
curl -X POST /api/self-checkout/cart/1/confirm/ -d '{"email": "cliente@ejemplo.com", "id_cliente": 1}'
# → {"ok": true, "resultado": {"codigo_movimiento": ..., "nro_comprobante": ..., ...}}
```

### Errores

Respuesta consistente: `{"error": "mensaje", "code": "CODIGO"}`. Códigos: `STOCK_INSUFFICIENT`, `EMAIL_REQUIRED`, `CART_NOT_FOUND`, `ARTICLE_NOT_FOUND`, `CONFIRM_FAILED`, etc.

### Troubleshooting: 400 en `/api/mercadopago/create-payment/`

Si el kiosco muestra error al elegir "Pagar con Mercado Pago" y la petición devuelve **400 Bad Request**, revisar:

1. **Empresa en sesión:** La API de Mercado Pago usa `base_empresa` (cookie/sesión). El usuario del kiosco debe tener una empresa seleccionada; si el kiosco se abre sin login, asegurar que la URL o el flujo establezcan la base (ej. selector de empresa o cookie).
2. **Configuración Mercado Pago:** En `/mercadopago/` debe existir una **MercadoPagoConfig** para esa `base_empresa`, con **Access Token** y **Public Key** válidos (prueba o producción).
3. **Body esperado:** El front envía JSON: `cart_id`, `payment_intent_id`, `total`, `id_sucursal`, `id_punto_venta`, `kiosk_id`, `back_url_success`, `back_url_failure`. El backend debe aceptar POST con `Content-Type: application/json`.

Ver también: `docs/PROPUESTA_SALES_DEPRECADO_MERCADOPAGO_SELF_CHECKOUT.md`.

### Confirm (transaccional)

`POST cart/<id>/confirm/` ejecuta transacción atómica:

1. **Idempotente:** si el carrito ya está confirmado, retorna resultado existente sin duplicar.
2. **Revalida stock** al inicio (UPDATE condicional en `stock_deposito`).
3. **Orden:** codmov → talonarios → cuentacliente → stock_deposito → stock → self_checkout_cart → audit_log.
4. **Rollback completo** si falla cualquier paso.
5. **Trazabilidad:** audit_log con `correlation_id`, `cart_id`, `codigo_movimiento`, `nro_comprobante`.

Estados: `borrador` → `pago_pendiente` → `pago_aprobado` → `confirmado`.

**Pago aprobado sin comprobante:** Si el cliente pagó en Mercado Pago (QR o dispositivo) pero no se emitió el comprobante (error de red, cierre del navegador, fallo AFIP, etc.), el carrito queda en `pago_aprobado`. Ver [PAGO_APROBADO_SIN_COMPROBANTE.md](../docs/self_checkout/PAGO_APROBADO_SIN_COMPROBANTE.md) para consecuencias y recuperación (comando `self_checkout_confirm_pending`).

**Numeración talonario vs AFIP:** Si aparece "No coincide el Nro. de talonario con el de ARCA", hay que sincronizar la numeración en administraNET (tabla `talonarios`). Ver [NUMERACION_TALONARIO_AFIP.md](../docs/self_checkout/NUMERACION_TALONARIO_AFIP.md).

---

## Modelo de datos (MySQL)

Prefijo: `self_checkout_`. Operación por `base_empresa`: cada empresa tiene sus propias tablas en su base MySQL.

---

## Diccionario de datos

### self_checkout_kiosk
Configuración por kiosco físico.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| kiosk_id | VARCHAR(64) UK | Identificador único del kiosco (ej: kiosk-01) |
| id_sucursal | INT | FK lógica → sucursales |
| id_punto_venta | INT | FK lógica → puntos_venta |
| id_deposito | INT | FK lógica → deposito |
| modo_rfid | VARCHAR(16) | delta \| snapshot |
| activo | TINYINT(1) | 1=activo |
| created_at, updated_at | DATETIME | Timestamps |

**Índices:** `uk_kiosk_id`, `idx_kiosk_activo`, `idx_sucursal`, `idx_sucursal_pv_dep`

---

### self_checkout_cart
Carrito principal. Estados: `borrador` → `pago_pendiente` → `pago_aprobado` → `confirmado` \| `cancelado` \| `error`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| kiosk_id | VARCHAR(64) | FK lógica → self_checkout_kiosk |
| id_sucursal, id_punto_venta, id_deposito | INT | Contexto operativo |
| estado | VARCHAR(32) | borrador, pago_pendiente, pago_aprobado, confirmado, cancelado, error |
| id_cliente | INT | FK lógica → clientes (1=CF) |
| email | VARCHAR(255) | Obligatorio para confirmar |
| cuit | VARCHAR(20) | Condición fiscal |
| tipo_comprobante | VARCHAR(4) | FA \| FB |
| codigo_movimiento | BIGINT | Tras confirmación (codmov) |
| id_cuentacliente | BIGINT | FK lógica → cuentacliente.id tras confirmación |
| subtotal, total | DECIMAL(18,4) | Importes |
| created_at, updated_at, confirmed_at | DATETIME | Timestamps |

**Índices:** `idx_kiosk_estado`, `idx_sucursal_created`, `idx_estado`, `idx_created`

---

### self_checkout_cart_item
Ítems del carrito.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| cart_id | BIGINT | FK lógica → self_checkout_cart.id |
| id_articulo | INT | FK lógica → articulo.IDArt |
| codigo_articulo | VARCHAR(64) | Código de barras / interno |
| descripcion | VARCHAR(255) | Nombre artículo |
| cantidad | DECIMAL(18,4) | Cantidad vendida |
| precio_unitario | DECIMAL(18,4) | Precio aplicado |
| alicuota_iva, importe_iva | DECIMAL | IVA |
| importe_total | DECIMAL(18,4) | Línea total |
| origen | VARCHAR(16) | scan \| rfid |
| rfid_event_id | BIGINT | FK lógica → self_checkout_rfid_event.id (si origen=rfid) |
| orden | INT | Orden en carrito |
| created_at, updated_at | DATETIME | Timestamps |

**Índices:** `idx_cart`, `idx_id_articulo`, `idx_cart_articulo`

---

### self_checkout_payment_intent
Stub de intenciones de pago (integración MercadoPago futura).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| cart_id | BIGINT | FK lógica → self_checkout_cart.id |
| kiosk_id, id_sucursal, id_punto_venta | - | Contexto |
| monto | DECIMAL(18,4) | Importe |
| estado | VARCHAR(32) | pendiente, aprobado, rechazado, expirado, cancelado |
| id_externo | VARCHAR(128) | ID en pasarela de pago |
| metodo | VARCHAR(32) | Tipo de pago |
| created_at, updated_at, approved_at | DATETIME | Timestamps |

**Índices:** `idx_cart`, `idx_estado`, `idx_created`

---

### self_checkout_invoice
Factura electrónica (CAE/CAEA).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| cart_id | BIGINT | FK lógica → self_checkout_cart.id |
| codigo_movimiento | BIGINT | Referencia codmov |
| id_cuentacliente | BIGINT | FK lógica → cuentacliente.id |
| nro_comprobante | VARCHAR(32) | Número factura |
| tipo_comprobante | VARCHAR(4) | FA \| FB |
| estado | VARCHAR(32) | pendiente, cae_ok, caea_pending, error |
| cae | VARCHAR(64) | CAE de AFIP |
| vto_cae | DATE | Vencimiento CAE |
| fe_regimen | VARCHAR(8) | CAE \| CAEA |
| request_payload, response_payload | TEXT | Log request/response AFIP |
| error_msg | VARCHAR(512) | Mensaje si error |
| created_at, updated_at | DATETIME | Timestamps |

**Índices:** `idx_cart`, `idx_cuentacliente`, `idx_estado`, `idx_nro_comprobante`

---

### self_checkout_rfid_event
Eventos de lectura RFID (lectura masiva con confirmación explícita).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| kiosk_id | VARCHAR(64) | Kiosco origen |
| id_sucursal | INT | Contexto |
| tag_id | VARCHAR(128) | ID del tag RFID |
| id_articulo | INT | FK lógica → articulo.IDArt (mapeado) |
| sesion_id | VARCHAR(64) | Sesión de lectura |
| estado | VARCHAR(32) | leido, mapeado, propuesto, confirmado, rechazado |
| confirmado_por_usuario | TINYINT(1) | 1 si usuario confirmó |
| cart_id | BIGINT | FK lógica → self_checkout_cart.id (si aplicado) |
| cart_item_id | BIGINT | FK lógica → self_checkout_cart_item.id |
| payload | JSON | Datos raw del evento |
| created_at | DATETIME | Timestamp lectura |

**Índices:** `idx_kiosk_sesion`, `idx_tag`, `idx_estado`, `idx_cart`

---

### self_checkout_audit_log
Auditoría de operaciones.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id | BIGINT PK | Auto-increment |
| kiosk_id, id_sucursal, id_punto_venta | - | Contexto |
| cart_id | BIGINT | FK lógica → self_checkout_cart.id |
| accion | VARCHAR(64) | Nombre de la acción |
| detalle | TEXT | Detalle adicional |
| created_at | DATETIME | Timestamp |

**Índices:** `idx_kiosk_created`, `idx_cart`, `idx_sucursal_created`, `idx_accion`

---

### Diagrama de relaciones (FKs lógicas)

```
self_checkout_kiosk (kiosk_id)
    ↑
self_checkout_cart ←── self_checkout_cart_item
    │                       ↑
    ├── self_checkout_payment_intent
    ├── self_checkout_invoice  ──→ cuentacliente
    ├── self_checkout_rfid_event
    └── self_checkout_audit_log

cart_item.id_articulo ──→ articulo
rfid_event.id_articulo ──→ articulo
```

**Nota:** Sin FKs físicas en el DDL para compatibilidad con esquemas AdministraNET. Integridad referencial garantizada por la aplicación.

---

## Tests

```bash
python manage.py test self_checkout.tests
```

Requisito: `pip install mysqlclient` (Django carga el backend MySQL al iniciar). Los tests usan mocks y no acceden a MySQL.

---

## FE (Factura Electrónica) con pyafipws

### Configuración por UI (recomendado)

La configuración FE se realiza desde **Facturación AFIP** en el menú (Self Checkout → Facturación AFIP): certificado, clave privada, CUIT y **modo Homologación/Producción**. Homologación usa entornos de prueba AFIP (todas las pruebas); Producción solo cuando esté validado. La config se guarda por base empresa (administraNET).

### Configuración por variables de entorno (fallback)

**Nunca** guardar credenciales en código ni loguearlas.

```bash
# .env (no commitear valores reales) — se usa si no hay config en UI
AFIP_CERT_PATH=/path/to/certificado.crt
AFIP_KEY_PATH=/path/to/clave.key
AFIP_CUIT=20123456789
AFIP_HOMO=1                    # 1=homologación, 0=producción
AFIP_CACHE_DIR=/tmp/pyafipws   # opcional
```

### Identificación del cliente y FA/FB/FC

La **condición fiscal del emisor** se obtiene de **datosempresa.IDIva** (administraNET VB6). Según AFIP:

- **Emisor Responsable Inscripto (IDIva 1) o Sujeto no categorizado (7):** se emite **Factura A** o **Factura B** según el receptor (padrón AFIP por CUIT del cliente; consumidor final → FB).
- **Emisor Monotributo/Exento (IDIva 2, 3, 4, 6):** siempre se emite **Factura C**; en el kiosco no se muestra la opción "Ticket Factura" (FA) y se ofrece solo "Continuar" / Consumidor Final.

Si el cliente no se identifica (sin CUIT) → Consumidor Final → FB (o FC si el emisor es Monotributo). Para emitir Factura A el usuario ingresa CUIT; se valida con padrón AFIP y solo si corresponde se emite FA.

**Talonarios:** En administraNET debe existir un talonario con `TipoComprobante = 'FC'` para el punto de venta del kiosco cuando la empresa sea Monotributo.

**RG 5616 (error 10246 – Condición IVA receptor):** AFIP exige el campo "Condición frente al IVA del receptor". En **pyafipws** (reingart/pyafipws, `wsfev1.py`) el parámetro correcto en `CrearFactura()` es **`condicion_iva_receptor_id`** (snake_case); se serializa al SOAP como `CondicionIVAReceptorId`. Valores típicos: 5 = Consumidor final, 1 = Responsable inscripto. El módulo lo setea según tipo de comprobante y documento.

**Campos y reglas por tipo (FA/FB/FC):** Ver **`docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md`** para el listado de campos FECAEDetRequest, reglas AFIP (10047, 10048, 10049, 10071) y cómo se arma el payload para Factura C (ImpIVA=0, sin IVA, FchVtoPago solo si Concepto 2 o 3).

### Estados de factura

| Estado | Descripción |
|--------|-------------|
| `pendiente` | Recién creada, sin intentar FE |
| `issued_cae` | CAE obtenido de AFIP |
| `issued_caea_pending` | CAEA obtenido, pendiente informar a AFIP |
| `sent` | CAEA informado correctamente |
| `failed` | Error (AFIP rechazó o no configurado) |

### Reintentos

```bash
python manage.py self_checkout_retry_fe [--base-empresa X] [--limit 50] [--dry-run]
```

Reintenta facturas con estado `issued_caea_pending` o `failed`.

---

## Reglas de negocio

- **Stock:** `disponible = saldo - saldo_pedido_cliente`. No vender sin disponible.
- **Factura:** Siempre se genera. FA, FB o FC según condición fiscal del emisor (datosempresa.IDIva) y del cliente (padrón AFIP).
- **AFIP:** CAE si responde; CAEA si falla (envío posterior).
- **Transacción confirmación:** codmov → talonarios → cuentacliente → stock_deposito → stock → audit_log (atómica).

---

## Documentación relacionada

- `reports/docs/DESARROLLO_SELF_CHECKOUT_SYNAP_FASE1.md`
- `reports/docs/AUDITORIA_PERMISOS_ADMINISTRANET_SELF_CHECKOUT.md`
- `reports/docs/CONTEXTO_TABLAS_VB6_INFORMES.md` (sección 11)

---

## Definition of Done (Fase 1)

| Área | Criterio | Estado |
|------|----------|--------|
| **Backend** | Tablas self_checkout_* por SQL en MySQL | ✅ |
| | Stock validado por DISPONIBLE | ✅ |
| | No confirmar sin stock | ✅ |
| | Factura siempre generada | ✅ |
| | CAEA soportado si AFIP falla (stub) | ✅ |
| | Transacciones atómicas | ✅ |
| | Auditoría registrada | ✅ |
| **Seguridad** | Permisos AdministraNET reutilizados | ✅ |
| | Roles kiosk / supervisor / admin | ✅ |
| | Sesión con PV y depósito | ✅ |
| **API** | Endpoints REST funcionando | ✅ |
| | Errores claros | ✅ |
| | Sin dependencia VB6 | ✅ |
| **UI** | Flujo autoservicio completo | ✅ |
| | Email obligatorio | ✅ |
| | Confirmación explícita | ✅ |
| | Errores UX-friendly | ✅ |
| | Kiosco-ready (touch) | ✅ |
| **Documentación** | Contexto DB actualizado | ✅ |
| | Auditoría permisos documentada | ✅ |
| | README técnico | ✅ |
