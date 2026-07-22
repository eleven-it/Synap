# Manual de usuario – Stock e Inventario

Guía práctica del módulo **Stock** en Synap: consulta de inventario por etapa de fábrica y carga de movimientos de stock.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

**Manual HTML en la app:** **`/stock/manual/`** (requiere sesión). En las pantallas del módulo hay un botón **Ayuda** que abre este manual en la sección correspondiente. Regenerar HTML: `python3 scripts/generar_manuales_html.py`.

---

## 1. Acceso

Menú Synap → **Stock**.

| Pantalla | Dónde encontrarla |
|----------|-------------------|
| **Inventario por etapa** | Stock → Inventario |
| **Ingreso Mov. Stock** (alta de movimiento) | Stock → Ingreso Mov. Stock |

---

## 2. Inventario por etapa

### Para qué sirve

Ver, por artículo, el saldo en las etapas de fábrica:

- Producción  
- Semi elaborado  
- 2da selección  
- Terminado  

y un **Consolidado** (suma de esas etapas).

También muestra **Talle** y **Color** del artículo, útiles para controlar calidad y surtido.

### Columnas

| Columna | Significado |
|--------|-------------|
| **Artículo** | Código y nombre |
| **Talle** | Talle del artículo (si no hay dato, se muestra «—») |
| **Color** | Color sólido (ej. Negro) o combinación (ej. Rosa/Gris) |
| **Producción** | Saldo en depósitos de producción |
| **Semi elaborado** | Saldo en semi elaborado |
| **2da Selección** | Saldo en segunda selección |
| **Terminado** | Saldo en terminado |
| **Consolidado** | Suma de las cuatro etapas |

### Filtros

1. **Marcas:** puede elegir una o varias (vacío = todas).
2. **Artículo:** busque por código o nombre, o fije un artículo.
3. **Presentación:** **Pares** (por defecto) o **Docenas**.
4. Por defecto solo se listan artículos **con stock**; active incluir sin stock si lo necesita.
5. **Actualizar** aplica los filtros; **Limpiar** vuelve al estado inicial.

### Día a día

- Controle el avance del stock por etapa (producción → semi → 2da → terminado).
- Use Talle y Color al revisar planillas o surtido.
- Si Talle o Color aparecen en «—», el artículo aún no tiene ese dato cargado; no significa que el saldo sea cero.

---

## 3. Alta de movimiento

**Pantalla:** Stock → **Ingreso Mov. Stock**.

**Diseño:** una sola pantalla a ancho completo (sin pestañas). Arriba va la **cabecera del movimiento** (compacta, colapsable); debajo, el workspace de **Artículos**, que es el foco principal. Abajo, la barra fija **Cancelar** / **Confirmar movimiento**.

### Cabecera del movimiento

1. Complete los datos mínimos: **Fecha**, **Motivo** y **Depósito origen** (y **Depósito destino** si el motivo lo exige, p. ej. transferencia).
2. Según el motivo pueden aparecer campos adicionales (vendedor, cliente, referencia, pedidos internos/PEDI, proyecto, operario/máquina, valor variable, detalle).
3. Si faltan datos mínimos, el encabezado oscuro muestra el chip **Datos incompletos** y el botón **Agregar** permanece deshabilitado.
4. Use el chevron de la tarjeta **Cabecera del movimiento** para compactarla: al colapsar verá un resumen (motivo, depósito, fecha en formato **dd/MM/yyyy**).

### Artículos (workspace principal)

1. En la barra **Buscar artículo**, escriba nombre o código (o escanee en móvil).
2. El listado de sugerencias muestra **solo el nombre** del artículo. Navegue con **↓ / ↑**, confirme con **Enter** o cierre con **Esc**.
3. Indique **Movimiento** (Entrada/Salida, si el motivo lo permite) y **Cantidad**, luego **Agregar**.
4. La tabla lista los renglones con: **Cod. manual**, descripción, movimiento, cantidad, nro. de pedido interno (si aplica), lote, series y eliminar. No hay columna de código de sistema; el código manual se muestra completo.
5. Cuando tenga al menos un renglón, pulse **Confirmar movimiento**, revise el resumen y confirme.

### Consejos

- En **celular**, la carga es por tarjetas; el escáner de cámara aparece si el dispositivo lo permite.
- Motivos de armado/desarmado: puede usar `*` en la búsqueda para listar artículos ensamblados.
- No hay botón **Continuar** ni pestañas: cabecera y artículos conviven en la misma vista.

---

## 4. Mensajes frecuentes

- **Chip «Datos incompletos» / Agregar deshabilitado:** complete fecha, motivo y depósito origen (y destino si aplica).
- **«Código inexistente»:** el texto no coincide con un artículo; revise el código o busque por nombre.
- **«No hay artículos con los filtros seleccionados»** (inventario): amplíe marcas, quite el filtro de artículo o incluya sin stock.
- **Talle/Color en «—»:** falta el dato de talle/color; no implica saldo cero.
- **Inventario vacío con stock real:** revise en Producción → Config. Depósitos que cada depósito tenga el tipo de etapa correcto y que sume al stock.
- **Sin empresa activa:** seleccione la empresa al iniciar sesión.

---

*Manual de usuario – Stock e Inventario. Synap. Actualizado 22/07/2026.*
