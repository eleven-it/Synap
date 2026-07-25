# Diseño técnico – Módulo Self-Checkout (Synap)

**Versión:** Fase 1 (Diseño – pre-implementación)  
**Fecha:** 23-01-2025  
**Referencias:** CONTEXTO_TABLAS_VB6_INFORMES.md, INFORME_AUDITORIA_TPV_TANDA1.md  

---

## 1. Arquitectura general

### 1.1 Posicionamiento del módulo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SYNAP (Django)                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Reports         │  │ Login / Auth     │  │ Self-Checkout (NUEVO)       │  │
│  │ Dashboard       │  │ AdministraNET    │  │ - Carrito independiente     │  │
│  │ SIA             │  │ session          │  │ - Pagos online              │  │
│  └────────┬────────┘  └────────┬────────┘  │ - FE A/B                    │  │
│           │                    │           │ - RFID (lectura masiva)     │  │
│           └────────────────────┼───────────┴──────────────┬──────────────┘  │
│                                │                          │                 │
│                                ▼                          ▼                 │
│                    ┌───────────────────────────────────────────────────────┐│
│                    │              MySQL (AdministraNET DB)                  ││
│                    │  Tablas existentes: cuentacliente, stock, codmov,     ││
│                    │  talonarios, articulo, stock_deposito, cliente, etc.  ││
│                    │  Tablas nuevas: self_checkout_*                       ││
│                    └───────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ NO USA
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VB6 TPV (independiente)                            │
│  cuerpostock, codmov, cuentacliente, etc. – reglas de negocio compartidas   │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **DB-first:** Todo se resuelve contra la base MySQL existente.
- **Sin dependencia de VB6:** No hay API ni llamadas a VB6; se reutilizan las reglas documentadas.
- **Tablas nuevas:** Solo para el flujo de autoservicio (carrito, payment_intent, RFID, audit).

### 1.2 Principios de diseño

| Principio | Aplicación |
|-----------|------------|
| No reutilizar cuerpostock | Carrito en `self_checkout_cart` / `self_checkout_cart_items`. |
| No vender sin stock | Validar `stock_deposito.saldo >= cantidad` antes de confirmar. |
| Pagos 100% online | Integración futura con MercadoPago/tarjetas; ahora diseño de `payment_intent`. |
| FE A/B obligatoria | Email obligatorio; tipo según condición fiscal del cliente. |
| RFID = confirmación explícita | Tags leídos → propuesta de ítems → usuario confirma → se agregan. |
| Múltiples kioscos | `kiosk_id` en todas las tablas self_checkout. |

---

## 2. Diagrama de flujo de estados

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                     CICLO DE VENTA SCO                        │
                    └──────────────────────────────────────────────────────────────┘

  ┌─────────────┐     scan/rfid      ┌─────────────┐     email OK      ┌─────────────────┐
  │   INICIO    │ ─────────────────► │   CARRITO   │ ────────────────► │ PAGO PENDIENTE  │
  │  (borrador) │     + ítems        │  (borrador) │   (validar stock) │                 │
  └─────────────┘                    └──────┬──────┘                   └────────┬────────┘
         ▲                                  │                                   │
         │                                  │ eliminar ítems                    │ pago
         │                                  │ vaciar                            │ aprobado
         └──────────────────────────────────┘                                   │
                                                                                ▼
  ┌─────────────┐     "Nueva compra"   ┌─────────────────┐     transacción   ┌─────────────────┐
  │   INICIO    │ ◄──────────────────  │ PANTALLA FINAL  │ ◄────────────────  │ PAGO APROBADO   │
  │             │                      │ Imprimir/Enviar │    atómica         │ Confirmación     │
  └─────────────┘                      └─────────────────┘    DB              └─────────────────┘
                                               │
                                               │ FE emitida
                                               │ Stock descontado
                                               │ cuentacliente INSERT
```

### 2.1 Estados del carrito

| Estado | Valor `estado` | Descripción |
|--------|----------------|-------------|
| `borrador` | `borrador` | Carrito en edición; se pueden agregar/quitar ítems. |
| `pago_pendiente` | `pago_pendiente` | Email capturado, stock validado; esperando pago online. |
| `pago_aprobado` | `pago_aprobado` | Pago aprobado por pasarela; aún no confirmado en DB. |
| `confirmado` | `confirmado` | Transacción atómica ejecutada; FE emitida, stock descontado. |
| `cancelado` | `cancelado` | Carrito cancelado o expirado. |
| `error` | `error` | Error en pago o confirmación; requiere intervención. |

---

## 3. Modelo de datos propuesto

### 3.1 Tablas nuevas (self_checkout_*)

#### `self_checkout_cart`

Carrito principal. Un registro por sesión de compra activa.

| Campo | Tipo | Null | Descripción |
|-------|------|------|-------------|
| `id` | BIGINT PK AUTO_INCREMENT | No | PK |
| `kiosk_id` | VARCHAR(64) | No | Identificador del kiosco (ej. `kiosk-01`) |
| `id_sucursal` | INT | No | FK a sucursales.id_sucursal |
| `id_punto_venta` | INT | No | FK a punto_venta.id_punto_venta |
| `id_deposito` | INT | No | Depósito de salida (stock_deposito.id_deposito) |
| `estado` | VARCHAR(32) | No | borrador \| pago_pendiente \| pago_aprobado \| confirmado \| cancelado \| error |
| `id_cliente` | INT | Sí | cliente.Codigo (1 = CF si ocasional) |
| `email` | VARCHAR(255) | Sí | Email (OBLIGATORIO para pasar a pago) |
| `cuit` | VARCHAR(20) | Sí | Para determinar FA vs FB |
| `tipo_comprobante` | VARCHAR(4) | Sí | FA \| FB (definido al confirmar) |
| `codigo_movimiento` | BIGINT | Sí | Asignado tras confirmación (codmov) |
| `id_cuentacliente` | BIGINT | Sí | cuentacliente.id_cuentacliente tras INSERT |
| `subtotal` | DECIMAL(18,4) | No | Subtotal sin IVA |
| `total` | DECIMAL(18,4) | No | Total con IVA |
| `created_at` | DATETIME | No | |
| `updated_at` | DATETIME | No | |
| `confirmed_at` | DATETIME | Sí | Momento de confirmación |

**Índices:** `(kiosk_id, estado)`, `(id_sucursal, created_at)`, `(estado, created_at)`.

---

#### `self_checkout_cart_items`

Ítems del carrito. No reutiliza cuerpostock.

| Campo | Tipo | Null | Descripción |
|-------|------|------|-------------|
| `id` | BIGINT PK AUTO_INCREMENT | No | PK |
| `cart_id` | BIGINT | No | FK self_checkout_cart.id |
| `id_articulo` | INT | No | articulo.IDArt |
| `codigo_articulo` | VARCHAR(64) | Sí | articulo.id_manual (para display) |
| `descripcion` | VARCHAR(255) | Sí | |
| `cantidad` | DECIMAL(18,4) | No | |
| `precio_unitario` | DECIMAL(18,4) | No | Precio venta unitario |
| `alicuota_iva` | DECIMAL(8,4) | Sí | % IVA |
| `importe_iva` | DECIMAL(18,4) | Sí | |
| `importe_total` | DECIMAL(18,4) | No | Cantidad × precio + IVA |
| `origen` | VARCHAR(16) | No | `scan` \| `rfid` |
| `rfid_event_id` | BIGINT | Sí | FK self_checkout_rfid_events (si origen=rfid) |
| `orden` | INT | No | Orden de aparición en carrito |
| `created_at` | DATETIME | No | |
| `updated_at` | DATETIME | No | |

**Índices:** `(cart_id)`, `(cart_id, orden)`.

---

#### `self_checkout_payment_intents`

Intención de pago. Un registro por intento de pago (puede haber varios si falla).

| Campo | Tipo | Null | Descripción |
|-------|------|------|-------------|
| `id` | BIGINT PK AUTO_INCREMENT | No | PK |
| `cart_id` | BIGINT | No | FK self_checkout_cart.id |
| `kiosk_id` | VARCHAR(64) | No | |
| `id_sucursal` | INT | No | |
| `id_punto_venta` | INT | No | |
| `monto` | DECIMAL(18,4) | No | Monto a cobrar |
| `estado` | VARCHAR(32) | No | pendiente \| aprobado \| rechazado \| expirado \| cancelado |
| `id_externo` | VARCHAR(128) | Sí | ID de MercadoPago/u otra pasarela |
| `metodo` | VARCHAR(32) | Sí | tarjeta \| transferencia \| etc. |
| `created_at` | DATETIME | No | |
| `updated_at` | DATETIME | No | |
| `approved_at` | DATETIME | Sí | |

**Índices:** `(cart_id)`, `(estado, created_at)`.

---

#### `self_checkout_rfid_events`

Eventos RFID para auditoría y trazabilidad.

| Campo | Tipo | Null | Descripción |
|-------|------|------|-------------|
| `id` | BIGINT PK AUTO_INCREMENT | No | PK |
| `kiosk_id` | VARCHAR(64) | No | |
| `id_sucursal` | INT | No | |
| `tag_id` | VARCHAR(128) | No | EPC/UID del tag |
| `id_articulo` | INT | Sí | articulo.IDArt (mapeado) |
| `sesion_id` | VARCHAR(64) | No | Identificador de sesión de lectura |
| `estado` | VARCHAR(32) | No | leido \| mapeado \| propuesto \| confirmado \| rechazado |
| `confirmado_por_usuario` | TINYINT(1) | No | 0=no, 1=sí |
| `cart_id` | BIGINT | Sí | FK si se agregó a carrito |
| `cart_item_id` | BIGINT | Sí | FK si se creó ítem |
| `created_at` | DATETIME | No | |

**Índices:** `(kiosk_id, sesion_id)`, `(tag_id, created_at)`.

---

#### `self_checkout_audit_log`

Log de auditoría de operaciones.

| Campo | Tipo | Null | Descripción |
|-------|------|------|-------------|
| `id` | BIGINT PK AUTO_INCREMENT | No | PK |
| `kiosk_id` | VARCHAR(64) | No | |
| `id_sucursal` | INT | No | |
| `id_punto_venta` | INT | No | |
| `cart_id` | BIGINT | Sí | |
| `accion` | VARCHAR(64) | No | carrito_creado, item_agregado, item_eliminado, pago_iniciado, pago_aprobado, confirmado, error, etc. |
| `detalle` | TEXT | Sí | JSON o texto libre |
| `created_at` | DATETIME | No | |

**Índices:** `(kiosk_id, created_at)`, `(cart_id)`, `(accion)`.

---

### 3.2 Tablas existentes que se escriben (commit final)

Según CONTEXTO_TABLAS e INFORME_AUDITORIA_TPV_TANDA1:

| Tabla | Operación | Uso |
|-------|-----------|-----|
| `codmov` | UPDATE | Incrementar CodigoMovimiento |
| `talonarios` | UPDATE | NroActual por id_punto_venta + TipoComprobante (FA/FB) |
| `cuentacliente` | INSERT | Cabecera comprobante |
| `stock` | INSERT | Movimiento de salida por ítem |
| `stock_deposito` | UPDATE | saldo -= cantidad por ítem |
| `fe_codbarra` | INSERT/UPDATE | Código de barras FE (si aplica) |
| `cuentacliente` | UPDATE | fe_cae, fe_vto_cae, fe_comp (post-FE) |

**Nota:** tc_comprobante, caja, saldo_caja, imputacion, percep_cli: se integran cuando exista el módulo de pagos y percepciones. En Fase 1, el commit contempla solo: codmov, talonarios, cuentacliente, stock, stock_deposito. FE se emite después del commit (o en el mismo flujo según diseño del módulo FE).

---

## 4. Flujo de confirmación definitiva

### 4.1 Precondiciones

1. Carrito en estado `pago_aprobado`.
2. Payment intent con `estado = aprobado`.
3. Email capturado y válido.
4. Stock validado: `∀ ítem: stock_deposito.saldo >= cantidad` para `id_deposito` del carrito.
5. Tipo comprobante definido: FA (RI) o FB (CF, monotributo, exento) según cliente/Contribuyentes.

### 4.2 Orden exacto del commit final (transacción atómica)

```
BEGIN;

1. UPDATE codmov SET CodigoMovimiento = CodigoMovimiento + 1 WHERE codigo = 1;
   SELECT CodigoMovimiento INTO @contador FROM codmov WHERE codigo = 1;

2. UPDATE talonarios SET NroActual = NroActual + 1 
   WHERE id_punto_venta = :id_pv AND TipoComprobante = :tipo_comp;
   SELECT NroActual INTO @nro_comp FROM talonarios 
   WHERE id_punto_venta = :id_pv AND TipoComprobante = :tipo_comp;

3. INSERT INTO cuentacliente (
     CodigoMovimiento, NroComprobante, TipoComprobante, Fecha, Codigo, CodSucursal, id_pv,
     ImporteVenta, SubtotalDesc, Iva1, Iva2, tpv_comp, tpv_nombre_ocasional, tpv_mail_ocasional,
     ... (resto campos según VB6 cuentacliente)
   ) VALUES (@contador, @nro_comp, :tipo_comp, NOW(), :id_cliente, :id_sucursal, :id_pv, ...);
   SET @id_cuentacliente = LAST_INSERT_ID();

4. Para cada ítem en self_checkout_cart_items:
   a. UPDATE stock_deposito SET saldo = saldo - :cantidad 
      WHERE id_articulo = :id_art AND id_deposito = :id_deposito;
   b. INSERT INTO stock (CodigoMovimiento, IDArt, Cantidad, Entrada, Salida, CodDeposito, ...)
      VALUES (@contador, :id_art, :cantidad, 0, :cantidad, :id_deposito, ...);

5. UPDATE self_checkout_cart SET 
     estado = 'confirmado', 
     codigo_movimiento = @contador, 
     id_cuentacliente = @id_cuentacliente,
     confirmed_at = NOW()
   WHERE id = :cart_id;

6. INSERT INTO self_checkout_audit_log (kiosk_id, id_sucursal, id_punto_venta, cart_id, accion, detalle, created_at)
   VALUES (..., 'confirmado', '{"codigo_movimiento": @contador, ...}', NOW());

COMMIT;
```

### 4.3 Post-commit (fuera de transacción o en transacción separada)

- Emisión FE (AFIP): si el sistema FE está integrado, enviar comprobante y luego UPDATE cuentacliente (fe_cae, fe_vto_cae, fe_comp, fe_transmitido), INSERT fe_codbarra.
- Envío de email con comprobante.
- Integración con tc_comprobante, caja, saldo_caja cuando exista el módulo de pagos.

### 4.4 Rollback

Si cualquier paso falla → `ROLLBACK`. El carrito permanece en `pago_aprobado`; se debe permitir reintentar o cancelar manualmente (supervisor).

---

## 5. Estrategia de concurrencia de stock

### 5.1 Regla: no vender sin stock

- **Validación previa al pago:** Antes de pasar a `pago_pendiente`, verificar que para cada ítem exista `stock_deposito.saldo >= cantidad` (por `id_articulo`, `id_deposito`).
- **Bloqueo optimista en confirmación:** En el paso 4a, usar:
  ```sql
  UPDATE stock_deposito 
  SET saldo = saldo - :cantidad 
  WHERE id_articulo = :id_art AND id_deposito = :id_deposito 
    AND saldo >= :cantidad;
  ```
  Si `ROW_COUNT() = 0` → rollback, estado `error`, mensaje "Stock insuficiente".

### 5.2 Interacción con TPV VB6

- TPV y Self-Checkout comparten `stock_deposito` y `stock`.
- Ambos pueden vender en paralelo; la condición `saldo >= cantidad` evita stock negativo.
- Si dos ventas compiten por el mismo stock, una fallará en el UPDATE; se debe reintentar o informar al usuario.

### 5.3 Depósito por kiosco

- Cada kiosco tiene un `id_deposito` fijo (configuración).
- Todo el stock se descuenta de ese depósito.

---

## 6. RFID – flujo de lectura masiva

### 6.1 Regla: nunca agregar silenciosamente

```
┌─────────────────┐    tags leídos    ┌─────────────────┐    usuario confirma   ┌─────────────────┐
│ Sesión lectura  │ ────────────────► │ Propuesta ítems │ ────────────────────► │ Ítems en carrito │
│ (ventana tiempo)│                   │ (agrupados)     │   "Agregar" / "No"    │ (self_checkout_  │
└─────────────────┘                   └─────────────────┘                       │  cart_items)     │
        │                                      │                                         │
        ▼                                      ▼                                         ▼
  rfid_events                        rfid_events.estado=propuesto              rfid_events.estado=
  estado=leido                                                                  confirmado
```

### 6.2 Pasos

1. **Inicio sesión:** Crear `sesion_id` (UUID o similar).
2. **Lectura:** Recibir tags → INSERT en `self_checkout_rfid_events` (estado=leido).
3. **Mapeo:** tag_id → articulo (tabla de mapeo tag_id ↔ id_articulo).
4. **Propuesta:** Agrupar por artículo, mostrar lista al usuario.
5. **Confirmación:** Usuario acepta → INSERT en `self_checkout_cart_items` (origen=rfid, rfid_event_id), UPDATE rfid_events.estado=confirmado.
6. **Rechazo:** Usuario rechaza → UPDATE rfid_events.estado=rechazado.

---

## 7. Roles y permisos

| Rol | Código | Permisos |
|-----|--------|----------|
| SelfCheckoutKiosk | `self_checkout.kiosk` | Crear carrito, agregar ítems, iniciar pago, confirmar (en kiosco asignado). No ve reportes, no modifica precios. |
| SelfCheckoutSupervisor | `self_checkout.supervisor` | Todo lo anterior + cancelar carritos, ver audit_log del kiosco, resolver errores. |
| Admin | `*` o `self_checkout.admin` | Acceso total; configuración kioscos, reportes. |

Implementar vía tabla de permisos (ej. `core`/AdministraNET) y middleware que verifique `self_checkout.kiosk` por ruta/vista del kiosco.

---

## 8. UX/UI – estructura de componentes

### 8.1 Pantallas

| Pantalla | Estados | Componentes |
|----------|---------|-------------|
| Carrito | borrador | Lista ítems, totales, botón "Pagar", scan activo, zona RFID propuesta |
| Captura email | borrador → pago_pendiente | Input email, validación, botón "Continuar al pago" |
| Pago | pago_pendiente | iframe/redirect pasarela, estado "Procesando...", timeout |
| Resultado | pago_aprobado → confirmado | "Procesando confirmación..." → "¡Listo!" |
| Final | confirmado | Botones: Imprimir, Enviar por email, Nueva compra |

### 8.2 Feedback

- **Visual:** Indicador de ítem agregado, total actualizado, estado de pago.
- **Sonoro:** Beep al escanear, sonido de éxito/error.
- **Estados claros:** Siempre visible: total, cantidad de ítems, estado actual.

---

## 9. Riesgos detectados

### 9.1 Concurrencia

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Stock insuficiente entre validación y confirmación | Alta | Medio | UPDATE con `saldo >= cantidad`; rollback y mensaje claro. |
| codmov en dos procesos simultáneos | Baja | Alto | Transacción separada con lock; o usar `SELECT ... FOR UPDATE` antes del UPDATE. |
| Dos kioscos mismos talonarios | Baja | Alto | Un talonario por punto de venta; cada kiosco vinculado a un id_punto_venta distinto o usar lock. |

### 9.2 Stock

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Saldo negativo por bug | Media | Alto | CHECK constraint si el motor lo permite; UPDATE condicional; tests. |
| Descuento en depósito equivocado | Baja | Medio | id_deposito fijo por kiosco; validar en configuración. |

### 9.3 Pagos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Pago aprobado y fallo en confirmación | Media | Alto | Carrito en error; proceso de conciliación; reintento automático con idempotencia. |
| Pago duplicado | Baja | Alto | payment_intent con estado; no crear dos confirmaciones para el mismo cart_id. |

### 9.4 Factura electrónica

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Fallo AFIP tras commit DB | Media | Alto | FE asíncrona con reintentos; cuentacliente con fe_comp='No' hasta éxito. |
| Email inválido | Baja | Medio | Validación antes de pagar; permitir corrección si aún en borrador. |

### 9.5 UX en tienda

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Cliente abandona sin pagar | Alta | Bajo | Carritos en borrador con TTL; limpieza periódica. |
| RFID mal configurado | Media | Medio | Propuesta explícita; usuario siempre confirma. |
| Pantalla táctil no responsiva | Media | Medio | UI grande, botones amplios, feedback inmediato. |

---

## 10. Checklist para empezar a codear

### 10.1 Infraestructura

- [ ] Crear app Django `self_checkout` (o similar).
- [ ] Migraciones para `self_checkout_cart`, `self_checkout_cart_items`, `self_checkout_payment_intents`, `self_checkout_rfid_events`, `self_checkout_audit_log`.
- [ ] Configurar rutas y permisos (`self_checkout.kiosk`, `self_checkout.supervisor`).
- [ ] Configuración por kiosco: `kiosk_id`, `id_sucursal`, `id_punto_venta`, `id_deposito` (tabla o settings).

### 10.2 Servicios de negocio

- [ ] Servicio `CartService`: crear carrito, agregar ítem (scan), quitar ítem, validar stock.
- [ ] Servicio `StockValidator`: comprobar `stock_deposito.saldo >= cantidad` por ítem.
- [ ] Servicio `ConfirmacionService`: ejecutar transacción atómica del commit final.
- [ ] Servicio `TipoComprobanteService`: determinar FA vs FB según cliente/Contribuyentes.
- [ ] Servicio `RfidService`: registrar evento, mapeo tag→artículo, propuesta, confirmar ítems.

### 10.3 API / endpoints

- [ ] `POST /api/self-checkout/cart/` – crear carrito.
- [ ] `POST /api/self-checkout/cart/{id}/items/` – agregar ítem (scan).
- [ ] `DELETE /api/self-checkout/cart/{id}/items/{item_id}` – quitar ítem.
- [ ] `POST /api/self-checkout/cart/{id}/email/` – capturar email, validar stock, pasar a pago_pendiente.
- [ ] `POST /api/self-checkout/cart/{id}/payment-intent/` – crear payment_intent (placeholder).
- [ ] `POST /api/self-checkout/cart/{id}/confirm/` – confirmar (tras pago aprobado).
- [ ] `POST /api/self-checkout/rfid/propose/` – recibir tags, devolver propuesta.
- [ ] `POST /api/self-checkout/rfid/confirm/` – confirmar propuesta e insertar ítems.

### 10.4 Integración con tablas existentes

- [ ] Revisar esquema real de `codmov`, `talonarios`, `cuentacliente` (nombres de campos).
- [ ] Revisar campos obligatorios de `cuentacliente` para INSERT.
- [ ] Revisar estructura de `stock` y `stock_deposito` (id_articulo vs IDArt, id_deposito vs CodDeposito).
- [ ] Mapeo cliente: Consumidor Final = Codigo 1; búsqueda por CUIT si aplica.

### 10.5 Tests

- [ ] Test: agregar ítem con stock suficiente.
- [ ] Test: rechazar ítem si stock insuficiente.
- [ ] Test: confirmación atómica (codmov, talonarios, cuentacliente, stock, stock_deposito).
- [ ] Test: rollback si stock insuficiente en confirmación.
- [ ] Test: dos confirmaciones concurrentes (una debe fallar).

---

## 11. Resumen de entregables Fase 1

| Entregable | Estado |
|------------|--------|
| Arquitectura general | ✅ Documento |
| Diagrama de flujo | ✅ Sección 2 |
| Modelo de datos | ✅ Sección 3 |
| Transacciones críticas | ✅ Sección 4 |
| Estrategia concurrencia stock | ✅ Sección 5 |
| Definición commit final | ✅ Sección 4.2 |
| Riesgos detectados | ✅ Sección 9 |
| Checklist para codear | ✅ Sección 10 |

**Próximo paso:** Validación por PO. Tras aprobación, iniciar implementación (Fase 2).
