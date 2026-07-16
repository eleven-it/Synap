# Exploration: Unificación pedido simple → draft masivo (1 sucursal)

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Fecha:** 16/07/2026  
**Modo persistencia:** hybrid (Engram + openspec)

## Decisiones producto (LOCKED)

- «Pedido simple» conserva nombre en UI; implementación = **matriz masiva con una sola columna** (sucursal del PED o domicilio operativo).
- Deprecar foco de `/ecom/mayoristapp/venta/` (OrderShell + `EcomCart` como borrador de trabajo).
- Hub: **Nuevo simple**, **Continuar borrador**, **Abrir PED** → pantalla masivo (modo 1 sucursal).
- Editar/consultar PED (`?cod_mov=`) MUST sobre pedido simple (masivo 1 sucursal).
- Solo **PED**; deprecar PRE/DEV en este flujo.
- Deprecar catálogo/filtro por stock en captura.
- Pack fijo **Bulto > Display** (ya en `batch_checkout_masivo._pack_tipo_y_mult`).
- Masivo MUST ganar: **enviar mail**, **crédito**, **repetir pedido**.
- Borrador único: **`EcomPedidoMasivoDraft`** Postgres (no `EcomCart` como workspace).
- Precios: mismo motor `price_rules_engine` / `mayorista_checkout_service.confirmar` (validado).

---

## Current State

### Entry points Hub → venta vs masivo

| Origen | Destino actual | Params / notas |
|--------|----------------|----------------|
| Hub «Nuevo → Pedido simple» | `/ecom/mayoristapp/venta/` | Link directo (`urls.nuevo_simple`); **sin** modal borrador |
| Hub «Nuevo → Masivo sucursales» | `/ecom/mayoristapp/pedido-masivo-sucursales/` | Modal si hay borrador masivo activo |
| Hub tarjeta borrador `tipo=carrito` | `/ecom/mayoristapp/venta/` | `EcomCart` borrador; meta `cart_id` no viaja en URL |
| Hub tarjeta borrador `tipo=masivo` | `/ecom/mayoristapp/pedido-masivo-sucursales/?draft={id}` | Continuar matriz |
| Hub tarjeta PED MySQL | `/ecom/mayoristapp/venta/?cod_mov={cod}` | Editar/consultar vía OrderShell |
| Menú PWA `ecom_compra` | `/ecom/mayoristapp/venta/` | `core/pwa_nivel_a.py`, `ecom/menu_config.py` |
| Menú `ecom_pedido_masivo` | `/ecom/mayoristapp/pedido-masivo-sucursales/` | Permiso `ecom.pedido_masivo.usar` |

**Pipeline hub** (`ecom/services/pedidos_hub_pipeline.py`):

- `_borradores_carrito`: lista `EcomCart` estado borrador con ítems → columna Borrador.
- `_borradores_masivo`: `EcomPedidoMasivoDraft` borrador/confirmando → columna Borrador.
- `_pedidos_mysql`: solo `TipoComprobante='PED'` → URL venta con `cod_mov`.
- Modal borrador en hub JS solo considera draft **masivo** (`draftMasivoId`); carritos simples no participan del flujo Continuar/Archivar.

### OrderShell / venta (`/venta/`)

- Template `compra_mayorista.html` + mixins `compra_mayorista_pedido.mjs`, `compra_mayorista_checkout.mjs`, `compra_mayorista_app.mjs`.
- Borrador: **`EcomCart`** + `EcomCartItem` (Postgres); autoguardado vía APIs carrito.
- Modos PED: `nuevo` | `editar_pendiente` | `consulta` según `?cod_mov=` y estado MySQL.
- Editar pendiente: `_hidratarCarritoDesdePedido` → `POST …/carrito/desde-pedido/` (`pedido_plantilla_service.cargar_desde_pedido`).
- Confirmar edición: anula origen + checkout nuevo PED (REQ-VTA-04).
- Features presentes en venta y **ausentes en masivo UI**:
  - Widget crédito (`creditoWidget` en checkout/header).
  - Enviar mail post-carga / manual (`solicitarEnviarMail`, `mail_enqueue`).
  - Repetir pedido (`SynapRepetirPedido`, `repetir_pedido_modal.js`).
  - Catálogo con validación stock configurable (`ecom_validar_stock_pedidos`).

### Draft masivo actual

**Modelo** (`ecom/models.py`, migración `0029`, `0030`, `0031`):

- `EcomPedidoMasivoDraft`: `base_empresa`, `id_usuario`, `cod_viajante`, `id_cliente`, `estado`, `ultimo_error`, `codigos_movimiento[]`, `descuento_pie_pct`, `descuentos_fila{}`.
- `EcomPedidoMasivoDraftCelda`: `(draft, id_articulo, id_cliente_domicilio) → cantidad_packs`.
- **No existe** `cod_mov_origen`, `modo`, ni `id_domicilio_fijo` en el modelo.

**Servicios** (`pedido_masivo_matriz.py`, `batch_checkout_masivo.py`):

- `obtener_o_crear_draft`: reutiliza borrador activo usuario+cliente o crea nuevo.
- Confirmación: 1 PED MySQL por sucursal con celdas > 0; carritos efímeros + `confirmar()` checkout.
- Mail: heredado de `CheckoutInput.enviar_mail_cliente=True` en confirmación (encola si cliente tiene email).
- Crédito: `evaluar_autorizacion` en `mayorista_checkout_service.confirmar` (autorizacion_sistema en cabecera).
- Preview: `validar_stock=False`; confirmación real: `validar_stock=True` en `_cargar_lineas_sucursal`.
- Cabecera comercial: integrada vía change `ecom-pedido-cabecera-comercial` (apply-complete).

**UI** (`pedido_masivo_sucursales.html`, `pedido_masivo_app.mjs`):

- Matriz N sucursales; acordeón móvil.
- Buscador artículos por ternas (`buscar_articulos_filtrados_ternas`); sin filtro stock en catálogo.
- Sin hero acciones Anular/Repetir/PDF/mail para PED existente.

### Repetir pedido

- `pedido_plantilla_service`: copia líneas PED → **`EcomCart`** (no draft masivo).
- APIs: `GET/POST …/carrito/desde-pedido/` en `pedido_gestion_views.py`.

---

## Qué falta para modo 1 sucursal + paridad funcional

| Capacidad | Estado actual | Gap |
|-----------|---------------|-----|
| UI 1 columna | Matriz multi-sucursal siempre | Param `modo=simple` o `id_domicilio` + ocultar columnas extra |
| Borrador simple unificado | Dos tipos en hub (carrito + masivo) | Migrar/deprecar `EcomCart` borrador; hub solo masivo |
| Abrir PED pendiente | Venta + carrito | API cargar PED → celdas draft (1 domicilio del PED) |
| Consulta PED no editable | Venta modo consulta | Masivo read-only + hero acciones (PDF, mail, repetir) |
| Repetir pedido | → EcomCart | Adaptar plantilla → celdas draft o flujo «nuevo desde PED» |
| Crédito en captura | Solo venta/checkout mixin | Exponer widget crédito en contexto masivo (API cliente existente) |
| Enviar mail manual | Solo venta con `cod_mov` | Reutilizar `mail_enqueue` en hero masivo consulta |
| Hub URLs | PED → venta | PED → masivo `?cod_mov=`; simple → masivo sin draft carrito |
| Permisos | Masivo: `ecom.pedido_masivo.usar` | Alinear simple (¿mismo permiso o unificar con pedidos?) |
| PRE/DEV | Venta soporta tipos | Eliminar toggles/rutas en flujo unificado |
| Stock en catálogo venta | Configurable | Deprecar; confirm puede seguir validando stock según config |

---

## Approaches: cargar PED pendiente en draft

### 1. Copiar líneas a nuevo draft (recomendado)

Al abrir `?cod_mov=` en modo edición:

1. Validar PED pendiente no anulado (reutilizar `validar_pedido_como_plantilla`).
2. Resolver `id_cliente_domicilio` desde `cliente_datos_adicionales` del PED.
3. Crear/recuperar `EcomPedidoMasivoDraft` con **`cod_mov_origen`** (campo nuevo) y domicilio fijo.
4. Mapear renglones `stockp` → celdas (packs vía `_pack_tipo_y_mult` inverso o cantidad legacy).
5. Al confirmar: anular origen + confirmar lote 1 sucursal (misma semántica REQ-VTA-04).

| Pros | Cons | Effort |
|------|------|--------|
| Alineado con spec actual (no UPDATE in-place) | Migración Postgres + servicio nuevo | Medium |
| Reutiliza matriz/autoguardado existente | Conversión UOM/packs puede fallar en artículos edge | |
| Rollback claro ante error confirmación | Dos fuentes de verdad hasta confirmar | |
| Paridad con `pedido_plantilla_service` | | |

### 2. Edición vinculada (draft apunta a cod_mov, mutación directa MySQL)

Draft almacena `cod_mov` y UI edita «el mismo» PED con UPDATE legacy.

| Pros | Cons | Effort |
|------|------|--------|
| Un solo número hasta confirmar | **Contradice REQ-VTA-04** y checkout transaccional | High |
| | Riesgo concurrencia VB6/Synap | |
| | Duplica lógica fuera de `confirmar()` | |

### 3. Híbrido ligero (metadata linked, datos copiados)

Igual que (1) pero draft mantiene `cod_mov_origen` solo para anulación al confirmar; no re-sync automático desde MySQL.

| Pros | Cons | Effort |
|------|------|--------|
| Trazabilidad edición | Usuario puede desincronizar si MySQL cambia externamente | Medium-Low |
| Confirmación explícita anula+crea | Campo extra en modelo | |

**Recomendación:** **Approach 1 + metadata `cod_mov_origen` (variante 3)** — copia al abrir, confirmación anula+crea, consulta solo lectura sin draft mutable.

---

## Approaches: routing y deprecación venta

| Approach | Descripción | Pros | Cons | Effort |
|----------|-------------|------|------|--------|
| **A — Redirect venta → masivo** | `/venta/` 302 a masivo `?modo=simple` (+ preservar query) | Bookmarks/PWA compatibles | Dos URLs transitorias | Low |
| **B — Hub/menu apuntan directo** | Deprecar venta sin redirect inmediato | Menor sorpresa en URLs legacy | Links rotos gradualmente | Medium |
| **C — Venta shell mínima** | Template venta embebe iframe/redirect JS a masivo | — | Deuda técnica | Low (no recomendado) |

**Recomendación:** **A + B**: redirect canónico desde `/venta/` y `/compra/`; actualizar hub, menú, PWA deep links, pipeline tarjetas.

---

## Impacto Nivel A / PWA

**Hoy** (`docs/general/MOBILE_SOLO_NIVEL_A.md`, `mobile_level_a_middleware.py`):

- Permitidas: `/venta/`, `/compra/`, `/pedidos/`, `/pedido-masivo-sucursales/`.
- Menú móvil: `ecom_compra` (venta), `ecom_pedidos`, `ecom_pedido_masivo`.

**Tras unificación:**

- Pedido simple = misma ruta masivo (acordeón móvil ya soportado en change `ecom-pedido-masivo-ux-contexto`).
- **Acción:** redirigir `ecom_compra` deep link a masivo modo simple; mantener `/venta/` en allowlist como redirect temporal.
- Usuario con solo `ecom.pedidos` pero sin `ecom.pedido_masivo.usar` → **riesgo de permisos** a resolver en propose.
- Tests afectados: `core/tests/test_pwa_nivel_a_menu.py`, `core/tests/test_mobile_level_a_middleware.py`.

---

## Specs afectadas

| Spec / change | Impacto |
|---------------|---------|
| `ecom-pedido-masivo-sucursales` | ADD modo 1 sucursal; MOD etiquetas UI «Pedido simple»; MOD/deprecate REQ-MAS-02 catálogo ternas en simple (o relajar); ADD repetir/mail/crédito/consulta cod_mov |
| `ecom-pedido-venta-shell` | DEPRECATE como shell activa; mantener reqs de comportamiento migrados a masivo simple |
| `ecom-pedidos-hub-kanban` | MOD REQ-HUB-02/03: un solo tipo borrador; URLs masivo; modal también para «nuevo simple» |
| `ecom-checkout-mayorista` | CLARIFY: `EcomCart` solo efímero en batch (ya así); borrador de trabajo = draft masivo |
| `ecom-carrito-mayorista` | DEPRECATE borrador persistente simple |
| `ecom-pedido-cabecera-comercial` | Sin cambio funcional (apply-complete); consumir desde simple 1 sucursal |
| Change `ecom-pedido-cabecera-comercial` | Dependencia satisfecha; no bloquea |

---

## Affected Areas (implementación)

- `ecom/services/pedidos_hub_pipeline.py` — tarjetas borrador/ PED URLs; eliminar `_borradores_carrito` o migrar.
- `ecom/templates/ecom/pedidos_hub.html` — `nuevo_simple`, modal borrador unificado.
- `ecom/pedido_masivo_views.py` + `pedido_masivo_app.mjs` — modo simple, cod_mov, hero acciones.
- `ecom/services/pedido_masivo_matriz.py` — abrir con domicilio fijo; serializar 1 columna.
- `ecom/services/pedido_plantilla_service.py` — variante `cargar_desde_pedido_a_draft`.
- `ecom/models.py` + migración — `cod_mov_origen`, opcional `modo` / `id_domicilio_fijo`.
- `ecom/mayoristapp_web_views.py`, `pedido_gestion_views.py` — redirect venta.
- `ecom/menu_config.py`, `core/pwa_nivel_a.py`, `core/middleware/mobile_level_a_middleware.py`.
- `ecom/static/ecom/js/compra_mayorista_*.mjs` — deprecar o reducir a redirect.
- `docs/ecom/PEDIDO_MASIVO_SUCURSALES.md`, `docs/general/MOBILE_SOLO_NIVEL_A.md`.
- Tests: `test_pedidos_hub_pipeline`, `test_pedido_masivo_*`, `test_pwa_nivel_a_menu`, nuevos para carga PED→draft.

---

## Recommendation

Implementar **pedido simple como variante de pedido masivo** con:

1. **Query canon:** `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple` (+ `draft=`, `cod_mov=`, `id_domicilio=` según caso).
2. **Modelo draft:** agregar `cod_mov_origen` (nullable) y `id_domicilio_fijo` (nullable; en simple obligatorio tras elegir cliente/PED).
3. **Carga PED:** servicio `cargar_pedido_en_draft_masivo` (fork de plantilla → celdas, 1 domicilio).
4. **Confirmación edición:** flujo anula+crea antes del batch de 1 sucursal (reutilizar lógica venta).
5. **Paridad UX:** portar hero/mixins mail, repetir, crédito, PDF desde OrderShell a barra contexto masivo.
6. **Hub:** unificar borradores; PED links → masivo; redirect `/venta/`.
7. **Migración suave:** borradores `EcomCart` existentes → script one-shot o tarjeta «legacy» con CTA migrar.

Orden sugerido en propose: backend draft/carga PED → hub URLs → UI simple 1 col → acciones mail/crédito/repetir → redirect venta → limpieza EcomCart borrador.

---

## Risks

- **Permisos:** usuarios con pedido simple hoy sin `ecom.pedido_masivo.usar` quedarían bloqueados si no se unifican permisos.
- **Borradores EcomCart en producción:** pérdida de trabajo si se depreca sin migración.
- **Conversión packs:** renglones históricos con UOM distinta a Bulto/Display pueden redondear distinto al reabrir PED.
- **Edición concurrente:** vendedor edita draft mientras otro anula PED origen en AdministraNET → validar al confirmar.
- **Stock:** deprecar filtro catálogo no elimina validación en commit; alinear expectativa producto vs `ecom_validar_stock_pedidos`.
- **PWA bookmarks:** usuarios con `/venta/` guardado dependen del redirect permanente.
- **Scope spec venta-shell:** delta grande en capacidades archivadas; requiere propuesta explícita de deprecación.

---

## Ready for Proposal

**Sí.** Exploración suficiente para `sdd-propose` con scope, migración borradores, matriz permisos y deltas de spec listados arriba.
