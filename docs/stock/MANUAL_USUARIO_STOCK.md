# Manual de usuario – Stock e Inventario

Guía práctica del módulo **Stock** en Synap: consulta de inventario por etapa de fábrica y orientación para cargar movimientos.

**Antes de empezar:** iniciar sesión y seleccionar la empresa con la que va a trabajar.

---

## 1. Acceso

Menú Synap → **Stock**.

| Pantalla | Dónde encontrarla |
|----------|-------------------|
| **Inventario por etapa** | Stock → Inventario |
| Alta de movimiento | Stock → ingreso / movimiento (según el menú de su empresa) |

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

1. Complete la **cabecera**: motivo, fecha, depósitos origen/destino y detalle según el motivo.
2. Pase a la pestaña **Artículos**: busque por código o nombre, escanee si aplica y cargue cantidades.
3. Confirme el movimiento. En celular, el botón principal suele estar arriba.

---

## 4. Mensajes frecuentes

- **«No hay artículos con los filtros seleccionados»:** amplíe marcas, quite el filtro de artículo o incluya sin stock.
- **Talle/Color en «—»:** falta el dato de talle/color; no implica saldo cero.
- **Inventario vacío con stock real:** revise en Producción → Config. Depósitos que cada depósito tenga el tipo de etapa correcto y que sume al stock.
- **Sin empresa activa:** seleccione la empresa al iniciar sesión.

---

*Manual de usuario – Stock e Inventario. Synap. Actualizado 20/07/2026.*
