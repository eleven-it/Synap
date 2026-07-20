# Manual de usuario – Stock e Inventario

Manual operativo del módulo **Stock** en Synap, con foco en **Inventario por etapa** (saldos MPR) y orientación al alta de movimientos.

**Requisitos:** empresa activa en sesión y permiso adecuado (`stock.consultas` para inventario; permisos de movimiento según la operación).

**Referencias técnicas:** [INVENTARIO_TABLA_MPR.md](INVENTARIO_TABLA_MPR.md), [ALTA_MOVIMIENTO_UX.md](ALTA_MOVIMIENTO_UX.md), campos talle/color [../mpr/ARTICULO_CE_TALLES_COLOR.md](../mpr/ARTICULO_CE_TALLES_COLOR.md).

**Versión HTML en la app:** `/stock/manual/` (archivo estático en `stock/static/stock/manuales/`). Fuente: este Markdown; regenerar con `python scripts/generar_manuales_html.py`.

---

## 1. Acceso

Desde el menú Synap → **Stock**.

| Pantalla | Menú típico | Ruta |
|----------|-------------|------|
| **Inventario por etapa** | Stock → Inventario | `/stock/inventario/` |
| Alta / listado de movimientos | Stock → movimientos (según menú) | `/stock/...` (ver plantillas de movimiento) |

El inventario por etapa **reemplaza** la antigua consulta ficha (`/stock/consulta-ficha/` eliminada).

---

## 2. Inventario por etapa

**Permiso:** `stock.consultas`.

### Para qué sirve

Ver, por artículo, el saldo en los depósitos que **suman stock** y tienen etapa MPR configurada (`deposito.tipo_mpr`), más un **Consolidado** (suma de las cuatro etapas).

También muestra **Talle** y **Color** del artículo (campos especiales AdministraNET), útiles para controlar calidad y producción.

### Columnas

| Columna | Significado |
|--------|-------------|
| **Artículo** | Código compuesto (manual − proveedor si aplica) y nombre |
| **Talle** | Valor CE TALLES (vacío → «—») |
| **Color** | Valor CE COLOR: sólido (`Negro`) o combinación (`Rosa/Gris`) |
| **Producción** | Saldo en depósitos `tipo_mpr = Produccion` |
| **Semi elaborado** | `SemiElaborado` |
| **2da Selección** | `2daSeleccion` |
| **Terminado** | `Terminado` |
| **Consolidado** | Suma de las cuatro etapas anteriores |

Solo entran depósitos con `suma_stock = 'Si'` y `anulado = 'No'`.

### Filtros y presentación

1. **Marcas:** tags multi-selección (vacío = todas).
2. **Artículo:** búsqueda predictiva por código o nombre (≥ 2 caracteres), o fijar un artículo concreto.
3. **Presentación:** **Pares** (unidades, default) o **Docenas** (docenas de pares + pares debajo).
4. **Solo con stock** / incluir ceros: por defecto solo artículos con consolidado &gt; 0; activar incluir sin stock si hace falta.
5. **Actualizar** aplica filtros; **Limpiar** vuelve al estado base.
6. Paginación: 150 artículos por página.

### Cómo usarlo en el día a día

- Controlar stock por etapa de fábrica (producción → semi → 2da → terminado).
- Cruzar con **Talle/Color** al armar planillas o revisar surtido.
- Si Talle/Color aparecen vacíos, el artículo aún no tiene valor en campos especiales CE (cargar en AdministraNET o pedir carga masiva al equipo).

---

## 3. Alta de movimiento (orientación)

Pantalla de alta de movimiento de stock (plantilla `alta_movimiento.html`):

1. Completar **cabecera**: motivo, fecha, depósitos origen/destino, detalle/referencia según el motivo.
2. Pasar a la pestaña **Artículos**: buscar por código/nombre (predictivo), escanear si aplica, cargar cantidades.
3. **Continuar** / **Confirmar** según el flujo; en móvil el botón principal queda arriba.

Detalle visual/UX para desarrollo: [ALTA_MOVIMIENTO_UX.md](ALTA_MOVIMIENTO_UX.md).  
Búsqueda de artículos: [../general/BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](../general/BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md).

---

## 4. Mensajes frecuentes

- **«No hay artículos con los filtros seleccionados»:** Ampliar marcas, quitar filtro de artículo, o activar incluir sin stock.
- **Talle/Color en «—»:** Sin dato CE; no implica saldo cero.
- **Inventario vacío con stock real:** Verificar que los depósitos tengan `tipo_mpr` y `suma_stock = 'Si'`.
- **Sin empresa activa:** Seleccionar empresa en login/sesión.

---

*Documento: Manual de usuario Stock/Inventario. Proyecto Synap. Actualizado 20/07/2026.*
