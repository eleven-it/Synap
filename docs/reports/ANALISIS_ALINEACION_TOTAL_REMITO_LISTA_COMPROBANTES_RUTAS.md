# Análisis exhaustivo — Alineación a la derecha de «TOTAL REMITO» (informe comprobantes en ruta)

**Alcance:** tabla generada en `reports/static/reports/js/dashboard.js` (`renderTable`), slug `comprobantes-rutas` / `mayoristapp-lista-comprobantes-rutas`, columna `total_remito` y cabecera homónima.

---

## 1. Capas que intervienen en la alineación

| Capa | Qué puede impedir `text-align: right` |
|------|----------------------------------------|
| **UA (navegador)** | Muchos navegadores aplican a `<th>` alineación centrada por defecto si no hay regla más fuerte. |
| **Tailwind / CSS compilado** | Clases como `text-right` solo funcionan si existen en `theme/static/css/dist/styles.css`. El `content` de Tailwind incluye `../../reports/static/**/*.js`, pero un build desactualizado puede omitir clases nuevas. |
| **Herencia desde `<table>`** | La tabla genérica se creaba primero con `text-left` en la clase; para logística se **sobrescribe** la `className` completa sin `text-left` (solo en el branch `isLogisticaListaCrTable`). Si en el futuro se volviera a añadir `text-left` al `<table>`, heredaría en celdas sin `text-align` propio. |
| **`colgroup` + `table-layout: fixed`** | Reparte el ancho en columnas iguales; **no** fuerza centrado, pero con celdas muy estrechas un importe largo puede **partir en varias líneas**; la segunda línea alineada a la derecha puede **parecer** visualmente “más al centro” del hueco total entre columnas. |
| **Tabla anidada (agrupación)** | El cuerpo con agrupación va dentro de `<td colspan="…"><table>…</tbody></table></td>`. Es un **árbol de formato independiente**: herencia CSS desde la tabla exterior no cruza al contenido de la interior salvo propiedades heredables globales (`font-family`, `color`, `direction`, etc.). |
| **Dirección del texto (`dir`)** | Si un ancestro tuviera `dir="rtl"` o `direction: rtl`, los números y el símbolo `$` pueden reordenarse por el algoritmo bidi y **romper** la percepción de alineación. |
| **`Intl.NumberFormat` / moneda** | `formatCurrency` usa `es-AR`; puede insertar espacios tipográficos o caracteres Unicode de moneda; con bidi raro el flujo visual puede desviarse (mitigación: `dir="ltr"` en tablas de este informe). |
| **Plugins Tailwind** | `@tailwindcss/forms` y `@tailwindcss/typography` pueden tocar `input/select/textarea` y `.prose table`; el widget de informe **no** está envuelto en `.prose` en `dashboard_detail.html`, pero conviene tenerlo en cuenta si se mueve el bloque. |
| **Scroll / sticky** | `thead` sticky + `overflow` en el contenedor puede producir **desfase horizontal** entre cabecera y cuerpo en casos extremos (scrollbar, subpixel); eso se percibe como columnas “desalineadas”, no como texto centrado dentro de la celda. |
| **Especificidad / `!important`** | Alguna hoja global con `th { text-align: center !important }` vencería clases utilitarias sin `!important`. Mitigación aplicada: **`element.style.textAlign = "right"`** en DOM y **`style="text-align:right"`** en HTML inyectado (alta especificidad, solo superada por `!important` en cascada). |

---

## 2. Rutas de código que pintan «TOTAL REMITO»

1. **Cabecera:** bucle `fieldKeys.forEach` → `isCurrencyField(key)` (incluye `total_remito` explícito) → clases + `th.style.textAlign`.
2. **Filas sin agrupación:** mismo bucle sobre `row` → `td` + `td.style.textAlign` para moneda.
3. **Filas con agrupación (detalle):** `logisticaListaDetailRowHtml` → string HTML con `style="text-align:right"` en `<td>` monetarios.
4. **Filas de grupo (subtotal):** `renderLogisticaGroupedTreeHtml` → `<td style="text-align:right">` para columnas en `metricKeys` (derivadas de `isCurrencyField`).

Si **cualquiera** de estas rutas omitiera alineación, solo fallaría ese modo de vista (agrupado vs plano).

---

## 3. Medidas ya aplicadas en código (referencia)

- `isCurrencyField`: retorno explícito `true` para `total_remito`.
- Cabeceras y celdas monetarias (DOM): `style.textAlign = "right"`; no monetarias: `left`.
- HTML de filas agrupadas: `style="text-align:right"` en celdas monetarias.
- Tabla principal del informe: `dir="ltr"`; tabla anidada: `dir="ltr"`.
- Celdas monetarias: `whitespace-nowrap` (clase + inline donde aplica) para evitar **partición en dos líneas** del importe que confunde la lectura junto a `table-fixed`.

---

## 4. Qué revisar si el problema reaparece

1. **Build de Tailwind** tras cambiar clases en `dashboard.js`: regenerar `styles.css` si el entorno no lo hace en CI.
2. **Caché del navegador** del bundle `dashboard.js` (query `?v=` en `dashboard_detail.html`).
3. **Inspeccionar en DevTools** la celda concreta: ¿qué regla gana en “Computed” para `text-align`? ¿Hay `!important` externo?
4. **Nombre de campo API:** si el backend dejara de enviar `total_remito` (p. ej. otro alias), `isCurrencyField` podría no coincidir y la columna se trataría como texto izquierdo.

---

## 5. Conclusión

No hay una **única** causa: la combinación más frecuente en este stack es **UA / herencia + clases Tailwind no presentes o sobrescritas + posible salto de línea del importe** en columnas estrechas por `table-fixed` y `colgroup` equitativo. Las mitigaciones encadenadas (estilo inline, `dir="ltr"`, `nowrap`) cubren esas capas sin depender solo de utilidades CSS.

### 5.1 Verificación posterior (si aún fallaba la alineación)

Si con `th.style.textAlign` / `td.style.textAlign` y clases Tailwind el navegador **seguía** mostrando la columna sin alinear a la derecha, la causa más plausible es una **hoja de estilos con `text-align` y `!important`** (o reglas con igual especificidad que dependen del orden de carga) que **vencen al estilo en línea sin `!important`**. En ese caso la corrección aplicada en código es usar **`element.style.setProperty("text-align", "right", "important")`** en cabeceras y celdas monetarias del informe logística, y **`text-align:right!important`** en los fragmentos HTML de filas agrupadas / detalle.

Además, si `total_remito` llega como **cadena** desde la API, `formatCurrency` debe **coercionar a número** (incl. formato miles `1.234,56`) para no dejar texto crudo que pueda interactuar mal con el algoritmo bidi aunque `text-align` sea correcto.

### 5.2 Columna vecina «ACCIONES» (`inline-flex`) y refuerzo por scope

Si el `td` de ACCIONES usa un hijo **`inline-flex`** shrink-to-fit, el bloque de botones puede quedar **centrado en la celda** (comportamiento de alineación de contenido inline en celdas). Eso no cambia el `text-align` del `td` de TOTAL REMITO, pero en tablas con **`table-layout: fixed`** y columnas estrechas puede **confundir** visualmente el límite entre columnas. Mitigación: contenedor **`display:flex; width:100%; align-items: flex-end`** (clase `synap-lc-actions-inner`). Para montos, un **`span.synap-lc-money-inner`** a ancho completo con `text-align: right !important` bajo `.synap-logistica-lista-cr-table` evita depender solo de utilidades Tailwind generadas por el CDN para nodos creados en JS.

*Documento generado para trazabilidad técnica; alinear con cambios en `dashboard.js` y versión de script en `dashboard_detail.html`.*
