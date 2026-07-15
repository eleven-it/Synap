# Inventario — Gestión de pedidos Synap vs PHP/VB6

Comparación breve de pantallas y flujos. Detalle campo a campo del listado vendedor: [INVENTARIO_FORMULARIO_PEDIDOS_MAYORISTAPP.md](./INVENTARIO_FORMULARIO_PEDIDOS_MAYORISTAPP.md).

---

## Pantallas principales

| Flujo | PHP / VB6 | Synap | Estado |
|-------|-----------|-------|--------|
| Hub ventas — acceso pedidos | `componente-menu-card-dashboard.php` → `lista-pedidos-vendedor.php` | Hub `GET /ecom/mayoristapp/` → Pedidos + **Nuevo pedido** | ✅ |
| Alta pedido (carrito) | `alta_pedido.php` + `jcart/` | `GET /ecom/mayoristapp/venta/` + APIs carrito/checkout | ✅ (relay `frm=0` → Synap) |
| Confirmación alta | `alta_pedido_confirmado.php` | `POST …/checkout/confirmar/` (`mayorista_checkout_service`) | ✅ |
| Listado pedidos vendedor | `lista-pedidos-vendedor.php` + `relay-pedidos.php` | `pedidos_vendedor.html` + API v1 pedidos | ✅ (PDF/anular UI ⏳) |
| Preparación depósito | `logistica_pantalla_preparacion.php` | `estado_pedidos_preparacion.html` + API Kanban | ✅ |
| Asignar / preparar pedido | VB6 `Pedido_prep` | Sin equivalente web Synap (sigue VB6) | Legacy |
| Remito / factura | VB6 `Remito`, `FacturaA/B` | Informes reports + VB6 | Parcial |
| Anular pedido | `relay-pedidos.php` `anularPedido` | API `anular-pedido` | API ✅ / UI ⏳ |
| Ver PDF pedido | `ver_pedido-movil.php` / mail relay | — | ⏳ gap |
| Repetir pedido | PHP (artículos al carrito) | Política documentada en SPEC; UI según compra | Política ✅ |

---

## Selección de comprobante (portal cliente)

| PHP | Synap |
|-----|--------|
| `seleccionarComprobante` `frm=0` → `alta_pedido.php` | `frm=0` → `/ecom/mayoristapp/venta/` |

---

## API

| PHP | Synap |
|-----|--------|
| `relay-pedidos.php` POST `ajax` camelCase | `POST /ecom/api/v1/mayoristapp/comprobantes/pedidos/` snake_case |
| Respuesta `{ total, filas }` | `{ ok, page, page_size, total, results }` |

---

## Gaps aceptados (piloto)

- PDF y anulación en grilla vendedor.
- Anulación sin reversa automática de `stock_deposito`.
- Edición de pedido confirmado: no soportada (anular + repetir).
- Promociones y PV en formulario de alta legacy: pendientes en compra Synap.
