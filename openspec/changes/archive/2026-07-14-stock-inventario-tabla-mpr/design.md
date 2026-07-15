# Design UX — Inventario tabla MPR (Stock)

**Change:** `stock-inventario-tabla-mpr`  
**Propuesta:** [proposal.md](./proposal.md)  
**Audiencia:** Analista MPR · responsable de inventario · supervisor de planta

---

## 1. Objetivo de experiencia

La pantalla responde en **menos de 3 segundos** a: *«¿Cuánto tengo de este pack en cada etapa y en total?»*

No es un informe gerencial ni un ABM: es una **rejilla de control operativo** con lectura horizontal del pipeline.

---

## 2. Principios de diseño

| Principio | Implementación |
|-----------|----------------|
| **Pipeline legible** | Columnas siempre en orden: Producción → Semi elaborado → 2da Selección → Terminado → Consolidado |
| **Código es la ancla** | Primera columna sticky: `id_manual - CodArtProv` en `font-semibold tabular-nums` |
| **Total sin ambigüedad** | Consolidado con fondo `bg-slate-50 dark:bg-slate-800/60` y tipografía más marcada |
| **Ceros honestos** | Celdas en `0` en gris suave; vacío solo si artículo no aplica — no ocultar filas sin aviso |
| **Filtros compactos** | Una barra `h-9`, alineada al patrón `mpr/reportes/_filtros.html` |
| **Sin ruido** | Sin KPI strip en v1; la tabla es el protagonista |

---

## 3. Layout

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Breadcrumb: Inicio / Stock / Inventario                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ H1 Inventario por etapa                                                 │
│ Subtítulo: Saldos en depósitos que suman stock (configuración MPR)      │
├─────────────────────────────────────────────────────────────────────────┤
│ [ Marcas: chips tags… ]  [ 🔍 Buscar artículo… ]  [Ver todos] [Unid|Doc] │
├─────────────────────────────────────────────────────────────────────────┤
│ ◀ scroll horizontal ▶                                                   │
│ ┌──────────────┬──────────┬─────────────┬─────────────┬──────────┬──────│
│ │ Artículo     │Producción│Semi elabor. │2da Selección│Terminado │Consol│
│ ├──────────────┼──────────┼─────────────┼─────────────┼──────────┼──────│
│ │ 12A - PRV-01 │    48    │     12      │      0      │   120    │ 180  │
│ │ Pack básico  │          │             │             │          │      │
│ └──────────────┴──────────┴─────────────┴─────────────┴──────────┴──────│
├─────────────────────────────────────────────────────────────────────────┤
│ 142 artículos · Marca: Todas                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Columna Artículo

| Elemento | Estilo |
|----------|--------|
| Línea 1 | `{id_manual} - {CodArtProv}` — si `CodArtProv` vacío: solo `id_manual` (sin guión colgante) |
| Línea 2 (opcional P1) | `NombreArticulo` truncado `text-xs text-gray-500` |

### Celdas numéricas

- Alineación `text-right tabular-nums`.
- Modo **unidades** (default propuesto): entero.
- Modo **docenas** (P1): dos líneas como `mpr/reportes/partials/stock.html` (docenas arriba, unidades abajo).

### Consolidado

- Última columna sticky opcional en desktop ancho; mínimo: fondo diferenciado.
- Valor = suma de las cuatro etapas (no incluye Scrap).

---

## 4. Componentes reutilizados

| Componente | Origen | Uso |
|------------|--------|-----|
| Barra filtros flex | `mpr/reportes/_filtros.html` | Estructura y alturas |
| Buscador combobox | `mpr/reportes/_busqueda_tabla_articulos.html` | Adaptar a submit server-side |
| Tabla sticky + scroll | `mpr/reportes/partials/stock.html` | Estructura thead/tbody |
| Base layout | `base_app.html` | Shell Synap |
| Toast mensajes | `synap-messages.js` | Errores sesión / sin empresa |

**MUST NOT** tomar referencia visual de `ventas/objetivos-venta` ni `ventas/presupuestos`.

---

## 5. Filtros — comportamiento

### Marca (multi-select tags)

- Mismo componente que reportes: `filters_stock_existencias.html` + `tags_filter.mjs`.
- Chips removibles; vacío = todas las marcas.
- Query: `marcas_incluidos` (repetido o lista).
- Al aplicar: submit GET preservando otros filtros.

### Buscador predictivo

**Server-side sobre universo completo**

1. Usuario escribe ≥2 caracteres.
2. Debounce 300 ms → API con `q`, `marcas_incluidos`, `incluir_ceros` — **sin** `page`.
3. Dropdown: código compuesto + nombre.
4. Al elegir: `?id_articulo={IDArt}` (encuentra fila aunque esté fuera de la página visible).
5. Tabla paginada 150 filas; filtro `q` se aplica **antes** de paginar.

Criterios búsqueda (alineado existencias): `id_manual`, `CodArtProv`, `NombreArticulo`, códigos de barras.

### Estados vacíos

| Estado | Mensaje |
|--------|---------|
| Sin resultados | «No hay artículos con los filtros seleccionados.» |
| Sin config MPR | Banner ámbar: «Configure depósitos MPR para ver columnas por etapa.» |
| Cargando | Skeleton 5 filas (opcional P1) |

---

## 6. Paleta semántica (sutil)

No colorear todas las celdas; solo señales:

| Señal | Uso | Clase |
|-------|-----|-------|
| Consolidado alto | Opcional P2 heatmap | — |
| Sin config etapa | Header columna con tooltip | `text-amber-600` + ícono `info` |
| Fila hover | Lectura fila | `hover:bg-gray-50/80` |

Acento de foco en inputs: `purple-500` (canon MPR/reportes).

---

## 7. Accesibilidad

- `<table>` con `<th scope="col">`.
- Buscador: `role="combobox"`, `aria-expanded`, navegación teclado ↑↓ Enter (patrón MPR).
- Scroll horizontal: hint «Deslizá horizontalmente…» bajo filtros en móvil.

---

## 8. Responsive

| Breakpoint | Comportamiento |
|------------|----------------|
| `< md` | Filtros en columna; tabla scroll horizontal obligatorio |
| `≥ lg` | Filtros en fila; columna artículo sticky `min-w-[14rem]` |

---

## 9. Migración menú y eliminación legacy

| Antes | Después |
|-------|---------|
| `stock:consulta_ficha_stock` | `stock:inventario` |
| `/stock/consulta-ficha/` | **Eliminado** (404) |
| `consulta_ficha_stock.html` | **Eliminado** |
| Label «Inventario» | Sin cambio |

## 10. Ver todos / incluir ceros

- Default: solo consolidado > 0.
- Botón **Ver todos los artículos** → `incluir_ceros=1`; incluye filas con saldo ≤ 0 en todas las etapas.
- Estilo toggle o botón con estado activo visible.

## 11. Unidades / Docenas

- Toggle en barra de filtros; param `presentacion=unidades|docenas`.
- Docenas: misma presentación que `mpr/reportes/partials/stock.html`.
