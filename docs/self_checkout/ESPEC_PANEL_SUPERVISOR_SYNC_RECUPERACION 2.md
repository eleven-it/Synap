# Especificación: Panel Supervisor - Sincronización Talonarios y Recuperación de Carritos

**Estado: IMPLEMENTADO** (ver cambios en self_checkout/)

## 1. Resumen

- **Kiosco (cliente):** Ante cualquier error de confirmación (talonario, AFIP, stock, etc.) → solo mostrar "El autoservicio se encuentra fuera de servicio". Sin detalles técnicos ni acciones.
- **Panel supervisor (UI separada):** Solo usuarios con permiso `self_checkout.supervisor` o `admin`. Permite:
  - Consultar numeración AFIP vs AdministraNET por talonario.
  - Sincronizar talonarios con AFIP (actualizar `Nro`).
  - Ver carritos en error de confirmación.
  - Reintentar confirmación de un carrito.
  - Eliminar carritos en error.

---

## 2. Permisos y accesos

| Recurso | Permiso | Nota |
|---------|---------|------|
| Panel supervisor (todo) | `self_checkout.supervisor` o `self_checkout.admin` | Ya existe en constantes_permisos |
| Talonarios lista/editar | `self_checkout.admin` | Ya existe |
| Carritos pendientes | `self_checkout.supervisor` | Ya existe |
| Consulta AFIP / Sincronizar talonario | `self_checkout.supervisor` | Nuevo |

**No se crean permisos nuevos.** Se reutiliza `self_checkout.supervisor` para todas las operaciones de recuperación y sincronización.

---

## 3. Cambios en el kiosco (experiencia del cliente)

### 3.1. Errores de confirmación → siempre "Fuera de servicio"

Actualmente:
- `E_AFIP_UNAVAILABLE` → modal "Fuera de servicio"
- `E_CONFIRM_FAILED` (ej. talonario) → toast con mensaje técnico
- `E_STOCK_INSUFFICIENT` → toast con mensaje

**Cambio:** Cualquier error de confirmación en el kiosco debe mostrar solo el modal "Fuera de servicio" (sin detalles). El cliente no debe ver mensajes técnicos ni opciones de "Reintentar" o "Sincronizar".

**Implementación:**
- En `api_views.cart_confirm`: para respuestas de error, devolver un único código `E_SERVICE_UNAVAILABLE` (o reutilizar `E_AFIP_UNAVAILABLE` ampliado) cuando sea un error "operacional" (talonario, AFIP, stock, DB, etc.).
- En `kiosco.html` `confirmarVenta()`: si `!ok` en la respuesta de confirm → siempre mostrar `modalFueraDeServicio = true` (no distinguir por código). Eliminar el toast con el mensaje de error en ese flujo.
- Mensaje del modal: genérico "El autoservicio se encuentra fuera de servicio. Solicitá asistencia." (sin "Solicitar asistencia" como botón funcional si no está definido; o un botón "Cerrar" que solo cierre el modal).

### 3.2. Estado del carrito tras error

Cuando `confirmation_service.confirmar` falla, hace rollback. El carrito permanece en `pago_aprobado` (no hay INSERT en cuentacliente ni stock).

**Nuevo:** Persistir que hubo un intento fallido para que el panel supervisor pueda listar estos carritos:
- Opción A: Agregar columna `ultimo_error_confirmacion` y `ultimo_intento_confirmacion` en `self_checkout_cart`. Cuando falla confirm, hacer UPDATE (fuera del transaction de confirmar) para guardar código y timestamp.
- Opción B: Crear tabla `self_checkout_confirm_attempt` (cart_id, error_code, error_msg, created_at) para historial.
- **Recomendación:** Opción A más simple. Columna `estado` ya soporta `error` (ver 001_self_checkout_tables.sql). Usar estado `error_confirmacion` cuando falle la confirmación y guardar `ultimo_error_confirmacion` en un campo nuevo.

**SQL (migración):**
```sql
ALTER TABLE self_checkout_cart
  ADD COLUMN ultimo_error_confirmacion VARCHAR(512) DEFAULT NULL,
  ADD COLUMN ultimo_intento_confirmacion DATETIME DEFAULT NULL;
```
Y ampliar el comentario de `estado`: `'borrador|pago_pendiente|pago_aprobado|error_confirmacion|confirmado|cancelado|error'`.

**Flujo backend:** En `api_views.cart_confirm` y `cart_confirm_pending`, cuando `conf_svc.confirmar` retorna `ok=False`, antes de devolver el error:
1. UPDATE self_checkout_cart SET estado='error_confirmacion', ultimo_error_confirmacion=error_msg, ultimo_intento_confirmacion=NOW() WHERE id=cart_id.

(Requiere que el UPDATE use la misma conexión/transacción que el rollback... En realidad el confirmar hace rollback de toda la transacción, por lo que no hay cambios en cuentacliente. El carrito sigue en pago_aprobado. El UPDATE del estado del carrito debería hacerse en una conexión separada o después del rollback, porque si está en la misma transacción se rollbackea también. Mejor: hacer el UPDATE en api_views después de recibir ok=False, con una nueva conexión/transacción. Así el carrito pasa a error_confirmacion.)

---

## 4. Panel supervisor – estructura

### 4.1. URL y navegación

Nueva ruta principal: **Panel supervisor** que agrupa:

- Carritos en error (recuperación)
- Sincronización talonarios (ya existe talonarios_list; se añade el botón/modal)

**URLs propuestas:**

| Ruta | Vista | Descripción |
|------|-------|-------------|
| `/self-checkout/config/panel-supervisor/` | `panel_supervisor_view` | Hub: enlaces a Carritos en error y Talonarios |
| `/self-checkout/config/carritos-pendientes/` | (existente) | Lista carritos pago_aprobado. **Ampliar** para incluir carritos en `error_confirmacion`. |
| `/self-checkout/config/carritos-error/` | `carritos_error_view` | Lista solo carritos en `error_confirmacion` (opcional: puede ser una pestaña/filtro en carritos_pendientes) |
| `/self-checkout/talonarios/` | (existente) | Lista talonarios. **Añadir** botón "Consultar AFIP" por fila. |

**Alternativa más simple:** No crear "panel-supervisor" como hub. Usar:
- **Carritos pendientes** (`/self-checkout/config/carritos-pendientes/`) como pantalla principal del supervisor. Incluir pestañas o sección "Carritos en error de confirmación" además de "Pago aprobado sin comprobante".
- **Talonarios** (`/self-checkout/talonarios/`) añadir el botón "Consultar AFIP" + modal de sincronización.

### 4.2. Carritos pendientes – ampliación

**Listado detallado:** Una sola tabla con columnas: Nro carrito, Estado, Autoservicio, Total, Nro factura (si existe), Forma de pago. **Un solo botón principal** por carrito según la tarea pendiente:

| Estado carrito | Acción del botón |
|----------------|------------------|
| `confirmado` con factura | **Reimprimir** ticket/factura |
| `pago_aprobado` (pago MP sincronizado) | **Emitir comprobante** |
| `error_confirmacion` | **Reintentar** emisión |
| `pago_pendiente` / `borrador` sin pago local | **Buscar pago en MP** → si hay match → emitir comprobante |
| `borrador` (abandonado) | **Eliminar** |

**Carritos borrador:**
- Un carrito en `borrador` puede estar **abandonado** (cliente se fue sin pagar). En el listado debe poder **eliminarse**.
- Un `borrador` puede **recuperarse en el autoservicio** para modificar, eliminar o agregar ítems; el proceso continúa desde el mismo autoservicio (URL del kiosco con cart_id).
- Para `borrador`: si hay `payment_intent` asociado, ofrecer "Buscar pago en MP"; además, ofrecer "Eliminar" para abandonados.

**Cambios en la vista `carritos_pendientes_view`:**
- Incluir carritos con `estado ∈ { pago_aprobado, error_confirmacion, pago_pendiente, borrador }`.
- Mostrar columna "Estado" y determinar la acción según la tabla anterior.

**Cambios en el template `carritos_pendientes.html`:**
- Tabla unificada con un botón principal por fila según estado.
- "Reintentar": `POST /api/self-checkout/cart/<id>/confirm-pending/`. Si ok, quitar de la lista. Si error, toast con el mensaje.
- "Eliminar": `POST /api/self-checkout/cart/<id>/cancel/` (estado `cancelado`). Para carritos en `error_confirmacion`, `pago_aprobado` o `borrador`.

### 4.3. Talonarios – botón "Consultar AFIP" y modal

**En `talonarios_list.html`** (o `talonarios_edit.html`):
- Por cada fila de talonario, añadir botón "Consultar AFIP" (junto a "Modificar").
- Al hacer clic, abrir un modal que:
  1. Llame a `GET /api/self-checkout/talonarios/<id_pv>/<tipo>/consulta-afip/` para obtener:
     - `ultimo_afip`: último número autorizado en AFIP
     - `proximo_afip`: ultimo_afip + 1 (próximo a usar)
     - `nro_talonario`: Nro actual en talonarios (AdministraNET)
  2. Muestre: "Último en AFIP: N", "Próximo en AFIP: N+1", "Próximo en AdministraNET: M".
  3. Si M ≠ N+1, botón "Sincronizar: poner Nro = N+1".
  4. Al hacer "Sincronizar", `POST /api/self-checkout/talonarios/<id_pv>/<tipo>/sincronizar/` con body `{ "nro": N+1 }`.

**Permiso:** Solo `self_checkout.supervisor` (o admin, que ya lo incluye).

---

## 5. API – nuevos endpoints

### 5.1. GET `/api/self-checkout/talonarios/consulta-afip/`

**Query params:** `id_punto_venta`, `tipo_comprobante`  
**Permiso:** `supervisor`  
**Respuesta exitosa (200):**
```json
{
  "id_punto_venta": 1,
  "tipo_comprobante": "FC",
  "ultimo_afip": 1,
  "proximo_afip": 2,
  "nro_talonario": 1,
  "sincronizado": false
}
```
`sincronizado`: true si nro_talonario == proximo_afip.

**Respuesta error AFIP (200 con ok: false):**
```json
{
  "ok": false,
  "error": "No se pudo conectar con AFIP: ..."
}
```

### 5.2. POST `/api/self-checkout/talonarios/sincronizar/`

**Body:** `{ "id_punto_venta": 1, "tipo_comprobante": "FC", "nro": 2 }`  
**Permiso:** `supervisor`  
**Acción:** `UPDATE talonarios SET Nro = nro WHERE id_punto_venta AND TipoComprobante`  
**Respuesta (200):**
```json
{
  "ok": true,
  "id_punto_venta": 1,
  "tipo_comprobante": "FC",
  "nro_actualizado": 2
}
```

### 5.3. POST `/api/self-checkout/cart/<id>/cancel/` (eliminar carrito)

**Permiso:** `supervisor`  
**Condiciones:** Solo si estado ∈ { `pago_aprobado`, `error_confirmacion`, `borrador` }.  
**Acción:** `UPDATE self_checkout_cart SET estado = 'cancelado' WHERE id = ?`  
**Respuesta (200):**
```json
{ "ok": true }
```

Permite cancelar carritos abandonados en borrador y carritos en error o pago_aprobado sin comprobante que no se van a recuperar.

---

## 6. Cambios en backend (archivos)

| Archivo | Cambios |
|---------|---------|
| `api_views.py` | 1) En `cart_confirm` y `cart_confirm_pending`, al fallar: UPDATE cart estado=error_confirmacion, ultimo_error. 2) Tratar error talonario como "fuera de servicio" (mismo código que AFIP para kiosco). 3) Nuevos endpoints: consulta-afip, sincronizar, cart cancel. |
| `kiosco.html` | En `confirmarVenta`: ante cualquier error de confirm, mostrar modalFueraDeServicio (no toast con detalle). |
| `views.py` | En `carritos_pendientes_view`: incluir carritos con estado=error_confirmacion. |
| `carritos_pendientes.html` | Sección/filtro carritos en error, botones Reintentar y Eliminar. |
| `talonarios_list.html` | Botón "Consultar AFIP" por fila, modal con consulta y sincronizar. |
| `api_urls.py` | Rutas: talonarios/consulta-afip/, talonarios/sincronizar/, cart/<id>/cancel/ |
| `001_self_checkout_tables.sql` o migración | ALTER cart: ultimo_error_confirmacion, ultimo_intento_confirmacion; estado incluye error_confirmacion |

---

## 7. Detalle: clasificación de errores para el kiosco

En `api_views.cart_confirm`, cuando `conf_svc.confirmar` retorna `ok=False`:

| Tipo de error (por contenido de error_msg) | Código a devolver | Kiosco muestra |
|-------------------------------------------|-------------------|----------------|
| talonario, arca, no coincide | E_SERVICE_UNAVAILABLE o E_AFIP_UNAVAILABLE | Fuera de servicio |
| cae, caea, afip, wsaa, wsfe, etc. | E_AFIP_UNAVAILABLE | Fuera de servicio |
| stock, disponible | E_SERVICE_UNAVAILABLE | Fuera de servicio |
| Otros | E_SERVICE_UNAVAILABLE | Fuera de servicio |

**Conclusión:** Para el kiosco, siempre devolver un código que el frontend interprete como "mostrar fuera de servicio" (p. ej. `E_AFIP_UNAVAILABLE` o nuevo `E_SERVICE_UNAVAILABLE`). El frontend puede simplificar: si confirm falla, mostrar modal fuera de servicio sin inspeccionar el código.

Para **carritos pendientes** (supervisor): sí devolver el mensaje completo en `error` para mostrarlo en toast, de modo que el supervisor pueda ver "No coincide talonario..." u otro detalle y actuar (sincronizar, reintentar, eliminar).

---

## 8. Orden de implementación sugerido

1. **Backend:** ALTER tabla cart (ultimo_error, ultimo_intento); estado error_confirmacion.
2. **Backend:** En `cart_confirm` y `cart_confirm_pending`, al fallar: UPDATE cart a error_confirmacion.
3. **Backend:** Ampliar criterio de "fuera de servicio" para incluir talonario/stock en cart_confirm.
4. **Kiosco:** confirmarVenta → cualquier error → modalFueraDeServicio.
5. **API:** Endpoints consulta-afip, sincronizar, cart cancel.
6. **Talonarios UI:** Botón y modal consulta/sincronización.
7. **Carritos pendientes:** Incluir error_confirmacion, botones Reintentar y Eliminar.
