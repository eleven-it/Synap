# Inventario funcional — Rediseño UI de pedidos (mayoristapp)

**Proyecto:** Synap · módulo `ecom` (mayoristapp)  
**Fecha de referencia:** 10/07/2026  
**Alcance:** inventario funcional verificado en código para el rediseño de la experiencia de toma de pedido, listados y detalle. No incluye cambios de backend.

**Documentos relacionados:** `08-plan-implementacion.md`, `09-checklist-regresion.md`, `docs/ecom/SPEC_GESTION_PEDIDOS_SYNAP.md`, `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`.

---

## 1. Objetivo

Registrar el estado actual (10/07/2026) de las pantallas de pedidos mayoristapp en Synap: rutas, vistas, plantillas, stack front-end, matriz funcional SÍ/NO/PARCIAL, endpoints de compra y reglas de negocio expuestas en UI. Sirve de base para el rediseño incremental sin romper contratos API ni servicios backend.

---

## 2. Mapa de pantallas

| Pantalla | Ruta web | Vista Django | Plantilla principal | JS / estado |
|----------|----------|--------------|---------------------|-------------|
| **Hub** | `/ecom/mayoristapp/pedidos/` | `PedidosHubView` (`ecom/pedido_gestion_views.py`) | `ecom/templates/ecom/pedidos_hub.html` | `pedidos_shell.js`; KPIs vía API |
| **Compra (toma pedido)** | `/ecom/mayoristapp/compra/` | `CompraMayoristaView` (`ecom/mayoristapp_web_views.py`) | `ecom/templates/ecom/compra_mayorista.html` | Alpine 3 inline (`compraMayorista()`); módulos `compra_mayorista_cliente.mjs`, `compra_mayorista_marcas.mjs` |
| **Listado pedidos** | `/ecom/mayoristapp/pedidos-vendedor/` | `PedidosVendedorView` (`ecom/mayoristapp_web_views.py`) | `ecom/templates/ecom/pedidos_vendedor.html` | `ecom/static/ecom/js/pedidos_vendedor.js` |
| **Detalle PED** | `/ecom/mayoristapp/pedidos/<cod_mov>/` | `PedidoDetalleView` (`ecom/pedido_gestion_views.py`) | `ecom/templates/ecom/pedido_detalle.html` | `pedidos_shell.js` |
| **Presupuestos** | `/ecom/mayoristapp/presupuestos-vendedor/` | `PresupuestosVendedorView` (`ecom/mayoristapp_web_views.py`) | `ecom/templates/ecom/presupuestos_vendedor.html` | `presupuestos_vendedor.js` |
| **Detalle PRE / DEV** | `/ecom/mayoristapp/comprobantes/<cod_mov>/` | `ComprobanteComercialDetalleView` (`ecom/pedido_gestion_views.py`) | `ecom/templates/ecom/comprobante_detalle.html` (o equivalente en plantilla) | `pedidos_shell.js` |

**Prefijo URL raíz:** `django_project/urls.py` monta `ecom/` → todas las rutas anteriores llevan prefijo `/ecom/`.

---

## 3. Stack front-end

| Capa | Tecnología | Archivos canónicos |
|------|------------|-------------------|
| Layout pedidos | Django templates + herencia | `ecom/templates/ecom/base_pedidos.html` |
| Estilos compartidos | Tailwind + CSS custom pedidos | `ecom/templates/ecom/includes/pedidos_page_styles.html` |
| Shell / utilidades | JS vanilla | `ecom/static/ecom/js/pedidos_shell.js` |
| Interactividad compra | Alpine.js 3 (componente monolítico en plantilla) | Bloque `<script>` en `compra_mayorista.html` |
| Módulos ES parciales | `.mjs` | `compra_mayorista_cliente.mjs`, `compra_mayorista_marcas.mjs`, `ecom_predictive.mjs` |
| Listados | JS vanilla | `pedidos_vendedor.js`, `presupuestos_vendedor.js` |
| HTMX | **No utilizado** en flujo pedidos mayoristapp | — |

### 3.1 Includes reutilizables (pedidos)

- `ecom/includes/pedidos_breadcrumb.html`
- `ecom/includes/pedidos_toggle_comprobante.html` (PED / PRE / DEV)
- `ecom/includes/pedidos_busqueda_articulos_tpv.html`
- `ecom/includes/pedidos_hero_actions_*.html` (listado, detalle, presupuestos)
- `ecom/includes/pedidos_alert_desktop.html`
- `ecom/includes/repetir_pedido_modal.html` + `repetir_pedido_modal.js`

### 3.2 Fuente de verdad visual

Patrón canónico Synap: familia reportes slate/sky y módulo MPR (`docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md`). El layout `base_pedidos.html` replica hero, breadcrumb y contenedor de `reports/dashboard` / `mpr/wizard`.

---

## 4. Matriz funcional (estado actual)

Leyenda: **SÍ** = disponible en UI; **NO** = no expuesto en UI (puede existir API/backend); **PARCIAL** = implementado de forma limitada o solo en ciertos modos.

| # | Funcionalidad | Estado | Notas verificadas |
|---|---------------|--------|-------------------|
| 1 | Selección de cliente | **SÍ** | Autocomplete vendedor; autogestión con cliente en sesión |
| 2 | Alta rápida de cliente | **NO** | API `clientes/rapido/` existe; sin formulario en compra |
| 3 | Búsqueda de clientes | **SÍ** | `GET/POST` relay `clientes/buscar/` |
| 4 | Listas de precios | **PARCIAL** | Se aplica lista del cliente; sin selector manual en UI |
| 5 | Condición de venta | **PARCIAL** | Heredada del cliente; sin combo editable en compra |
| 6 | Vendedor / viajante | **PARCIAL** | Sesión del usuario; filtro en listado, no en alta |
| 7 | Sucursal | **NO** | Backend usa sucursal de sesión; sin selector UI |
| 8 | Depósito | **NO** | Backend resuelve depósito; sin selector UI |
| 9 | Fecha de pedido | **NO** | Fecha servidor al confirmar; sin datepicker |
| 10 | Fecha de entrega | **PARCIAL** | Campo texto en checkout; validación limitada |
| 11 | Moneda | **NO** | Moneda implícita de empresa |
| 12 | Productos / catálogo | **SÍ** | Grilla + búsqueda POST `catalogo/articulos/listado/` |
| 13 | Variantes de artículo | **NO** | Un ítem por `idart` |
| 14 | UOM / presentaciones | **PARCIAL** | API detalle soporta; UI no elige presentación |
| 15 | Cantidades | **SÍ** | PATCH ítem carrito |
| 16 | Precios | **SÍ** (solo lectura) | Mostrados desde `serializar_carrito`; UI no recalcula |
| 17 | Descuento pie | **SÍ** | Relay `carrito/descuento-pie/` |
| 18 | Descuento renglón | **API only** | Backend acepta; sin control en UI compra |
| 19 | Promociones | **SÍ** | Motor en `catalogo_producto` + carrito |
| 20 | Impuestos / IVA | **SÍ** | Totales desde backend |
| 21 | Stock disponible | **SÍ** | Validación PED/PRE en carrito y checkout |
| 22 | Stock comprometido | **NO** | No se muestra `saldo_pedido_cliente` en UI |
| 23 | Observaciones | **SÍ** | Textarea en panel checkout |
| 24 | Entrega (texto) | **PARCIAL** | Campo libre; sin catálogo de rutas |
| 25 | Dirección de entrega | **NO** | API `clientes/domicilio/` existe; sin selector |
| 26 | Transporte | **NO** | — |
| 27 | Notas internas | **NO** | — |
| 28 | Totales (subtotal, IVA, total) | **SÍ** | Siempre desde respuesta `serializar_carrito` |
| 29 | Confirmar comprobante | **SÍ** | `POST checkout/confirmar/` |
| 30 | Guardar borrador | **SÍ** | `EcomCart` Postgres; persiste entre requests |
| 31 | Edición pedido confirmado | **NO** | Pedido legacy inmutable desde Synap |
| 32 | Duplicar / repetir pedido | **SÍ** | `carrito/desde-pedido/` + modal repetir |
| 33 | Eliminar líneas | **SÍ** | `DELETE carrito/items/<id>/` |
| 34 | Validaciones UI | **SÍ** | Cliente obligatorio, stock, mensajes flash |
| 35 | Estados loading / empty | **SÍ** | Spinners grilla, mensajes vacíos |
| 36 | Código de barras | **PARCIAL** | Búsqueda por código en catálogo; sin lector dedicado |
| 37 | Atajos de teclado | **SÍ** | Navegación búsqueda artículos (↑↓ Enter) |
| 38 | PRE → PED (convertir) | **SÍ** | API `presupuestos/<cod_mov>/convertir-pedido/` + UI detalle |

---

## 5. Endpoints clave — flujo compra

Base: `/ecom/api/mayoristapp/`. Los nombres de ruta Django están en `ecom/urls.py`.

### 5.1 Contexto y sesión

| Método | Endpoint | Vista relay | Uso en UI |
|--------|----------|-------------|-----------|
| GET | `compra/contexto/` | `CompraMayoristaContextoAPIView` | PV, cliente activo, tipo comprobante, crédito |
| GET | `clientes/seleccionado/` | `ClienteSeleccionadoRelayAPIView` | Widget crédito post-selección |
| POST | `clientes/buscar/` | `ClienteBuscarRelayAPIView` | Autocomplete cliente |
| POST | `clientes/seleccionar/` | `ClienteSeleccionarRelayAPIView` | Fijar cliente en sesión |

### 5.2 Catálogo

| Método | Endpoint | Vista relay | Uso en UI |
|--------|----------|-------------|-----------|
| POST | `catalogo/articulos/listado/` | `CatalogoArticulosListadoRelayAPIView` | Grilla y búsqueda productos |
| GET | `catalogo/marcas/` | `CatalogoMarcasRelayAPIView` | Filtro marcas (panel vendedor) |
| GET | `catalogo/articulos/<idart>/detalle/` | `CatalogoArticuloDetalleRelayAPIView` | Detalle (API; UI limitada) |

### 5.3 Carrito

| Método | Endpoint | Vista relay | Uso en UI |
|--------|----------|-------------|-----------|
| GET | `carrito/` | `CarritoRelayAPIView` | Estado completo (`serializar_carrito`) |
| POST | `carrito/` | `CarritoRelayAPIView` | Agregar línea |
| PATCH | `carrito/items/<id>/` | `CarritoItemRelayAPIView` | Cantidad / datos ítem |
| DELETE | `carrito/items/<id>/` | `CarritoItemRelayAPIView` | Quitar línea |
| POST | `carrito/vaciar/` | `CarritoVaciarRelayAPIView` | Limpiar borrador |
| PATCH | `carrito/descuento-pie/` | `CarritoDescuentoPieRelayAPIView` | Descuento global |
| PATCH | `carrito/tipo-comprobante/` | `CarritoTipoComprobanteRelayAPIView` | Toggle PED / PRE / DEV |

### 5.4 Checkout y repetición

| Método | Endpoint | Vista relay | Uso en UI |
|--------|----------|-------------|-----------|
| POST | `checkout/confirmar/` | `CheckoutConfirmarRelayAPIView` | Alta transaccional legacy |
| GET | `pedidos/recientes/` | `PedidosRecientesAPIView` | Chips repetir pedido |
| GET | `carrito/desde-pedido/<cod_mov>/preview/` | `CarritoDesdePedidoPreviewAPIView` | Modal repetir (resumen) |
| POST | `carrito/desde-pedido/` | `CarritoDesdePedidoAPIView` | Cargar plantilla en carrito |
| POST | `presupuestos/<cod_mov>/convertir-pedido/` | `PresupuestoConvertirPedidoAPIView` | PRE → PED desde detalle |

### 5.5 Precios auxiliares

| Método | Endpoint | Notas |
|--------|----------|-------|
| GET/POST | `precios/lista-precio/` | Lista precio del cliente |
| GET/POST | `precios/promociones/` | Promos aplicables |

### 5.6 Cliente — APIs sin UI en compra

| Endpoint | Estado UI |
|----------|-----------|
| `clientes/rapido/` | API alta rápida; **sin formulario** |
| `clientes/domicilio/` | API domicilios; **sin selector** |
| `clientes/domicilio/opciones-visita/` | API rutas visita; **sin selector** |
| `clientes/contacto/` | API contacto; **sin formulario** |

---

## 6. Reglas de negocio expuestas en UI

### 6.1 Precios y totales

- La UI **no calcula** precios, descuentos ni IVA localmente.
- Toda visualización de importes proviene de `mayorista_cart_service.serializar_carrito()` en respuestas GET/PATCH/POST del carrito y tras checkout idempotente.
- Tras cada mutación de carrito, Alpine reemplaza estado desde `data.carrito` del JSON.

### 6.2 Sesión vendedor vs cliente

| Regla | Comportamiento |
|-------|----------------|
| GET compra (vendedor) | `CompraMayoristaView.dispatch`: limpia cliente en sesión y reinicia borrador `EcomCart` (`reiniciar_borrador_compra_vendedor`) |
| GET compra (cliente autogestión) | Mantiene `idcliente` de sesión; no limpia carrito al entrar |
| Cambio de cliente (vendedor) | Seleccionar otro cliente vacía carrito y recarga contexto |
| Tipo usuario | `tipousuario == 'cliente'` oculta panel búsqueda cliente |

### 6.3 Stock

| Tipo comprobante | Validación stock en carrito/checkout |
|------------------|--------------------------------------|
| PED | **SÍ** — bloqueo o warning según disponibilidad |
| PRE | **SÍ** — misma validación que PED |
| DEV | **NO** — devolución no valida stock disponible |

### 6.4 Ciclo de vida del comprobante

- Pedido **confirmado** (`comp_ped` en MySQL) **no es editable** desde Synap; solo consulta, PDF, mail, anulación (listado/detalle).
- Borrador vive en **Postgres** (`EcomCart` + ítems); se pierde al vaciar, cambiar cliente (vendedor) o confirmar exitoso.
- POST checkout es **idempotente** por carrito: reintento devuelve resultado previo sin duplicar alta.

### 6.5 Relay legacy `ajax=1`

Muchos endpoints de listados, comprobantes, ctacte y estadísticas del ecosistema mayoristapp siguen aceptando `?ajax=1` para compatibilidad PHP. El flujo **compra/carrito/checkout** usa REST JSON sin `ajax=1`. El listado pedidos vendedor consume API v1 (`POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/`).

---

## 7. Archivos backend — fuera de alcance del rediseño UI

**No modificar** en el rediseño de interfaz (contratos estables):

| Área | Paths |
|------|-------|
| Vistas gestión pedidos | `ecom/pedido_gestion_views.py` |
| API REST v1 pedidos | `ecom/api/v1/comprobantes/pedidos.py` |
| Relays compra/carrito | `ecom/carrito_relay_views.py`, `ecom/checkout_relay_views.py` |
| Relays cliente/catálogo | `ecom/cliente_relay_views.py`, `ecom/catalogo_relay_views.py`, `ecom/catalogo_producto_relay_views.py` |
| Servicios dominio | `ecom/services/mayorista_cart_service.py`, `ecom/services/mayorista_checkout_service.py`, `ecom/services/pedido_plantilla_service.py` |
| Modelo borrador | `ecom/models.py` (`EcomCart`, ítems) |
| Permisos | `ecom/services/pedido_permisos.py`, `core/constantes_permisos.py` (permisos `ecom.*`) |
| Config entorno | `.env` |

El rediseño UI limita cambios a **templates**, **static JS/CSS** e **includes** bajo `ecom/templates/` y `ecom/static/ecom/`.

---

## 8. Permisos relevantes

| Permiso | Efecto |
|---------|--------|
| `ecom.carrito.editar` | Usar carrito y checkout mayorista |
| `ecom.pedidos.crear` | Crear pedidos (compra / confirmar) |
| `ecom.pedidos.ver` | Listados y detalle |
| Sesión `tipousuario` | `cliente` vs vendedor altera paneles y limpieza de sesión |

---

## 9. Gaps funcionales priorizados para el rediseño

1. **PARCIAL → SÍ:** fecha entrega con datepicker, dirección desde `clientes/domicilio/`, selector lista de precios.
2. **API only → UI:** descuento renglón, alta rápida cliente.
3. **NO → evaluar:** sucursal, depósito, moneda, notas internas, transporte (requieren decisión de producto y posible extensión backend).
4. **Modularización front:** extraer Alpine monolítico de `compra_mayorista.html` a módulos `.mjs` sin cambiar payloads API.

---

## 10. Referencias de código

| Artefacto | Path |
|-----------|------|
| URLs mayoristapp | `ecom/urls.py` |
| Vista compra | `ecom/mayoristapp_web_views.py` → `CompraMayoristaView` |
| Vista hub | `ecom/pedido_gestion_views.py` → `PedidosHubView` |
| Serialización carrito | `ecom/services/mayorista_cart_service.py` → `serializar_carrito` |
| Checkout | `ecom/services/mayorista_checkout_service.py` |
| Tests vista compra | `ecom/tests/test_compra_mayorista_view.py` |
| Tests carrito | `ecom/tests/test_mayorista_cart_service.py` |

---

*Última actualización: 10/07/2026.*
