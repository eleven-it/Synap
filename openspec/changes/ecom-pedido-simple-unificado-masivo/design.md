# Design: Unificación pedido simple en masivo (1 sucursal)

## Technical Approach

«Pedido simple» pasa a ser la matriz masiva (`PedidoMasivoSucursalesView`) en modo 1 columna vía `?modo=simple`. El borrador único es `EcomPedidoMasivoDraft` (Postgres), extendido con `cod_mov_origen`, `modo` e `id_domicilio_fijo`. Un servicio nuevo `cargar_pedido_en_draft_masivo` (fork de `pedido_plantilla_service`) copia renglones PED → celdas de 1 domicilio. Confirmación reutiliza `batch_checkout_masivo`/`mayorista_checkout_service.confirmar`; al editar un PED Pendiente se anula el origen y se crea uno nuevo (semántica REQ-VTA-04). `/venta/` y `/compra/` redirigen a masivo preservando query. Se reutilizan patrones existentes de `pedido_masivo_sucursales.html` + `pedido_masivo_app.mjs` (canon UI reportes/MPR).

## Architecture Decisions

| Decisión | Elegido | Alternativa rechazada | Rationale |
|----------|---------|-----------------------|-----------|
| Carga PED | Copiar líneas → nuevo draft + `cod_mov_origen` (Approach 1+3) | UPDATE in-place MySQL (Approach 2) | Respeta checkout transaccional y REQ-VTA-04; evita concurrencia VB6 |
| Modo simple | Param `?modo=simple` + `modo` en draft | Vista/URL separada | Reutiliza toda la matriz; una sola base de código |
| Domicilio | `id_domicilio_fijo` fija la única columna | Filtrar en UI sin persistir | Consistencia al recargar/continuar; deriva del PED origen |
| Deprecar venta | Redirect 302 `/venta/`,`/compra/` → masivo (query preservado) | Links directos sin redirect | Bookmarks/PWA siguen operando |
| Confirmar edición | Anular origen + crear (batch 1 sucursal) | Reusar número PED | Paridad con OrderShell; rollback por compensación existente |
| Permisos | `pedidos.crear` **O** `pedido_masivo.usar` en captura; multi-columna solo `pedido_masivo.usar` | Exigir `pedido_masivo.usar` a todos | No bloquea usuarios de pedido simple actuales |

## Data Flow

    Hub / PWA ──?modo=simple[&cod_mov|&draft]──▶ PedidoMasivoSucursalesView
        │                                              │
        │ (cod_mov)                                    ▼
        ▼                                    obtener_o_crear_draft(modo=simple)
    cargar_pedido_en_draft_masivo ──▶ celdas (id_domicilio_fijo) ──▶ serializar_matriz(1 col)
        │                                              │
        ▼ (confirmar)                                  ▼
    anular_pedido_relay(cod_mov_origen) ──▶ confirmar_lote_masivo ──▶ PED nuevo + mail/crédito

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `ecom/models.py` | Modify | `EcomPedidoMasivoDraft`: `cod_mov_origen` (Int null), `modo` (Char default `masivo`), `id_domicilio_fijo` (Int null) |
| `ecom/migrations/00XX_*.py` | Create | Migración Postgres nullable, sin default destructivo |
| `ecom/services/pedido_masivo_matriz.py` | Modify | `obtener_o_crear_draft(modo, id_domicilio_fijo, cod_mov_origen)`; `serializar_matriz` filtra 1 columna en simple |
| `ecom/services/pedido_plantilla_service.py` | Modify | Add `cargar_pedido_en_draft_masivo` (PED→celdas, packs vía `_pack_tipo_y_mult` inverso) |
| `ecom/services/batch_checkout_masivo.py` | Modify | Anular `cod_mov_origen` antes del lote cuando presente |
| `ecom/pedido_masivo_views.py` | Modify | Leer `modo`/`cod_mov`/`id_domicilio`; abrir desde PED; endpoints mail/repetir/pdf |
| `ecom/pedido_masivo_app.mjs` (static) | Modify | Modo simple 1 col; hero acciones mail/crédito/repetir/PDF; read-only consulta |
| `ecom/templates/ecom/pedido_masivo_sucursales.html` | Modify | Etiquetas «Pedido simple»; barra hero acciones |
| `ecom/services/pedidos_hub_pipeline.py` | Modify | PED→masivo `?modo=simple&cod_mov=`; eliminar/migrar `_borradores_carrito`; borrador único |
| `ecom/templates/ecom/pedidos_hub.html` | Modify | `nuevo_simple`→masivo; modal Continuar/Archivar también en simple |
| `ecom/urls.py` | Modify | `/venta/`,`/compra/` → RedirectView a masivo `?modo=simple` (query_string) |
| `ecom/mayoristapp_web_views.py` | Modify | Deprecar `CompraMayoristaView` activa (redirect) |
| `ecom/permissions.py` | Modify | `EcomPedidoCapturaPermission` (OR `pedidos.crear`/`pedido_masivo.usar`) |
| `ecom/menu_config.py`, `core/pwa_nivel_a.py`, `core/middleware/mobile_level_a_middleware.py` | Modify | Deep links `ecom_compra`→masivo simple; mantener `/venta/` en allowlist (redirect) |
| `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`, `docs/general/MOBILE_SOLO_NIVEL_A.md` | Modify | Documentar modo simple y permisos |

## Interfaces / Contracts

```python
def cargar_pedido_en_draft_masivo(base_empresa, cod_mov, sess_user, *, id_usuario) -> tuple[EcomPedidoMasivoDraft | None, str | None]:
    """Valida PED (validar_pedido_como_plantilla), resuelve id_cliente_domicilio,
    crea draft modo=simple con cod_mov_origen + id_domicilio_fijo, mapea stockp→celdas (packs)."""
```

`serializar_matriz` añade `modo`, `cod_mov_origen`, `id_domicilio_fijo`; en simple `sucursales` = 1 (la fija). Confirm devuelve `codigos_movimiento` y anulación de origen en `payload`.

## Sequence Diagrams

Nuevo simple:

    Hub"Nuevo simple" ▶ /pedido-masivo-sucursales/?modo=simple
      ▶ elegir cliente ▶ abrir(modo=simple,id_domicilio) ▶ draft nuevo ▶ matriz 1 col ▶ confirmar ▶ PED

Continuar draft:

    Hub tarjeta borrador ▶ ?modo=simple&draft=ID ▶ obtener_o_crear_draft(draft_id) ▶ matriz ▶ confirmar

Abrir PED (cod_mov):

    Hub/PWA ▶ ?modo=simple&cod_mov=C ▶ cargar_pedido_en_draft_masivo(C)
      ├ Pendiente → editable; confirmar = anular(C)+crear
      └ Anulado/no-pendiente → read-only + hero(PDF/mail/repetir)

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | `cargar_pedido_en_draft_masivo`, conversión packs, `serializar_matriz` 1 col | `docker exec Synap_app python manage.py test ecom` |
| Integration | Confirm anula+crea; permisos OR; hub URLs/borrador único | tests `test_pedido_masivo_*`, `test_pedidos_hub_pipeline` |
| E2E/PWA | Deep link `ecom_compra`→simple; redirect `/venta/` | `test_pwa_nivel_a_menu`, `test_mobile_level_a_middleware` |

## Migration / Rollout

Campos draft nullable (código previo los ignora). Borradores `EcomCart` legacy: tarjeta «legacy» con CTA migrar o script one-shot (no borrado automático). Rollback: revertir redirect y restaurar hub a OrderShell; multi-sucursal intacto.

## Open Questions

- [ ] Permisos: ¿alcanza OR `pedidos.crear`/`pedido_masivo.usar`, o producto quiere unificar en un único permiso? (afecta spec REQ)
- [ ] Migración `EcomCart`: ¿script automático o CTA manual por vendedor?
- [ ] Conversión UOM histórica distinta a Bulto/Display: mensaje de redondeo vs rechazo de renglón.
