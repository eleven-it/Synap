# Pedido masivo por sucursales

**Change:** `ecom-pedidos-hub-kanban-masivo-sucursales` · UX contexto: `ecom-pedido-masivo-ux-contexto`  
**Consolidado hub/lote:** `ecom-pedido-masivo-consolidado-hub` (22/07/2026)  
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

### Selección de sucursal en simple — 16/07/2026

Al elegir cliente, la pantalla consulta sus domicilios operativos. Si existe uno solo,
se selecciona automáticamente; si no existe ninguno, informa el error correspondiente;
si hay más de uno, el usuario debe elegir la **Sucursal** antes de abrir el borrador.
La API rechaza aperturas simples sin domicilio en este último caso con
`code=requiere_sucursal`, por lo que nunca toma arbitrariamente la primera sucursal.
Al cambiar la sucursal de un borrador simple existente, sus celdas se reasignan al nuevo
domicilio para conservar las cantidades en la única columna del pedido.

### UX PWA P0 — 17/07/2026

Ajustes de captura móvil (<lg) sin tocar lógica de borrador/confirm ni la matriz desktop:

| Criterio | Detalle |
|----------|---------|
| **CA-1** | Inputs/select/textarea en `.pm-matrix-viewport` con **font-size ≥ 16px** (`1rem`) y **min-height ≥ 44px** (`2.75rem`) para evitar zoom automático en iOS Safari. |
| **CA-2** | Sin `min-height: 100dvh` en móvil: scroll de **página** (`height: auto`, `overflow-y: visible`) + `padding-bottom` con `env(safe-area-inset-bottom)`. |
| **CA-3** | Filas móvil (simple y acordeón masivo): layout **vertical** con labels visibles («% desc.», «Packs» / «Cantidad») y grid 2 columnas (% estrecho, cantidad ancha). |
| **CA-4** | `.pm-preview-panel` **sticky** al pie con fondo sólido; botones eliminar/acordeón ≥ 44px; `scrollIntoView` con `block: 'nearest'` al enfocar fecha. |

Archivos: `pedidos_page_styles.html`, `pedido_masivo_sucursales.html`, `pedido_masivo_app.mjs`.

### Layout matriz: simple vs masivo + PWA — 17/07/2026

Ambos modos comparten el shell de 3 zonas (`.pm-matrix-shell`) en desktop y el
patrón de tarjetas en móvil, pero el reparto de ancho difiere:

| Modo | Desktop (lg+) | Móvil / PWA (<lg) |
|------|---------------|-------------------|
| **Simple** (1 sucursal) | Clase `pm-matrix-shell--simple`: la **descripción del artículo predomina**; cantidad fija `--pm-col-suc: 5.7rem` (~6 dígitos + 20%). Buscador en **primera fila**; dropdown abre **hacia abajo**. | **Lista plana** + buscador siempre visible. Scroll de página (`height: auto`, sin `100dvh`). |
| **Masivo** (N sucursales) | Distribución actual: zona media con **scroll-x** en sucursales (`.pm-ztable-mid` `min-width:100%`). | **Acordeón** por sucursal (primera abierta). Mismo scroll de página en PWA. |

**Foco (móvil + desktop):** los inputs de cantidad se duplican en el DOM (matriz
desktop + acordeón/lista móvil) con el mismo `data-pm-qty`. `_qtyInputVisible()`
elige el input **visible** (`offsetParent !== null`) según viewport, y
`focusBuscadorArt()` prefiere `#pm-art-mob` en `<lg`. Así, tras agregar un
artículo, el foco cae en el campo realmente pintado y la carga fluye.

### Permisos (OR)

| Key | Uso |
|-----|-----|
| `ecom.pedidos.crear` **o** `ecom.pedido_masivo.usar` | Captura en modo simple y APIs de matriz (`EcomPedidoCapturaPermission`) |
| `ecom.pedido_masivo.usar` | Matriz **multi-columna** (modo masivo sin `modo=simple`) |
| `ecom.pedidos.ver` | Ver borradores y PED en hub |

## Flujo (14/07/2026 — barra contexto + auto-apertura)

1. **Tarjeta de contexto comercial** densa y colapsable (`.pm-context-card`): grid 2 columnas con **label + campo en la misma línea** (`.pm-field-row` + `.pm-label-inline`). Orden: fecha pedido | fecha entrega; vencimiento | lista; cliente | condición. Las fechas usan `input type="date"` nativo ligado al ISO del estado (`cabecera.fecha_pedido`/`fecha_entrega`/`vencimiento`) y sincronizan su espejo `*_display` (dd/MM/yyyy) vía `onCabeceraFechaIso`. Anchos semánticos: fechas `w-[9.5rem]/max-w-[10rem]`, cliente `flex-1 min-w-[12rem]`, lista/condición `w-[14rem]/max-w-[16rem]`. Chevron en el eyebrow expande/compacta (estado Alpine `contextoAbierto`, default `true`, persistido en `sessionStorage['pm-contexto-abierto']`); al compactar solo se muestra una fila resumen (cliente + fechas clave) para liberar alto a la matriz.
2. **Hero oscuro (una fila):** título + badge «Borrador #N»; acciones a la derecha: **vendedor operativo** (antes de Anular), Anular, Hub y **Confirmar pedido** (`bg-orange-500`, mismo naranja CTA Synap del navbar). Tras confirmar (o PED en solo consulta) aparece **Nuevo** (dropdown purple: Pedido simple | Masivo sucursales), igual que en el Hub. Sin subtítulo de packs/autoguardado.
3. Al **elegir cliente** en el buscador predictivo, el front invoca automáticamente `POST …/abrir/` (misma semántica que antes tenía el botón). Spinner inline «Abriendo borrador…» durante la petición; guard anti doble POST.
3. **Matriz siempre visible** desde el primer render: shell de tabla (desktop) o acordeón por sucursal (móvil). Estados vacíos:
   - Sin borrador → guía «Elegí un cliente…»
   - Borrador sin sucursales → alerta amber
   - Borrador sin filas → guía «Agregá artículos…» + fila buscador al pie (solo con `draftId`)
4. Columnas = `cliente_domicilio` no anulados con ≥1 **relación** activa (vendedor operativo + cliente) cuando VCM está activo; si no, todos los domicilios activos. Orden de columnas: **ascendente numérico por `NroCalle`**. Encabezado = **`Suc ` + `NroCalle`** en **negrita** (ej. `Suc 14`). Click en la celda del encabezado (desktop) o en la fila del acordeón (móvil) abre un modal con calle, dpto, distrito, provincia y zona. En móvil, el chevron expande/colapsa el acordeón sin abrir el modal. Ver `docs/ecom/VENDEDOR_CLIENTE_MARCA.md`.  
5. Filas = artículos **Terminado** de marcas asignadas con **paridad carrito/precio**: `Discontinuo='No'` y `ecommerce='Si'` (mismo criterio que `obtener_articulo_row_precio` / `agregar_item`). El buscador predictivo (`buscar_articulos_filtrados_ternas`) no ofrece ítems que luego fallarían en preview/confirm con «Artículo no encontrado o inactivo». Criterios de búsqueda tipada (≥2 caracteres, `tam=20`): código de sistema (`IDArt`/`CodigoArticuloT`), `id_manual`, nombre y **código de barra** (`NroCodBarra`). **Flecha abajo** (o botón ▾) lista **todo** el catálogo filtrado (`?todos=1`, sin mínimo de 2 caracteres; tope 5000). Al navegar con ↑/↓ el ítem resaltado hace `scrollIntoView({ block: 'nearest' })` dentro del dropdown (`max-h-56`), mismo patrón que el catálogo mayorista. Desktop y móvil.  
   Columna **Precio** = precio real del motor (lista del cliente). Columna **STOCK** = packs disponibles Terminado (ver § stock abajo).  
6. Celdas = cantidad en **packs**. Columna de sumatoria: **Total packs**. Enter en la última sucursal vuelve al buscador. Con más de una línea de artículo, la matriz muestra fila **Totales** con suma de packs por sucursal (y total packs en la columna Total). Buscador con **multi-select** (checkbox + «Agregar seleccionados»); chip **Mostrar/Ocultar todos** en encabezado Artículo.
7. **Fecha de entrega** obligatoria al confirmar: si falta, modal de aviso y foco en el campo. Cliente en UI sin `(cod: N)`.  
8. Confirmar → **1 PED por sucursal** con `cliente_datos_adicionales.id_cliente_domicilio`.
9. **Importar Excel (13/08/2026, `?v=masivo42`):** con borrador editable, la tarjeta de contexto ofrece **Descargar plantilla** e **Importar Excel**. La plantilla trae el catálogo VCM (SuperArt/`id_manual` + nombre) y columnas de sucursal; **solo las cantidades son editables** (hoja protegida, sin precios ni descuentos). Tope de filas de catálogo: 5000 (red de seguridad; en `administranet` prod al 13/08/2026 hay 310 Terminado con ecommerce). Fila 1 oculta = `id_cliente` + `id_cliente_domicilio`. Hoja `_Synap` (veryHidden) identifica cliente y vendedor: al subir, si no coinciden con el pedido abierto → HTTP 409 y el borrador no cambia. **Reemplazo total** de celdas; pie ← `cliente.Descuento` y renglón ← `descuento_por_cli`. El import **no** valida stock (sí preview/confirmar). Sin cantidades, `.csv`, Excel corrupto o sin hoja `Pedido` → no se modifica el borrador. Modal Synap (`masivo_importar`); sin `alert`/`confirm`.

### Matriz — layout viewport, scroll y columnas fijas izq./der. (14/07/2026)

**Shell de viewport fijo (solo desktop `≥lg`):** la página no hace scroll horizontal ni vertical propio; el `scroll` vive dentro de la matriz. Estructura flex vertical dentro de `h-[calc(100dvh-4.5rem)]`:

- `<section.pm-matrix-viewport … overflow-hidden>` + `div.mx-auto … min-w-0` → evita que la tabla (ancho `max-content`) desborde la página completa. En desktop su altura efectiva descuenta header (4rem), padding del shell (4rem) y status bar (2rem): `calc(100dvh - 8rem)`.
- **Contexto (arriba, `flex-shrink-0`):** migas, hero oscuro, alertas y tarjeta de contexto comercial. Siempre visibles.
- **Matriz (medio, `flex-1 min-h-0 min-w-0`):** contenedor `.pm-matrix-scroll` con `overflow-auto` → **único** scroll horizontal (sucursales) y vertical (filas). No empuja fuera contexto ni pie.
- **Pie (abajo, `flex-shrink-0`):** `.pm-preview-panel` (descuento de lote, botón «Actualizar preview», NETO/IVA/TOTAL con chip **Estimado** / **Validado**). Siempre visible salvo viewport muy bajo (entonces la matriz encoge, no el pie).

Si las sucursales superan el ancho del viewport, la matriz hace **scroll horizontal** y permanecen fijas (sticky):

| Columna | Lado | Comportamiento |
|---------|------|----------------|
| **Artículo** | Izq. (`left: 0`) | Absorbe el sobrante del viewport (`min` ~16 rem); nombre en 2 líneas; chip **Mostrar/Ocultar todos** en el encabezado |
| **Precio** | Izq. (`left: --pm-left-precio`) | Fijo ~5.5 rem; `left` medido en runtime (`syncPmStickyCols`) |
| **% Desc.** | Izq. (`left: --pm-left-desc`) | Fijo ~4.25 rem; sombra derecha como límite con sucursales |
| **STOCK** | Izq. (zona fija, antes de sucursales) | Fijo `--pm-col-stock: 5.5rem`; packs; «Sin stock» / «—» |
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

**Stock Terminado (packs):** cada ítem del catálogo (`GET …/pedido-masivo/articulos/`) y cada fila de artículo en la matriz (`serializar_matriz` / `GET …/matriz/`) incluye `stock_disponible_packs` (número, hasta 3 decimales). Origen: depósito físico con `tipo_mpr = 'Terminado'` (`get_deposito_terminado_mpr` en `mpr/services.py`); disponible = `max(0, saldo − saldo_pedido_cliente)` vía `StockService.get_disponible_map` (bulk, sin N+1). Unidad: packs según `multiplo_cantidad_vta` / `multiplo_empaque` (misma convención que validación de celdas). Si no hay depósito Terminado configurado, el campo es `0`.

#### Columna stock, catálogo completo y multi-select — 31/07/2026 (`?v=masivo40`)

| Aspecto | Comportamiento |
|---------|----------------|
| **Columna STOCK** | Desktop shell 3 zonas: columna fija izquierda entre % Desc. y sucursales; orden Artículo \| Precio \| % Desc. \| STOCK. Cabeceras alineadas en la misma línea que las sucursales; el chip «Mostrar todos» queda debajo de Artículo. Valor al cargar fila (`aplicarMatriz`, `elegirArticulo`, bulk). Formato: entero tabular; `0` → chip «Sin stock» (rose); `null`/`undefined` → «—». **No** se muestra en el dropdown de búsqueda. PWA: sublínea `stock N` / `sin stock` en tarjeta/acordeón. Token CSS `--pm-col-stock: 5.5rem`; buscador `colspan="4"`. |
| **Chip Mostrar todos ↔ Ocultar todos** | Pill estilo filtros reportes en `<th>` Artículo (desktop) y barra bajo buscador móvil (+ contador N artículos). Estado `catalogoDesplegado` (default `false`). **Mostrar todos:** modal espera + `GET …/articulos/?todos=1`; agrega filas vacías no existentes (con `stock_disponible_packs` y múltiplos); `catalogoDesplegado=true`. **Ocultar todos:** modal espera; quita filas cuya suma de packs en todas las sucursales es 0 (`celdas`); conserva las con qty>0 en alguna sucursal; `catalogoDesplegado=false`. Borrar fila manual con trash → `catalogoDesplegado=false`. Sin toasts de éxito; solo errores de red. Deshabilitado si `!matrizEditable` o sin `idCliente`/`draftId`. |
| **Dropdown multi-select** | Checkbox por ítem; click fila/checkbox toggle selección (`articulosSeleccionados`). Footer sticky «Agregar seleccionados (n)»; Enter con selección agrega bulk; sin selección → `elegirResaltadoArt`. `_fetchArticulos` mapea `stock_disponible_packs` y `multiplo_*` (no visibles en listbox). |
| **Modal espera** | Overlay `esperaOperacion` + mensaje «Procesando…» para bulk Mostrar/Ocultar y agregar seleccionados (si N>15). |

Archivos: `pedido_masivo_sucursales.html`, `pedidos_page_styles.html`, `pedido_masivo_app.mjs`.

**Estado Alpine:** `previewFuente` (`estimado` \| `servidor`), `previewEstimado`, getter `totalesPie`.

### Responsive móvil/tablet (14/07/2026)

- Viewport `<lg`: tabla oculta; **acordeón** por `id_cliente_domicilio` reutilizando `celda()` / `onCelda()` / `descFila()`.
- Panel preview/totales apilado verticalmente; botones alcanzables en pantalla estrecha.
- Encabezado de sucursal en móvil/PWA: prefijo **`Suc `** + nº (ej. `Suc 14`) + **un** botón expandir/contraer (sin chevron CSS duplicado; el total solo se muestra si hay importe).
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
| GET | `/ecom/api/mayoristapp/pedido-masivo/articulos/?id_cliente=&q=` | Catálogo filtrado por marcas terna; cada ítem trae `stock_disponible_packs` |
| GET | `/ecom/api/mayoristapp/pedido-masivo/plantilla-excel/?draft_id=` | Descarga `.xlsx` con catálogo VCM (código + nombre) y sucursales; cantidades editables; identifica cliente |
| POST | `/ecom/api/mayoristapp/pedido-masivo/importar/` | Multipart `draft_id` + `archivo` (.xlsx). **Reemplaza** el borrador. Exige plantilla del mismo cliente/vendedor. Valida cuaterna VCM. Import ok: `descuento_pie_pct` ← `cliente.Descuento`. Sin cantidades o errores → HTTP 409, no modifica celdas ni pie |

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

Tras el resumen del modal (`masivo_confirmar`), el front envía `POST …/confirmar/` con `"stream": true` y cabecera comercial (`desc_pie_pct`, fechas, condición, lista). El front usa `Accept: */*` y la vista declara un renderer NDJSON, por lo que también negocia `Accept: application/x-ndjson` sin HTTP 406. La respuesta sigue siendo `Content-Type: application/x-ndjson; charset=utf-8`: **una línea JSON por evento**, sin array envolvente.

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

### Unidad de empaquetado (múltiplo de cantidad) — 20/07/2026

Las cantidades cargadas en la matriz (modo masivo y **modo simple**) deben respetar la **unidad de empaquetado** del artículo:

| Campo MySQL (`articulo`) | Uso en Synap |
|--------------------------|--------------|
| `multiplo_cantidad_vta` | Unidad de empaquetado de venta. Fuente única de validación. |
| `multiplo_empaque` (API/FE) | Valor resuelto por `multiplo_empaque_venta()` en `ecom/services/multiplo_empaque.py` (= `multiplo_cantidad_vta` si > 0; else 1). |

**Nota:** no se usa `multiplo_vta` para esta validación.

**Regla:** cantidad `q > 0` debe ser múltiplo entero de `multiplo_empaque`. Si `multiplo_empaque ≤ 1`, no se valida.

**Validación:**

- **Autoguardado celda** (`POST …/celda/`): rechaza con `code=multiplo_empaque` y mensaje en español.
- **Confirmar lote** (`batch_checkout_masivo`): rechaza antes de crear PEDs; devuelve `infracciones_multiplo[]`.
- **Front** (`pedido_masivo_app.mjs`): modal `aviso` al editar celda inválida; bloqueo en «Validar totales» y antes de abrir confirmación; borde ámbar en inputs inválidos.

### Preview vs confirmación — stock (14/07/2026)

- **Preview** (`POST …/pedido-masivo/preview/`): **no** valida stock (`validar_stock=False` en `calcular_totales_lote_masivo`); los totales del pie se calculan aunque falte disponible.
- **Confirmación** (simple y masivo): respeta `configuracion_ecom.ecom_validar_stock_pedidos` (default **Si**). Con **No**, carrito y commit PED no bloquean por stock. Ver `docs/ecom/AJUSTES_VENTAS.md`.

Documentación de diseño y estado: `docs/order-ui-redesign/05-design-system-pedidos.md` y `10-estado-implementacion.md`.

## Post-confirmación y resumen de lote (22/07/2026)

Tras confirmar un lote masivo (`batch_checkout_masivo` exitoso):

| Aspecto | Comportamiento |
|---------|----------------|
| `estado_aprobacion_lote` | Con subflag `ecom_aprobacion_pedidos_activa` ON y PED pendientes comerciales → `pendiente`; sin subflag → `-` |
| Modal éxito | Incluye CTA **Ver resumen del lote** hacia `/ecom/mayoristapp/pedidos/lote/<draft_id>/` y mensaje de que la autorización comercial es a nivel lote |
| Hub | Tarjeta `lote_masivo` en la columna Kanban que corresponda; PED hijos **no** se muestran en hub (acceso vía resumen del lote) |
| Matriz read-only | Pestaña «Qué se cargó» del resumen embebe `/ecom/mayoristapp/pedido-masivo-sucursales/?draft=<id>&readonly=1` con shell **sin navbar** (`ecom/base_embed.html`); permite abrir drafts `confirmado` solo para lectura (sin edición, autoguardado ni confirmar) |

Servicio resumen: `ecom/services/lote_resumen.py`. Pantalla: `ecom/templates/ecom/lote_resumen.html`.

El resumen lista solo sucursales del territorio VCM del viajante del draft (intersección con celdas del draft); se incluyen además domicilios con PED real en MySQL aunque queden fuera de VCM.
