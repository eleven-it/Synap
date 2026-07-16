# Pedido masivo por sucursales

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` · UX contexto: `ecom-pedido-masivo-ux-contexto`  
**Unificación pedido simple:** `ecom-pedido-simple-unificado-masivo` (16/07/2026)  
**Cabecera comercial (barra contexto):** `docs/ecom/PEDIDO_CABECERA_COMERCIAL.md`  
**Ruta (Phase 4):** `/ecom/mayoristapp/pedido-masivo-sucursales/`  
**Ruta canónica pedido simple:** `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple` (+ `cod_mov`, `draft`, `id_domicilio`)  
**Canon UI:** Tablero de producción (slate/sky)  
**Fecha:** 16/07/2026

## Modo simple (1 sucursal) — 16/07/2026

El **pedido simple** dejó de usar `OrderShell` / `EcomCart` borrador y se unificó en la misma matriz masiva con **una columna**:

| Aspecto | Comportamiento |
|---------|----------------|
| Parámetro | `?modo=simple` en la URL (sin ruta nueva) |
| Borrador | `EcomPedidoMasivoDraft` con `modo=simple`, `id_domicilio_fijo`, `cod_mov_origen` |
| Carga PED | `cargar_pedido_en_draft_masivo` copia `stockp` → celdas (packs Bulto>Display); UOM no estándar → redondeo + aviso |
| Confirmar edición Pendiente | Anula PED origen + crea uno nuevo (`batch_checkout_masivo`, REQ-CHK-014) |
| Hero modo simple | Crédito, Enviar mail, Repetir, Ver PDF, Anular (si `puede_anular`); título «Pedido simple» |
| Solo consulta | Si el PED origen no está Pendiente, matriz read-only |
| Legacy `/venta/` y `/compra/` | Redirect 302 a masivo `?modo=simple` preservando query (`cod_mov`, etc.) |
| Hub | Tarjetas PED y «Nuevo simple» → `?modo=simple&cod_mov=` o `?modo=simple&draft=` |
| Carrito legacy | `EcomCart` borrador aparece como tarjeta **Carrito legacy** con CTA migrar/archivar (no mezcla con draft masivo) |

### Permisos (OR)

| Key | Uso |
|-----|-----|
| `ecom.pedidos.crear` **o** `ecom.pedido_masivo.usar` | Captura en modo simple y APIs de matriz (`EcomPedidoCapturaPermission`) |
| `ecom.pedido_masivo.usar` | Matriz **multi-columna** (modo masivo sin `modo=simple`) |
| `ecom.pedidos.ver` | Ver borradores y PED en hub |

## Flujo (14/07/2026 — barra contexto + auto-apertura)

1. **Tarjeta de contexto comercial** densa y colapsable (`.pm-context-card`): grid 2 columnas con **label + campo en la misma línea** (`.pm-field-row` + `.pm-label-inline`). Orden: fecha pedido | fecha entrega; vencimiento | lista; cliente | condición. Las fechas usan `input type="date"` nativo ligado al ISO del estado (`cabecera.fecha_pedido`/`fecha_entrega`/`vencimiento`) y sincronizan su espejo `*_display` (dd/MM/yyyy) vía `onCabeceraFechaIso`. Anchos semánticos: fechas `w-[9.5rem]/max-w-[10rem]`, cliente `flex-1 min-w-[12rem]`, lista/condición `w-[14rem]/max-w-[16rem]`. Chevron en el eyebrow expande/compacta (estado Alpine `contextoAbierto`, default `true`, persistido en `sessionStorage['pm-contexto-abierto']`); al compactar solo se muestra una fila resumen (cliente + fechas clave) para liberar alto a la matriz.
2. **Hero oscuro (una fila):** título + badge «Borrador #N»; acciones a la derecha: **vendedor operativo** (antes de Anular), Anular, Hub y **Confirmar pedido** (`bg-orange-500`, mismo naranja CTA Synap del navbar). Sin subtítulo de packs/autoguardado.
3. Al **elegir cliente** en el buscador predictivo, el front invoca automáticamente `POST …/abrir/` (misma semántica que antes tenía el botón). Spinner inline «Abriendo borrador…» durante la petición; guard anti doble POST.
3. **Matriz siempre visible** desde el primer render: shell de tabla (desktop) o acordeón por sucursal (móvil). Estados vacíos:
   - Sin borrador → guía «Elegí un cliente…»
   - Borrador sin sucursales → alerta amber
   - Borrador sin filas → guía «Agregá artículos…» + fila buscador al pie (solo con `draftId`)
4. Columnas = `cliente_domicilio` no anulados con ≥1 **relación** activa (vendedor operativo + cliente) cuando VCM está activo; si no, todos los domicilios activos. Encabezado = **`NroCalle`** (nº de sucursal). Click en la celda del encabezado (desktop) o en la fila del acordeón (móvil) abre un modal con calle, dpto, distrito, provincia y zona. En móvil, el chevron expande/colapsa el acordeón sin abrir el modal. Ver `docs/ecom/VENDEDOR_CLIENTE_MARCA.md`.  
5. Filas = artículos **Terminado** de marcas asignadas con **paridad carrito/precio**: `Discontinuo='No'` y `ecommerce='Si'` (mismo criterio que `obtener_articulo_row_precio` / `agregar_item`). El buscador predictivo (`buscar_articulos_filtrados_ternas`) no ofrece ítems que luego fallarían en preview/confirm con «Artículo no encontrado o inactivo». **Flecha abajo** (o botón ▾) lista **todo** el catálogo filtrado (`?todos=1`, sin mínimo de 2 caracteres; tope 5000). La búsqueda tipada sigue pidiendo ≥2 caracteres y `tam=20`. Desktop y móvil.  
   Columna **Precio** = precio real del motor (lista del cliente).  
6. Celdas = cantidad en **packs**. Columna de sumatoria: **Total packs**. Enter en la última sucursal vuelve al buscador.  
7. **Fecha de entrega** obligatoria al confirmar: si falta, modal de aviso y foco en el campo. Cliente en UI sin `(cod: N)`.  
8. Confirmar → **1 PED por sucursal** con `cliente_datos_adicionales.id_cliente_domicilio`.

### Matriz — layout viewport, scroll y columnas fijas izq./der. (14/07/2026)

**Shell de viewport fijo (solo desktop `≥lg`):** la página no hace scroll horizontal ni vertical propio; el `scroll` vive dentro de la matriz. Estructura flex vertical dentro de `h-[calc(100dvh-4.5rem)]`:

- `<section.pm-matrix-viewport … overflow-hidden>` + `div.mx-auto … min-w-0` → evita que la tabla (ancho `max-content`) desborde la página completa. En desktop su altura efectiva descuenta header (4rem), padding del shell (4rem) y status bar (2rem): `calc(100dvh - 8rem)`.
- **Contexto (arriba, `flex-shrink-0`):** migas, hero oscuro, alertas y tarjeta de contexto comercial. Siempre visibles.
- **Matriz (medio, `flex-1 min-h-0 min-w-0`):** contenedor `.pm-matrix-scroll` con `overflow-auto` → **único** scroll horizontal (sucursales) y vertical (filas). No empuja fuera contexto ni pie.
- **Pie (abajo, `flex-shrink-0`):** `.pm-preview-panel` (descuento de lote, botón «Actualizar preview», NETO/IVA/TOTAL con chip **Estimado** / **Validado**). Siempre visible salvo viewport muy bajo (entonces la matriz encoge, no el pie).

Si las sucursales superan el ancho del viewport, la matriz hace **scroll horizontal** y permanecen fijas (sticky):

| Columna | Lado | Comportamiento |
|---------|------|----------------|
| **Artículo** | Izq. (`left: 0`) | Absorbe el sobrante del viewport (`min` ~16 rem); nombre en 2 líneas |
| **Precio** | Izq. (`left: --pm-left-precio`) | Fijo ~5.5 rem; `left` medido en runtime (`syncPmStickyCols`) |
| **% Desc.** | Izq. (`left: --pm-left-desc`) | Fijo ~4.25 rem; sombra derecha como límite con sucursales |
| **Qty sucursal** | Centro (scroll-x) | Fijo ~4.5 rem (≈6 dígitos); no se estira con el viewport |
| **Total** | Der. (`right: --pm-right-total`) | Fijo ~5.5 rem; sombra a la **izquierda** del bloque; fondo sólido |
| **Eliminar** | Der. (`right: 0`) | Columna dedicada (~2.75 rem) con ícono trash; fondo sólido |

- El **botón eliminar** ya no vive dentro de la celda Artículo: ahora es una **columna sticky derecha** propia, junto a Total.
- Fondos **sólidos** (`bg-white`/`bg-slate-50` + `dark:bg-slate-900`) en las celdas sticky izq./der. para que las sucursales no se transparenten debajo al scrollear. Encabezados sticky con `z-index` mayor a las sucursales (izq. `32`, der. `22`, sucursal `20`).
- `--pm-right-total` = ancho real de la columna Eliminar, medido en runtime por `syncPmStickyCols` (refs `pmStickyTotal`/`pmStickyDelete`), igual que `--pm-left-*` para el bloque izquierdo.

Inputs de cantidad y % descuento: densidad `h-8` / `text-xs` (token `.pm-input-dense`). El contexto comercial inicia **compacto** para reservar alto a la matriz; el usuario puede expandirlo y la preferencia se conserva por sesión.

Clases: `.pm-matrix-*` en `pedidos_page_styles.html`. JS: `pedido_masivo_app.mjs` → `syncPmStickyCols` (mide anchos reales de Artículo/Precio → `--pm-left-*` y de Eliminar → `--pm-right-total`). El selector de vendedor se muestra en el hero oscuro (`selectorVendedorHero: true`, `selectorVendedorInline: false`); `toggleContexto()` recalcula los offsets sticky al cambiar el alto del contexto. Versionado del bundle: `?v=masivo7`.

> **Móvil/tablet (`<lg`):** el acordeón por sucursal no cambia; el botón eliminar sigue dentro de cada card. La columna sticky derecha aplica solo a la tabla desktop.

#### Fix robusto — shell de 3 zonas (14/07/2026, `?v=masivo8`)

El sticky en `<td>` fallaba porque `main.app-content` (flex item con `min-width:auto`) dejaba que la matriz empujara el ancho más allá del viewport y el scroll-x lo tomaba el body. Se reemplazó por un **shell de 3 zonas** (`.pm-matrix-shell` flex): izquierda fija (Artículo|Precio|%Desc), media con `overflow-x`/`overflow-y` solo en sucursales, y derecha fija (Total|Eliminar); las 3 tablas se alinean por índice con alto de fila fijo (`--pm-row-h`) y el `scrollTop` de la zona media se espeja a izq./der. vía JS (`_bindMatrixScrollSync`). Se añadió `min-width:0` scoped (`main.app-content:has(.pm-matrix-viewport)`) y se eliminó `syncPmStickyCols`. El buscador vive como **última fila** de la matriz (línea nueva) en las 3 zonas; dropdown hacia arriba (`pm-art-dropdown--up`, `?v=masivo12`).

### Totales híbridos — estimado FE + validación bajo demanda (14/07/2026, `?v=masivo12`)

Para bajar costo de servidor (clientes con muchas sucursales / timeout de 8 s), **no** se llama a `POST …/preview/` en cada edición.

| Fuente | Cuándo | Comportamiento |
|--------|--------|----------------|
| **Estimado** (chip amber) | Al editar celdas, % desc. fila, desc. pie o agregar/quitar artículos | `marcarTotalesEstimados()` / `recalcularPreviewEstimado()` en el navegador |
| **Validando…** / **Validado** | Solo botón «Validar totales» (`refrescarPreview`) | Preview servidor opcional; puede avisar timeout si hay muchas sucursales |
| **Confirm pedido** | Modal resumen (`masivo_confirmar`) → al confirmar, modal de progreso (`masivo_progreso`) con stream NDJSON en vivo por sucursal (`?v=masivo16`). Preview en paralelo al abrir resumen. Avisos de timeout no bloquean. `POST …/confirmar/` con `"stream": true` crea los PEDs |

**Reglas FE (aproximación):** por celda con qty > 0: `neto_linea = precio_unitario_neto × qty × (1 − %desc_fila/100)`; suma → `neto_bruto`; desc. pie: `neto = neto_bruto × (1 − descPiePct/100)`; IVA prorrateando el pie sobre líneas con `alicuota_iva` del artículo (default 21 %); `total = neto + iva`; redondeo a 2 decimales (`money()`).

**Datos:** `alicuota_iva` incluido en `buscar_articulos_filtrados_ternas`, `_nombres_articulos` y `serializar_matriz` (JOIN `iva`, default 21).

**Estado Alpine:** `previewFuente` (`estimado` \| `servidor`), `previewEstimado`, getter `totalesPie`.

### Responsive móvil/tablet (14/07/2026)

- Viewport `<lg`: tabla oculta; **acordeón** por `id_cliente_domicilio` reutilizando `celda()` / `onCelda()` / `descFila()`.
- Panel preview/totales apilado verticalmente; botones alcanzables en pantalla estrecha.
- Encabezado de sucursal en móvil/PWA: solo nº + **un** botón expandir/contraer (sin chevron CSS duplicado; el total solo se muestra si hay importe).
- **Nivel A / PWA (16/07/2026):** ruta HTML y APIs `/ecom/api/mayoristapp/` permitidas en móvil; menú e-com filtrado (`ecom_compra`, `ecom_pedidos`, `ecom_pedido_masivo`) y `PWA_ECOM_DEEP_LINKS`. Pedido simple: deep link `ecom_compra` → `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple`. Permisos captura: `ecom.pedidos.crear` **o** `ecom.pedido_masivo.usar`. Ver `docs/general/MOBILE_SOLO_NIVEL_A.md`.

## Borrador (Postgres)

Modelos: `EcomPedidoMasivoDraft` + `EcomPedidoMasivoDraftCelda`.

| Estado | Significado |
|--------|-------------|
| `borrador` | Editable; autoguardado |
| `confirmando` | Lock anti doble submit |
| `confirmado` | Lote OK; links a `CodigoMovimiento[]` |
| `archivado` | Descartado al crear otro (Archivar y crear) |
| `anulado` | Soft-delete desde UI; aparece en hub columna **Anulado**; recuperable con Continuar / `POST …/abrir/` |

### Anular borrador (14/07/2026)

- Solo desde `borrador` o `confirmando` (este último se trata como borrador editable).
- `POST /ecom/api/mayoristapp/pedido-masivo/anular/` body `{draft_id}` → persiste `estado=anulado` (no borra filas).
- Hub: tarjeta en columna **Anulado**, subtítulo «Borrador anulado · Recuperable», URL `?draft=<pk>`.
- Al abrir un draft anulado (`abrir` o Continuar), se reactiva automáticamente a `borrador`.
- UI: modal canon `masivo_anular` (`pedidos_modal.html`); botón **Anular** en hero.

### Rendimiento del buscador de artículos (14/07/2026)

- La UI aplica debounce de 250 ms y cancela con `AbortController` la consulta anterior al seguir escribiendo; una respuesta obsoleta no puede dejar el estado «Buscando…».
- `GET …/pedido-masivo/articulos/` rechaza términos de menos de 2 caracteres y limita el resultado a 40 artículos (la UI solicita 20).
- El servicio mantiene el filtro de marcas/territorio y el `LIMIT`, pero precalcula las reglas de precio de las sugerencias en lote. Así evita el patrón N+1 anterior de resolver el precio mediante consultas independientes por cada artículo mostrado.
- La coincidencia textual continúa usando `LIKE '%término%'` para permitir hallar fragmentos, por lo que no garantiza uso de índice sobre nombre/código en catálogos muy grandes. Los resultados priorizan coincidencias exactas y por prefijo; si la medición en producción todavía supera el objetivo, el siguiente paso es medir `EXPLAIN` sobre la base afectada y evaluar un índice/`FULLTEXT` administrado por el catálogo central de esquema legacy.

### Resiliencia

- **Cierre / F5:** recuperar desde hub.  
- **Fallo batch:** compensar PED del lote, draft → `borrador` con celdas intactas + `ultimo_error` JSON por sucursal.  
- Nunca vaciar la matriz por error de checkout.

## Permisos

| Key | Uso |
|-----|-----|
| `ecom.pedidos.crear` **o** `ecom.pedido_masivo.usar` | Captura pedido simple y APIs matriz (`EcomPedidoCapturaPermission`) |
| `ecom.pedido_masivo.usar` | Abrir y confirmar matriz multi-columna |
| `ecom.pedidos.ver` | Ver borradores en hub |

## Endpoints (Phase 4)

| Método | Path | Uso |
|--------|------|-----|
| GET | `/ecom/api/mayoristapp/pedido-masivo/clientes/?q=` | Clientes con ternas del viajante |
| GET | `/ecom/api/mayoristapp/pedido-masivo/sucursales/?id_cliente=` | Columnas `cliente_domicilio` |
| POST | `/ecom/api/mayoristapp/pedido-masivo/abrir/` | Crear/recuperar draft + matriz |
| GET | `/ecom/api/mayoristapp/pedido-masivo/matriz/?draft_id=` | Releer matriz |
| POST | `/ecom/api/mayoristapp/pedido-masivo/celda/` | Autoguardado celda |
| GET | `/ecom/api/mayoristapp/pedido-masivo/articulos/?id_cliente=&q=` | Catálogo filtrado por marcas terna |

UI: `/ecom/mayoristapp/pedido-masivo-sucursales/?draft=<id>`  
UI modo simple: `/ecom/mayoristapp/pedido-masivo-sucursales/?modo=simple` (opcional `&cod_mov=`, `&draft=`, `&id_domicilio=`)

**Confirmación de lote (1 PED/sucursal):** implementada (Phase 5). El PV se resuelve
sin campo adicional en la UI: `id_punto_venta` recibido, PV activo de sesión,
PV asignado al usuario y, como último fallback, el primer PV disponible para ese
usuario. Si no existe ninguno, la API informa que falta configuración de PV para
la empresa o el usuario.

| Método | Path | Uso |
|--------|------|-----|
| POST | `/ecom/api/mayoristapp/pedido-masivo/confirmar/` | Batch + compensación; body `{draft_id, id_punto_venta?, stream?}` — ver protocolo NDJSON abajo |
| POST | `/ecom/api/mayoristapp/pedido-masivo/anular/` | Anular borrador en edición; body `{draft_id}` |

Servicio: `ecom.services.batch_checkout_masivo.confirmar_lote_masivo` (sync) y `confirmar_lote_masivo_stream` (generador NDJSON). Anulación: `ecom.services.pedido_masivo_matriz.anular_borrador_masivo_usuario`.

### Confirmación con progreso en vivo — NDJSON (14/07/2026, `?v=masivo16`)

Tras el resumen del modal (`masivo_confirmar`), el front envía `POST …/confirmar/` con `"stream": true` y cabecera comercial (`desc_pie_pct`, fechas, condición, lista). La respuesta es `Content-Type: application/x-ndjson; charset=utf-8`: **una línea JSON por evento**, sin array envolvente.

**Body (campos relevantes):**

```json
{
  "draft_id": 123,
  "stream": true,
  "desc_pie_pct": 0,
  "fecha_pedido": "2026-07-14",
  "fecha_entrega": "2026-07-20",
  "id_condventa": 1,
  "lista_id": 1
}
```

**Eventos emitidos (orden):**

| `event` | Campos | Descripción |
|---------|--------|-------------|
| `inicio` | `total` (int) | Cantidad de sucursales a procesar |
| `sucursal` | `index`, `total`, `id_cliente_domicilio`, `nombre`, `estado` | Por cada sucursal: `procesando` → `ok` o `error` |
| `sucursal` (ok) | + `codigo_movimiento`, `nro_comprobante` | PED creado |
| `sucursal` (error) | + `error` | Fallo en esa sucursal; el lote entra en compensación |
| `fin` | `ok`, `message`, `codigos_movimiento[]`, `errores{}`, `compensacion[]`, `matriz` | Cierre; `matriz` solo en este evento (serializada por la view) |

**Ejemplo de secuencia (2 sucursales):**

```ndjson
{"event":"inicio","total":2}
{"event":"sucursal","index":1,"total":2,"id_cliente_domicilio":10,"nombre":"Av. Corrientes 1234","estado":"procesando"}
{"event":"sucursal","index":1,"total":2,"id_cliente_domicilio":10,"nombre":"Av. Corrientes 1234","estado":"ok","codigo_movimiento":9001,"nro_comprobante":"0001-00001234"}
{"event":"sucursal","index":2,"total":2,"id_cliente_domicilio":20,"nombre":"Sucursal Norte","estado":"procesando"}
{"event":"sucursal","index":2,"total":2,"id_cliente_domicilio":20,"nombre":"Sucursal Norte","estado":"ok","codigo_movimiento":9002,"nro_comprobante":"0001-00001235"}
{"event":"fin","ok":true,"message":"Se crearon 2 pedido(s).","codigos_movimiento":[9001,9002],"errores":{},"compensacion":[],"matriz":{...}}
```

**Comportamiento:**

- Sin `"stream": true` → respuesta JSON única (compat tests / clientes legacy); HTTP 409 si falla parcial.
- Compensación ante fallo: igual que sync — anula PEDs ya creados en la corrida, draft → `borrador`, celdas intactas, `ultimo_error` por sucursal.
- UI (`pedidos_modal.html`, `dialogKind = masivo_progreso`): barra `hechos/total`, lista pendiente/en curso/OK/error, sin botón Cancelar mientras `confirmando`. Éxito → cierra a ~1,5 s; error → vuelve a `masivo_confirmar` editable a ~2,5 s.
- Nombres de sucursal: backend vía `listar_sucursales_cliente`; FE resuelve desde `this.sucursales` si falta `nombre` en el evento.

---

## Change `ecom-pedidos-usabilidad-supervisor` — oleadas A–E (13/07/2026)

Resumen del corte vertical que consolidó usabilidad de pedidos y supervisor operativo. Impacto en el masivo concentrado en **oleada D** y **E**:

| Oleada | Alcance | Impacto en masivo |
|--------|---------|-------------------|
| **A — Supervisor/vendedor operativo** | Resolver único `resolver_viajante_operativo` + cartera supervisor en `configuracion_ecom` | `batch_checkout_masivo.py` y `pedido_masivo_matriz.py` usan el `CodViajante` operativo (no el logueado) |
| **B — VCM simple + lista RO** | Clientes/artículos por ternas del viajante efectivo; badge de lista solo lectura | Selector de vendedor + badge de lista compartidos con el simple en `pedido_masivo_sucursales.html` |
| **C — Descuentos pedido simple** | % desc. por renglón (PATCH) y desc. al pie backend | Base de descuentos reutilizada por el masivo |
| **D — Masivo (precio, desc, preview)** | Precio real vía `price_rules_engine` por fila; % desc. fila + pie; endpoint `POST …/pedido-masivo/preview/` (límite blando ≤200 celdas≠0); JS extraído a `static/ecom/pedido_masivo_app.mjs`; modal canon `pedidos_modal.html` reemplaza `confirm()` | **Núcleo del cambio en masivo** |
| **E — Visual slate/sky** | Barrido de purple en el flujo de pedido | `pedido_masivo_sucursales.html` sin purple; toggle, foco y CTAs en sky/amber/rose; token compartido `.pedidos-badge-lista` |

**Totales:** preview híbrido — estimación FE instantánea + validación backend (`preview` / batch). Fechas al usuario en `dd/MM/yyyy`.

### Preview vs confirmación — stock (14/07/2026)

- **Preview** (`POST …/pedido-masivo/preview/`): **no** valida stock (`validar_stock=False` en `calcular_totales_lote_masivo`); los totales del pie se calculan aunque falte disponible.
- **Confirmación** (simple y masivo): respeta `configuracion_ecom.ecom_validar_stock_pedidos` (default **Si**). Con **No**, carrito y commit PED no bloquean por stock. Ver `docs/ecom/AJUSTES_VENTAS.md`.

Documentación de diseño y estado: `docs/order-ui-redesign/05-design-system-pedidos.md` y `10-estado-implementacion.md`.
