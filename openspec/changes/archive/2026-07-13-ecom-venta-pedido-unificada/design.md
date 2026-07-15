# Design — Pedido de venta unificado

**Change:** `ecom-venta-pedido-unificada`  
**Fecha:** 13/07/2026  
**Canon UI:** OrderShell `base_pedidos` + tablero slate (compra actual).  
**Idioma UI:** español.

## 1. Navegación

| Ruta | Comportamiento |
|------|----------------|
| `GET /ecom/mayoristapp/venta/` | OrderShell (crear) |
| `GET /ecom/mayoristapp/venta/?cod_mov=N` | OrderShell modo PED N |
| `GET /ecom/mayoristapp/compra/` | Redirect → `venta/` (preservar query) |
| `GET /ecom/mayoristapp/pedidos/<N>/` | Redirect → `venta/?cod_mov=N` |

URL names:
- Canónico: `ecom:mayoristapp_venta`
- Alias redirect: `ecom:mayoristapp_compra` (compat)
- API: `ecom:mayoristapp_venta_contexto`; alias `mayoristapp_compra_contexto`

## 2. Modos del shell

```
modo = 'nuevo' | 'editar_pendiente' | 'consulta'
editable = (modo != 'consulta')
```

Resolución al cargar `cod_mov`:
1. GET cabecera PED (`v1_comprobantes_pedidos_cabecera`).
2. Si `Anulado=Si` o `Estado != 'Pendiente'` → `consulta`.
3. Si `Estado == 'Pendiente'` y no anulado → `editar_pendiente`.
4. Sin `cod_mov` → `nuevo` (borrador `EcomCart` como hoy).

En `consulta`: catálogo off, qty off, checkout off; sí Repetir/PDF/mail; Anular solo si API `puede_anular`.

En `editar_pendiente`: líneas cargadas desde detalle (como plantilla editable en carrito/session UI); banner + CTA «Confirmar cambios».

## 3. Confirmar cambios (Pendiente)

Secuencia atómica en frontend (con modal Synap):
1. Anular PED origen (`anular` API + motivo).
2. Checkout confirmar carrito resultante.
3. Navegar a `venta/?cod_mov=<nuevo>` en consulta/éxito.

Si falla anulación: no checkout. Si falla checkout tras anular: mostrar error (pedido origen ya anulado; carrito intacto) — documentar riesgo aceptado; no rollback automático de anulación en v1.

## 4. Acciones portadas del detalle

Reutilizar URLs bootstrap de detalle en la vista venta cuando hay `cod_mov`: cabecera, detalle líneas, anular, mail, pdf, preview/cargar desde pedido.

Stepper: include extraído o HTML portado desde `pedido_detalle.html`.

## 5. Textos

- Título: «Pedido de venta» / «Gestión de pedidos de venta»
- Breadcrumb: Pedidos / Nuevo | PED {nro}

## 6. Tests

- Redirect compra→venta, pedidos/N→venta?cod_mov=N
- Hub URL contiene `/venta/`
- Vista venta 200 con sesión
- `frm=0` relay → path `/venta/`
