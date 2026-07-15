# Design: Cabecera comercial de pedidos e-commerce

**Change:** `ecom-pedido-cabecera-comercial` · **Fecha:** 14/07/2026

## Technical Approach

Servicio único `pedido_cabecera_comercial.py` que resuelve la cabecera (fechas, condición, lista) a partir del cliente legacy y de overrides validados por rol. Checkout simple (`mayorista_checkout_service.confirmar`) y lote masivo (`batch_checkout_masivo.confirmar_lote_masivo`) consumen el mismo resolver y persisten en `comp_ped`/`cliente_datos_adicionales`. La autoridad de precios sigue en el commit (`_reprice_items` con `cart.lista_id`); el resolver solo fija `lista_id` efectiva antes de repricear. UI en canon MPR/slate; vendedor ve lista/condición en solo lectura.

## Architecture Decisions

| Decisión | Elegido | Alternativas | Rationale |
|----------|---------|--------------|-----------|
| Ubicación lógica | Nuevo servicio `pedido_cabecera_comercial.py` | Inline en checkout / masivo | Evita divergencia simple vs masivo; testeable aislado |
| Vencimiento | `fecha_pedido + cond_venta.Dias`; override solo supervisor y `≥ fecha_pedido` | +30 fijo (actual); siempre editable | Paridad AdministraNET; integridad comercial |
| Permiso lista/condición | `es_supervisor` (`supervisor_venta`/`permiso_supervisor_venta_web`) reusando `_si_no_supervisor` | Nuevo flag de permiso | Reusa `vendedor_operativo`; sin nueva config |
| Enforcement rol | Server-side: si no supervisor, se ignoran overrides y se fuerzan defaults del cliente | Solo `disabled` en UI | Seguridad: no confiar en front |
| Catálogos UI | Reusar `lista_precio_relay_json`; nuevo `condiciones_venta_relay_json` (`cond_venta`) | Query inline en vista | Consistencia relay JSON |
| Recalcular precios | Fijar `cart.lista_id` desde cabecera → `_reprice_items` en commit + preview | Confiar en precio del carrito | Motor único es autoridad |
| Fechas | Backend ISO/`date`; UI muestra dd/MM/yyyy | ISO en UI | Regla Synap español |

## Data Flow

```
UI cabecera (dd/MM/yyyy) ──ISO──▶ View (body)
        │                            │ es_supervisor
        ▼                            ▼
resolver_cabecera_comercial(cliente + overrides) ──▶ PedidoCabeceraComercial
        │ (lista_id, id_condventa, fechas, vencimiento)
        ▼
CheckoutInput ──▶ confirmar() / confirmar_lote_masivo()
        │ set cart.lista_id → _reprice_items (autoridad)
        ▼
comp_ped (Fecha, Vencimiento, FechaEntrega, CondVenta, id_condventa)
cliente_datos_adicionales (fechaEntrega) · stockp.lista_precio
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `ecom/services/pedido_cabecera_comercial.py` | Create | `PedidoCabeceraComercial`, `resolver_cabecera_comercial`, `dias_condicion`, `puede_editar_cabecera_comercial` |
| `ecom/services/precio_relays.py` | Modify | `condiciones_venta_relay_json(base_empresa)` desde `cond_venta` |
| `ecom/services/mayorista_checkout_service.py` | Modify | `CheckoutInput` +campos cabecera; `confirmar()` usa cabecera (quita `hoy`/`+30`), fija `cart.lista_id` |
| `ecom/services/batch_checkout_masivo.py` | Modify | `confirmar_lote_masivo`/`calcular_totales_lote_masivo` reciben cabecera y la propagan a cada PED |
| `ecom/checkout_relay_views.py` | Modify | Lee cabecera del body, resuelve por rol, arma `CheckoutInput` |
| `ecom/pedido_masivo_views.py` | Modify | Contexto (defaults + catálogos + `puede_editar`) y confirmación con cabecera |
| `ecom/static/ecom/js/compra_mayorista_checkout.mjs` | Modify | Panel cabecera, recalcular al cambiar lista (supervisor) |
| `ecom/static/ecom/js/pedido_masivo_app.mjs` | Modify | Cabecera en barra contexto → preview/confirmar |
| `ecom/templates/ecom/*` + `pedido_masivo_sucursales.html` | Modify | Panel/inputs cabecera (canon MPR) |
| `docs/ecom/` | Modify | Comportamiento cabecera comercial |

## Interfaces / Contracts

```python
@dataclass
class PedidoCabeceraComercial:
    fecha_pedido: date
    fecha_entrega: Optional[date]
    vencimiento: date
    id_condventa: Optional[int]
    cond_venta: str
    lista_id: int
    editable_por_rol: bool  # True si supervisor aplicó overrides

def resolver_cabecera_comercial(
    base_empresa: str, id_cliente: int, *,
    es_supervisor: bool,
    fecha_pedido: Optional[date] = None,
    fecha_entrega: Optional[date] = None,
    vencimiento: Optional[date] = None,   # override (solo supervisor)
    id_condventa: Optional[int] = None,   # override (solo supervisor)
    lista_id: Optional[int] = None,       # override (solo supervisor)
    dias_entrega: int = 0, dias_no_laborables: list[int] | None = None,
) -> tuple[Optional[PedidoCabeceraComercial], Optional[str]]: ...
```

`CheckoutInput` gana: `fecha_pedido`, `fecha_entrega`, `vencimiento`, `id_condventa`, `cond_venta`, `lista_id` (todos opcionales; si presentes tienen prioridad sobre el cálculo legacy). Reglas: no supervisor ⇒ resolver ignora overrides de lista/condición/vencimiento y usa `cliente.id_cv`/`cliente.ListaPrecio`; vencimiento default = `fecha_pedido + cond_venta.Dias`; validaciones `vencimiento ≥ fecha_pedido` y `fecha_entrega ≥ fecha_pedido`.

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Vencimiento = Fecha + Dias; override/validación; enforcement rol | `docker exec Synap_app python manage.py test ecom` con `cond_venta` mockeada |
| Integration | `confirmar` persiste Fecha/Vencimiento/CondVenta/lista_precio | Test checkout con cursor legacy fake |
| Integration | Masivo propaga misma cabecera a N PED | Test `confirmar_lote_masivo` |
| E2E/manual | Supervisor edita lista→recalcula; vendedor read-only | UI checkout + masivo |

## Migration / Rollout

No requiere migración MySQL ni Postgres (campos ya existen en `comp_ped`). Borradores previos sin campos de cabecera resuelven defaults del cliente. Rollback = revertir commit.

## Open Questions

- [x] Nombre/columnas exactas de `cond_venta` (`Codigo`, `Descripcion`, `Dias`) — confirmado en `reports/docs/tablas/cond_venta.md`.
- [x] Trigger de recálculo de precios en checkout simple al cambiar lista: `PATCH /ecom/api/mayoristapp/carrito/lista-precio/` + `_reprice_items` en commit.
- [x] Condición default siempre desde `cliente.id_cv` — asumido e implementado.
