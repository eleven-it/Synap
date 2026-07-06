# Propuesta — Inventario tabla MPR en Stock (`/stock/inventario/`)

**Change:** `stock-inventario-tabla-mpr`  
**Fecha:** 06/07/2026  
**Modo:** Product Mode (analista MPR / inventario)  
**Exploración:** [exploration.md](./exploration.md)  
**Diseño UX:** [design.md](./design.md)

---

## 1. Intención

Entregar en el módulo **Stock** una consulta de **inventario operativo MPR** en formato tabla: una fila por artículo, columnas por **etapa física del pipeline** (depósitos con `tipo_mpr` que suman stock) y columna **Consolidado**, reemplazando el submenú «Inventario» que hoy apunta a un stub en `/stock/consulta-ficha/`.

El analista MUST poder, en una sola pantalla:

- Ver saldos por **Producción**, **Semi elaborado**, **2da Selección** y **Terminado**.
- Leer el **total consolidado** (suma de etapas que suman stock, sin Scrap).
- **Filtrar por marca** y **buscar artículos** de forma predictiva.
- Identificar el artículo por **`id_manual - CodArtProv`**.

---

## 2. Problema

| Hoy | Dolor |
|-----|-------|
| `/stock/consulta-ficha/` es stub | Menú «Inventario» no entrega valor |
| Reporte stock en `/mpr/reportes/` | Vive en MPR; analistas de stock no lo encuentran en su menú |
| Pivote MPR por **nombre de depósito** | No coincide con el modelo mental por **etapa** |
| Sin filtro marca en stock operativo | Export manual desde otros informes |

---

## 3. Alcance

### Incluido (P0 — MVP)

| # | Entrega | Descripción |
|---|---------|-------------|
| S1 | **Ruta `/stock/inventario/`** | Vista Django, permiso `stock.consultas` |
| S2 | **Servicio pivote por `tipo_mpr`** | SQL sobre `stock_deposito` + `deposito` (`suma_stock='Si'`) + `articulo` |
| S3 | **Columnas fijas** | Artículo · Producción · Semi elaborado · 2da Selección · Terminado · Consolidado |
| S4 | **Filtro multi-marca (tags)** | Mismo componente que `filters_stock_existencias.html` + `tags_filter.mjs` |
| S5 | **Buscador predictivo artículo** | API sobre universo completo (sin límite de página de tabla) |
| S6 | **Botón Ver todos** | `incluir_ceros=1` incluye artículos con consolidado ≤ 0 |
| S7 | **Toggle Unidades / Docenas** | Reutilizar `mpr/reportes_presentacion` |
| S8 | **Menú Stock** | Subítem «Inventario» → `stock:inventario` |
| S9 | **Eliminar consulta-ficha** | Quitar ruta, vista, plantilla, tests y URL name legacy |
| S10 | **UI canon** | Tabla sticky, scroll horizontal, dark mode |
| S11 | **Tests** | Servicio pivote, URL, permiso, filtros, eliminación legacy |
| S12 | **Docs** | `docs/stock/INVENTARIO_TABLA_MPR.md` |

### Incluido (P1 — opcional)

| # | Entrega |
|---|---------|
| S13 | Export **CSV** |

### Fuera de alcance v1

- Scrap / Planchado como columnas (no suman al consolidado operativo).
- Edición de stock o ajustes desde esta pantalla.
- Informe en dashboard gerencial (`/reports/dashboard/`).
- Inventario físico / conteo (`inventario` VB6).

---

## 4. Capabilities (contrato para specs)

### New Capabilities

| Capability | Spec path | Descripción |
|------------|-----------|-------------|
| `stock-inventario-tabla` | `specs/stock-inventario-tabla/spec.md` | Consulta pivote MPR en Stock |
| `stock-inventario-filtros` | `specs/stock-inventario-filtros/spec.md` | Marca + búsqueda predictiva |

### Modified Capabilities

| Capability | Cambio |
|------------|--------|
| Menú shell Stock | URL subítem Inventario |

---

## 5. Enfoque técnico (resumen)

- **Vista:** `inventario_view` en `stock/views.py` — GET con `marcas_incluidos`, `q`, `id_articulo`, `incluir_ceros`, `presentacion`, `page`.
- **Servicio:** `stock/services/inventario_tabla.py` — agregación por `tipo_mpr`, etiquetas UI, consolidado vía `TIPOS_QUE_SUMAN_STOCK`.
- **API búsqueda:** `GET /stock/api/inventario/articulos/?q=` — permiso `stock.consultas`.
- **Plantilla:** `stock/templates/stock/inventario.html` — partials `_filtros_inventario.html`, `_tabla_inventario.html`.
- **Tipos AdministraNET:** `to_int_or_none`, `str_or_default`, `str_codigo_manual_articulo`.

---

## 6. Criterios de éxito

1. Menú **Stock → Inventario** abre `/stock/inventario/` con tabla poblada.
2. Columnas de etapa coinciden con saldos en depósitos `tipo_mpr` configurados y `suma_stock='Si'`.
3. **Consolidado** = suma Producción + Semi elaborado + 2da Selección + Terminado.
4. Filtro marca reduce filas; buscador localiza por `id_manual`, `CodArtProv`, nombre.
5. UI alineada a canon reportes/MPR (revisión visual contra `FUENTE_VERDAD_UI_REPORTES_MPR.md`).

---

## 7. Dependencias

- Configuración MPR de depósitos (`deposito.tipo_mpr`) en la empresa.
- Permiso existente `stock.consultas`.
- Sin migración de esquema MySQL en v1.

---

## 8. Próximos pasos SDD

1. Resolver preguntas de producto (exploration §8).
2. `/sdd-spec stock-inventario-tabla-mpr`
3. `/sdd-design stock-inventario-tabla-mpr` (detalle técnico si difiere de design.md UX)
4. `/sdd-tasks` → `/sdd-apply` → `/sdd-verify`
