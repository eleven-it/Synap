# OPT demanda (`ventana_pack`) — layout y jerarquía

**Plantilla:** `mpr/templates/mpr/ventana_pack.html`  
**Modal POST MPR (global):** El overlay de espera vive en `mpr/includes/mpr_post_loading_modal.html`, incluido desde `mpr/base_mpr.html`. Los formularios POST marcados con clase `mpr-post-loading` muestran el modal al enviar; textos opcionales con `data-mpr-loading-title` y `data-mpr-loading-subtitle`.

**Lista Packs:** `listar_ventana_pack` solo devuelve artículos con **cantidad a fabricar > 0** (saldo que no cubre ya pedido + reserva maestra); ver `docs/mpr/DIAGNOSTICO_DEMANDA_MPR.md`.  
**Objetivo:** recuperar altura útil (menos franja oscura y menos aire hasta la tabla), coherencia cromática con MPR (morado), menos ruido en cabeceras de tabla y CTA principal alineado a patrones habituales (derecha en desktop).

## Análisis (síntesis)

| Área | Problema | Enfoque |
|------|----------|---------|
| Sección + migas | Mucho padding vertical y `mb-8` en migas | `py-4`/`sm:py-5`, migas `mb-3`/`sm:mb-4` |
| Bloque oscuro | `p-6`, `mb-6`, `shadow-lg` lo hacían muy alto | `p-3`/`sm:p-4`, `mb-3`/`sm:mb-4`, `rounded-lg`, `shadow-md` |
| Título + filtros | Banner “alto” con poco aprovechamiento horizontal | H1 más compacto en mobile; filas `gap-2`; fechas con `py-1` |
| Actualizar | Ámbar desentonaba con el resto del MPR; el POST de sincronización puede tardar | `bg-purple-600` + foco `ring-purple`; inputs con foco morado; **modal global MPR** (`mpr-post-loading` + datos en el formulario; overlay `#mpr-post-loading-modal` en `base_mpr.html`) |
| Tablero | Botón sólido gris aceptable como secundario | Borde explícito, altura alineada con fila de fechas (`items-end`) |
| Pestañas + búsqueda | Tabs altos, mucho `mb-4` | `min-h-9`, menos `pb` en la franja |
| Tabla | Cabeceras slate/zinc fuertes (mucho color) | Fondos `slate-100`/`slate-50` suaves; grupo **Urgente** delimitado con `border-l-rose-*`; cuerpo con tintes `slate-50/90` y borde rosa suave en columnas urgentes |
| Altura tabla | Fijo `24.3rem` siempre | `h-[min(26rem,52vh)]` + `min-h-[14rem]` para adaptar a viewport |
| Continuar | Solo a la izquierda | Fila `justify-between`: contador a la izquierda, botón a la derecha (`sm:`); en móvil botón ancho completo debajo |

## Confirmar OPT (`ventana_pack_agrupar.html`)

| Área | Problema | Enfoque |
|------|----------|---------|
| Sección + migas | Igual que demanda: mucho aire arriba | `py-4`/`sm:py-5`, sin `min-h-screen`; fondo `slate-50`/`dark:slate-900` alineado a demanda; migas `mb-3`/`sm:mb-4` con tonos slate |
| Cabecera | Coherencia con pantalla anterior (demanda) | **Mismo bloque oscuro** que `ventana_pack`: `rounded-lg border-slate-700 bg-slate-800 p-3 sm:p-4 shadow-md`; H1 y ayuda en **blanco** / **slate-300**; asistente (si aplica) **dentro** del bloque; **fecha objetivo** en recuadro `slate-700` e `input` estilo fechas de demanda (`bg-slate-700`, texto claro, foco morado) |
| Fecha objetivo | Quedaba fuera del `<form>` (no se enviaba) | Atributo HTML5 `form="form-generar-opt"` en el `input` para asociarlo al formulario sin mover el bloque visual |
| Asistente | Banner wizard alto | Mismo patrón compacto que en `ventana_pack` |
| Tabla | Cabeceras `slate-300`/`zinc-300` pesadas | Mismo criterio que demanda: `gray-100`/`white`, bordes `border-l` y acento rosa solo en grupo **Urgente**; celdas cuerpo `gray-50/90` y bordes suaves |
| Filas | Mucho `py-3` | `py-2.5` en celdas editables y lectura |
| CTAs | Ambos a la izquierda | `sm:justify-between`: **Volver** a la izquierda, **Generar OPT** a la derecha; en móvil **Generar** primero (orden flex) y ancho completo para tacto |

## Datos en pestaña Unidades (código manual y nombre)

En la tabla de **Unidades**, la columna combinada «Cod. Manual y nombre artículo» usa `codigo_manual` e `descripcion_articulo` devueltos por `_listar_unidades_por_demanda` en `mpr/services.py` (lectura desde `articulo.id_manual` y `articulo.NombreArticulo`, con alias SQL y filas normalizadas para lectura estable con `DictCursor`). El valor mostrado como código manual es **solo** `articulo.id_manual` (normalizado con `str_codigo_manual_articulo` en `core.utils.administranet_types`). **No** se sustituye por `CodigoArticulo` / `CodigoArticuloT`: varias variantes comparten el mismo código de talón (p. ej. 2402) y no equivale al código manual jerárquico. Si `id_manual` está vacío en la base, se muestra «-»; el talón sigue en la columna «Cod. sistema» / `codigo_articulo` cuando aplique la pantalla.

En **Packs** y listas que lean `lista_produccion_agrupada` + `articulo`, el mismo criterio aplica a `codigo_manual` en `listar_lista_produccion_agrupada` y `listar_opt_listado`.

## Notas

- El modal de espera es solo en cliente (no cambia vistas ni servicios). Misma clase `mpr-post-loading` en demanda (**Actualizar**, **Continuar**), asistente, tablero, OPT/OPP, BOM, depósitos, etc.
- El formulario **Actualizar** conserva `id="form-ventana-pack-actualizar"` por si hay scripts que lo referencian.
- Si en monitores muy altos se desea más filas visibles, subir el límite (p. ej. `min(28rem,58vh)`).
