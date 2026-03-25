# OPT demanda (`ventana_pack`) — layout y jerarquía

**Plantilla:** `mpr/templates/mpr/ventana_pack.html`  
**Objetivo:** recuperar altura útil (menos franja oscura y menos aire hasta la tabla), coherencia cromática con MPR (morado), menos ruido en cabeceras de tabla y CTA principal alineado a patrones habituales (derecha en desktop).

## Análisis (síntesis)

| Área | Problema | Enfoque |
|------|----------|---------|
| Sección + migas | Mucho padding vertical y `mb-8` en migas | `py-4`/`sm:py-5`, migas `mb-3`/`sm:mb-4` |
| Bloque oscuro | `p-6`, `mb-6`, `shadow-lg` lo hacían muy alto | `p-3`/`sm:p-4`, `mb-3`/`sm:mb-4`, `rounded-lg`, `shadow-md` |
| Título + filtros | Banner “alto” con poco aprovechamiento horizontal | H1 más compacto en mobile; filas `gap-2`; fechas con `py-1` |
| Actualizar | Ámbar desentonaba con el resto del MPR | `bg-purple-600` + foco `ring-purple`; inputs con foco morado |
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

## Notas

- No se modificaron vistas, URLs ni formularios; solo clases y estructura HTML del template.
- Si en monitores muy altos se desea más filas visibles, subir el límite (p. ej. `min(28rem,58vh)`).
