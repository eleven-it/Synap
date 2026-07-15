# Spec — Gestión de pedidos Synap (mayoristapp)

**Alcance:** alta, consulta, repetición y anulación de pedidos (`PED`) desde el portal mayorista Synap, con persistencia en MySQL AdministraNET (compartido con VB6).  
**Relacionado:** [CHECKOUT_MAYORISTA_P2.md](./CHECKOUT_MAYORISTA_P2.md), [SPEC_MAYORISTAPP_COMPROBANTES.md](./SPEC_MAYORISTAPP_COMPROBANTES.md), [SPEC_ESTADO_PEDIDOS_PREPARACION.md](./SPEC_ESTADO_PEDIDOS_PREPARACION.md), [INVENTARIO_GESTION_PEDIDOS_SYNAP.md](./INVENTARIO_GESTION_PEDIDOS_SYNAP.md).

---

## 1. Proceso: alta → flujo venta AdministraNET

### 1.1 Alta (Synap → MySQL)

| Paso | Actor | Pantalla / API Synap | Efecto |
|------|-------|-------------------|--------|
| 1 | Vendedor o cliente | Selección de cliente (`/ecom/mayoristapp/clientes/` o sesión autogestión) | `mayoristapp.idcliente`, datos de crédito |
| 2 | Vendedor o cliente | **Pedido de venta** → `/ecom/mayoristapp/venta/` (`frm=0` vía relay) | Catálogo + carrito borrador (`EcomCart` Postgres) |
| 3 | Vendedor o cliente | Confirmar checkout `POST /ecom/api/mayoristapp/checkout/confirmar/` | Alta transaccional legacy |
| 4 | Sistema | — | Pedido en `comp_ped` con `Estado='Pendiente'`, `TipoPedido` según origen |
| 5 | Depósito / VB6 | `Pedido_prep`, preparación | `Estado` → `En preparación` / `Preparado` |
| 6 | Logística / VB6 | Remito, facturación | `En remito`, `Facturado`, `Cerrado`, etc. |

**Servicio de alta:** `ecom/services/mayorista_checkout_service.confirmar()`.

**Wiring portal cliente:** `seleccionarComprobante` con `frm=0` ya no apunta a `alta_pedido.php`; devuelve la ruta Synap `/ecom/mayoristapp/venta/` (resuelta con `reverse('ecom:mayoristapp_venta')` en `ClienteComprobanteFormularioRelayAPIView`).

### 1.2 Flujo posterior (fuera de Synap e-com, VB6 / logística)

Tras el alta web, el pedido entra al circuito operativo AdministraNET:

1. **Pendiente** — tomado, sin asignar a preparación.
2. **En preparación** — `Pedido_prep` asigna responsable (`id_usuario_preparacion`).
3. **Preparado** — mercadería lista en depósito.
4. **En remito** — vinculado a remito pendiente (`rem_ped` + `comp_ped` remito).
5. **Parcial / Facturado / Cerrado** — entregas y facturación en VB6.

Synap expone seguimiento en:

- Listado vendedor: `GET /ecom/mayoristapp/pedidos-vendedor/`
- Tablero preparación: `GET /ecom/mayoristapp/logistica/estado-pedidos/`

---

## 2. Tablas persistidas en el alta

| Tabla | Rol en alta PED | Escritor Synap |
|-------|-----------------|----------------|
| `codmov` | Numeración `CodigoMovimiento` (`SELECT … FOR UPDATE`) | `mayorista_checkout_service` |
| `talonarios` | Numeración `NroComprobante` / `NroCompBusq` por PV | `mayorista_checkout_service` |
| `comp_ped` | Cabecera: totales, cliente, PV, sucursal, `Estado`, `TipoPedido`, autorización | `mayorista_checkout_service` |
| `stockp` | Renglones: artículo, cantidad, precios, IVA, descuentos | `mayorista_checkout_service` |
| `stock_deposito` | `saldo_pedido_cliente += cantidad` (reserva stock) | `mayorista_checkout_service` (solo PED) |
| `cliente_datos_adicionales` | Entrega, domicilio, ruta, depósito despacho | `mayorista_checkout_service` |
| `percep_cli` | Percepciones IIBB por tipo (si sucursal agente) | `mayorista_percepciones` + checkout |
| `EcomCart` (Postgres) | Carrito borrador e idempotencia post-confirmación | `mayorista_cart_service` / checkout |

**Lectura (no escritura en alta):** `cliente`, `cuentacliente`, `credito_limite_dias`, `articulo`, `stock_deposito` (validación disponible).

**Anulación** (`anular_pedido_relay`): marca `Anulado='Si'` en `comp_ped`, `stockp`, `percep_cli` — ver gaps §6.

---

## 3. Estados y quién los escribe

| Campo / estado | Valor inicial (alta Synap) | Quién lo cambia después |
|----------------|---------------------------|-------------------------|
| `comp_ped.Estado` | `Pendiente` | VB6 `Pedido_prep`, remitos, facturación |
| `comp_ped.Anulado` | `No` | Synap `anular_pedido_relay` o VB6 |
| `comp_ped.autorizacion_sistema` | `Autorizado` / `No Autorizado` | Synap en checkout (`mayorista_credito`) |
| `comp_ped.TipoPedido` | `Ecom vendedor` / `Ecom cliente` | Synap en checkout |
| `stockp.Anulado` | `No` | Synap anulación o VB6 |
| `stock_deposito.saldo_pedido_cliente` | Incremento en alta PED | VB6 al preparar/remitir/facturar; **no** revertido hoy en anulación Synap |

Referencias de estados: `reports/docs/VALIDACION_PEDIDOS_PENDIENTES.md` §3.1.

---

## 4. Actores: vendedor vs cliente (autogestión)

| Aspecto | Vendedor | Cliente autogestión |
|---------|----------|---------------------|
| Entrada nuevo pedido | Hub → **Pedido de venta** o menú; `frm=0` tras elegir cliente | Misma ruta `/ecom/mayoristapp/venta/`; sesión con su `idcliente` |
| Checkout `es_cliente` | `false` | `true` |
| `TipoPedido` | `Ecom vendedor` | `Ecom cliente` |
| Autorización crédito | Evalúa límite de días (`mayorista_credito`) | Siempre `No Autorizado` (no bloquea alta) |
| Listado pedidos | `/ecom/mayoristapp/pedidos-vendedor/` (filtro vendedor/viajante) | Mismo listado filtrado por su cliente en sesión |
| Permisos mínimos | `ecom.pedidos.crear` + `ecom.pedidos.ver` (ver §5) | `ecom.carrito.editar` (autogestión portal cliente) |

---

## 5. Permisos

| Código | Uso | Equivalencia actual |
|--------|-----|---------------------|
| `ecom.pedidos.crear` | Alta de pedido (compra + checkout) | Hoy cubierto por `ecom.carrito.editar` |
| `ecom.pedidos.ver` | Listado y detalle de pedidos | Hoy cubierto por `ecom.comprobantes.ver` |
| `ecom.pedidos.ver_todos` | Listado gerencial sin filtro de vendedor | `todos_clientes=Si` en sesión legacy o permiso Synap |
| `ecom.comprobantes.anular` | Anular pedido desde API | UI en grilla y detalle |

Los permisos `ecom.pedidos.*` se registran en `core/constantes_permisos.py` para granularidad futura; menú y API v1 siguen aceptando las equivalencias anteriores hasta migración de roles.

---

## 6. Políticas de negocio

### 6.1 Repetir pedido

- **Qué se copia:** solo **artículo + cantidad** del pedido origen.
- **Precios:** siempre **precios actuales** del motor (`resolver_precio_articulo` en el commit del carrito).
- **Cliente (autogestión):** no ve precios históricos del pedido repetido; solo totales recalculados en carrito/checkout.
- **Vendedor:** al repetir puede ver precios del pedido origen como **referencia informativa** (no vinculantes al commit).

### 6.2 Pedido confirmado: editar vs consulta

| Estado | Shell `/venta/?cod_mov=` | Comportamiento |
|--------|-------------------------|----------------|
| `Pendiente` y no anulado | **Editar** | Líneas en carrito; al confirmar → modal Synap → anula origen + checkout nuevo (nuevo `CodigoMovimiento`) |
| Otro estado / anulado | **Consulta** | Solo lectura; Repetir / PDF / mail; Anular solo si API `puede_anular` |

No hay UPDATE in-place de renglones sobre el mismo `CodigoMovimiento`.  
`GET /ecom/mayoristapp/pedidos/<cod_mov>/` redirige a `/venta/?cod_mov=`.

---

## 7. Gaps conocidos

| Gap | Descripción | Estado |
|-----|-------------|--------|
| **Anulación sin reversa de stock** | `anular_pedido_relay` decrementa `stock_deposito.saldo_pedido_cliente` en PED Pendiente | Resuelto |
| **PDF comprobante** | `GET …/comprobantes/pedidos/<cod_mov>/pdf/` + botones en listado y detalle | Resuelto |
| **Anular desde grilla** | Acción Anular en `pedidos_vendedor.html` | Resuelto |
| **Promociones en línea** | Etiqueta de promo en catálogo y carrito (`promocion_etiqueta`) | Resuelto v1 |
| **Punto de venta en formulario** | Selector PV desde `listar_puntos_venta_usuario` en compra | Resuelto |
| **Selector cliente en compra** | Búsqueda y selección embebida para vendedor | Resuelto |
| **Stepper estado en detalle** | Ciclo comercial solo lectura + remitos vinculados | Resuelto |
| **Portal cliente repetir** | Acciones Ver/Repetir en listado `pedidos-cliente` | Resuelto |
| **Hub repetir último** | Atajo con cliente seleccionado (vendedor) | Resuelto |
| **Bloqueo anulación remito/factura** | PHP valida `ped_fact`/`rem_ped`; Synap solo `Estado=Pendiente` | Abierto P0 — ver RE `14-functional-equivalence-matrix.md` |
| **Domicilio / hoja ruta en OrderShell** | Backend acepta; UI `/venta/` no envía | Abierto P1 |
| **Filtro TipoPedido** | Opciones `Web`/`Sistema` vs persistido `Ecom vendedor`/`Ecom cliente` | Abierto P1 |

## 8. Backlog post-v1 (implementado)

| Ítem | Descripción | Estado |
|------|-------------|--------|
| **PRE → PED** | `POST …/presupuestos/<cod_mov>/convertir-pedido/` + botón en listado presupuestos | Resuelto |
| **Widget crédito en compra** | Saldo CC, límite días y autorización en `compra/contexto` | Resuelto |
| **Motivo obligatorio al anular** | Campo `motivo` en API; se persiste en `comp_ped.Detalle` | Resuelto |
| **Mail automático al crear PED** | `encolar_comprobante_mail` tras checkout confirmado | Resuelto |
| **Pallet / embalaje** | Selector Unidad/Display/Bulto/Pallet en catálogo y carrito | Resuelto v1 |

### Mejoras UX (jul 2026)

| Pantalla | Cambio |
|----------|--------|
| Hub | KPI «Sin autorizar» clicable; iconos en cards; eyebrow unificado |
| Compra | Breadcrumb; aviso cliente progresivo; **búsqueda predictiva** de cliente (dropdown único, `ecom_predictive.mjs`) |
| Listado | Auto-carga al entrar; skeleton; empty states diferenciados; tiempo real inactivo en slate |
| Layout | Clase `.pedidos-contenido`: sin solapamiento del card sobre el hero oscuro |
| **System Design** | Layout canónico `ecom/base_pedidos.html` + `includes/pedidos_page_styles.html` + `pedidos_shell.js` en todas las pantallas del módulo (hub, listado, detalle, compra, presupuestos) |

### Artefactos UI canónicos (jul 2026)

| Archivo | Rol |
|---------|-----|
| `ecom/templates/ecom/base_pedidos.html` | Extiende `base_app.html`; hero slate, eyebrow «Ventas · Pedidos», bloques `pedidos_*` |
| `ecom/templates/ecom/includes/pedidos_page_styles.html` | Tokens CSS: `.pedidos-btn-*`, `.pedidos-card`, `.pedidos-workspace`, `.pedidos-table`, filtros, fullscreen |
| `ecom/templates/ecom/includes/pedidos_breadcrumb.html` | Breadcrumb unificado |
| `ecom/templates/ecom/includes/pedidos_hero_actions_*.html` | Acciones hero por pantalla (listado, presupuestos, detalle) |
| `ecom/templates/ecom/includes/pedidos_alert_desktop.html` | Aviso preparación/remito desktop |
| `ecom/static/ecom/js/pedidos_shell.js` | Filtros toggle y pantalla completa (compartido) |

Referencia visual: **docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md** (familia reportes slate/sky). No usar patrones PHP ni pantallas legacy de `ventas/presupuesto_*` como referencia.

---

## 9. Rutas Synap (resumen)

| Acción | Ruta |
|--------|------|
| Hub gestión pedidos | `GET /ecom/mayoristapp/pedidos/` (menú **Ventas → Comprobantes → Pedidos**) |
| Pedido de venta (UI) | `GET /ecom/mayoristapp/venta/` (`?cod_mov=` abre PED) |
| Alias compra (redirect) | `GET /ecom/mayoristapp/compra/` → `/venta/` |
| Detalle legacy (redirect) | `GET /ecom/mayoristapp/pedidos/<cod_mov>/` → `/venta/?cod_mov=` |
| Confirmar alta | `POST /ecom/api/mayoristapp/checkout/confirmar/` |
| Listado vendedor | `GET /ecom/mayoristapp/pedidos-vendedor/` |
| API listado v1 | `POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/` |
| Relay formulario pedido | `GET /ecom/api/mayoristapp/clientes/comprobante-formulario/?ajax=1&frm=0` |
| Anular | `POST /ecom/api/mayoristapp/comprobantes/anular-pedido/?ajax=1` |
