# Tasks: Unificación pedido simple en masivo (1 sucursal)

**Change:** `ecom-pedido-simple-unificado-masivo`  
**OQs resueltas:** permisos OR (`pedidos.crear` ∨ `pedido_masivo.usar`); migración `EcomCart` = tarjeta legacy + CTA manual (script one-shot opcional); UOM no estándar = redondeo + aviso al usuario.

## Phase 1: Esquema y permisos

- [x] 1.1 En `ecom/models.py`, añadir a `EcomPedidoMasivoDraft`: `cod_mov_origen` (Int null), `modo` (Char default `masivo`), `id_domicilio_fijo` (Int null).
- [x] 1.2 Crear migración Postgres `ecom/migrations/00XX_*.py` (campos nullable, sin default destructivo).
- [x] 1.3 En `ecom/permissions.py`, implementar `EcomPedidoCapturaPermission`: acceso si `pedidos.crear` **O** `pedido_masivo.usar`; multi-columna solo con `pedido_masivo.usar`.

## Phase 2: Servicios draft y carga PED

- [x] 2.1 En `ecom/services/pedido_masivo_matriz.py`, extender `obtener_o_crear_draft` con `modo`, `id_domicilio_fijo`, `cod_mov_origen`.
- [x] 2.2 En `pedido_masivo_matriz.py`, ajustar `serializar_matriz`: en `modo=simple` devolver 1 sucursal (`id_domicilio_fijo`) y metadata `modo`/`cod_mov_origen`.
- [x] 2.3 En `ecom/services/pedido_plantilla_service.py`, implementar `cargar_pedido_en_draft_masivo` (validar PED, packs Bulto>Display, fijar domicilio).
- [x] 2.4 En carga PED, detectar UOM no estándar: aplicar redondeo documentado y exponer aviso en respuesta/UI (REQ-PSU-04).
- [x] 2.5 En `ecom/services/batch_checkout_masivo.py`, anular `cod_mov_origen` antes del lote si presente; validar origen Pendiente no anulado (REQ-CHK-014).

## Phase 3: UI modo simple (matriz 1 columna)

- [x] 3.1 En `ecom/pedido_masivo_views.py`, leer `modo`/`cod_mov`/`id_domicilio`; invocar carga PED; aplicar `EcomPedidoCapturaPermission`.
- [x] 3.2 En `ecom/static/.../pedido_masivo_app.mjs`, modo simple: 1 columna, etiqueta «Pedido simple», read-only si PED no Pendiente (REQ-PSU-05).
- [x] 3.3 En `ecom/templates/ecom/pedido_masivo_sucursales.html`, títulos/CTAs «Pedido simple» y contenedor hero acciones.
- [x] 3.4 Confirmación simple: modal Synap riesgos + flujo anula+crea vía checkout mayorista (REQ-PSU-06).

## Phase 4: Hub y borrador único

- [x] 4.1 En `ecom/services/pedidos_hub_pipeline.py`, URLs PED→`?modo=simple&cod_mov=`; eliminar `_borradores_carrito` del listado estándar.
- [x] 4.2 En `ecom/templates/ecom/pedidos_hub.html`, `nuevo_simple`→masivo; modal Continuar/Archivar también en Nuevo simple (REQ-HUB-03).
- [x] 4.3 Tarjeta legacy `EcomCart`: CTA «Migrar a borrador masivo» (conversión a celdas) o archivar; no mezclar con borrador masivo (REQ-CAR-009).

## Phase 5: Acciones hero (mail, crédito, repetir, PDF)

- [x] 5.1 En `pedido_masivo_app.mjs` + template, barra hero: crédito, Enviar mail, Repetir, Ver PDF, Anular si `puede_anular` (REQ-PSU-07).
- [x] 5.2 En `pedido_masivo_views.py`, endpoints/wiring mail, repetir, PDF reutilizando APIs mayoristas existentes.
- [x] 5.3 Repetir pedido: crear draft `modo=simple` con celdas copiadas; MUST NOT usar `EcomCart` borrador (REQ-CAR-008).

## Phase 6: Redirect y deep links

- [x] 6.1 En `ecom/urls.py`, `/venta/` y `/compra/` → `RedirectView` a masivo `?modo=simple` preservando `query_string` (REQ-PSU-10).
- [x] 6.2 En `ecom/mayoristapp_web_views.py`, deprecar `CompraMayoristaView` activa (redirect canónico).
- [x] 6.3 En `ecom/menu_config.py`, `core/pwa_nivel_a.py`, `core/middleware/mobile_level_a_middleware.py`: deep links `ecom_compra`→masivo simple; mantener `/venta/` en allowlist.

## Phase 7: Tests

- [x] 7.1 Unit: `cargar_pedido_en_draft_masivo`, conversión packs, `serializar_matriz` 1 col (`docker exec Synap_app python manage.py test ecom`).
- [x] 7.2 Integración: confirm anula+crea; permisos OR; hub borrador único y URLs (`test_pedido_masivo_*`, `test_pedidos_hub_pipeline`).
- [x] 7.3 PWA/redirect: deep link `ecom_compra`; redirect `/venta/?cod_mov=` (`test_pwa_nivel_a_menu`, `test_mobile_level_a_middleware`).

## Phase 8: Documentación y migración opcional

- [x] 8.1 Actualizar `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md` y `docs/general/MOBILE_SOLO_NIVEL_A.md` (modo simple, permisos OR, legacy cart).
- [ ] 8.2 (Opcional) Comando `manage.py` one-shot para migrar borradores `EcomCart` restantes a draft masivo; documentar en docs/ecom.
