# Especificación: Informe «Ventas por marca y SuperArt»

Slug canónico: **`ventas-marca-superart`**. Nombre en catálogo/UI: **Ventas por marca y SuperArt**.

**URL:** `/reports/dashboard/ventas-marca-superart/`. Atajo: `/reports/ventas-marca-superart/` → URL canónica.

**Diseño técnico:** [`DESIGN_INFORME_VENTAS_MARCA_SUPERART.md`](DESIGN_INFORME_VENTAS_MARCA_SUPERART.md).

---

## 1. Objetivo

Informe histórico de **packs**, **docenas** y **facturación** del período, agrupado por **Marca → SuperArt → Artículo**.

---

## 2. Jerarquía y exclusiones

| Nivel | Visible en árbol | Notas |
|-------|------------------|-------|
| Marca | Sí | Raíz; `CodigoMarca` / nombre; vacío → **«Sin marca»** |
| SuperArt | Sí | `articulo.id_manual`; vacío → **«Sin SuperArt»** |
| Artículo | Sí | Hoja con métricas |
| Rubro / subrubro / marca | No (marca sí en árbol) | Rubro/subrubro solo **filtros**; marca también filtro incluir/excluir |
| Proveedor / Cliente / Vendedor | No | Solo filtros (vendedor incluir/excluir) |

---

## 3. Métricas y datos

- **Columnas UI:** Packs, Docenas, Facturación (siempre las tres; sin toggle).
- **Packs:** `SUM(Cantidad)` con signo FA/NC.
- **Docenas:** packs / factor U.M. (mismo mapa que Ventas marcas mensual: P1→12, P2→6, …).
- **Facturación:** `SUM(PrecioNetoxR)` con signo FA/NC.
- **Sin KPIs** de cabecera; sin BO/objetivos/remitos/PEA.
- **Filtros:** período facturación, PV/sucursal/depósito, clientes, vendedores, rubro/subrubro/marca (incluir/excluir) y **SuperArt** (`superarts_incluidos`).
- **Ordenar por:** Facturación período, Packs, Docenas; forma asc/desc; reorden local si hay dataset.

---

## 4. Exportación Excel

Plano (una fila por artículo):

| Marca | SuperArt | Articulo | Packs | Docenas | Facturacion |

Nombre archivo: `Ventas_marca_superart_{fecha_inicio}_{fecha_fin}.xlsx`.

---

## 5. Requisitos (RFC 2119)

### R1 — Catálogo y acceso

El sistema **DEBE** exponer el informe con slug `ventas-marca-superart` en catálogo y `query_runner`.

#### Escenario: Apertura del informe

- **DADO** un usuario con acceso a reportes
- **CUANDO** abre `/reports/dashboard/ventas-marca-superart/`
- **ENTONCES** ve título «Ventas por marca y SuperArt», filtros de período facturación (sin fila backorder) y tabla con Packs, Docenas y Facturación

### R2 — Árbol

El sistema **DEBE** devolver jerarquía `marca` → `superart` → `articulo` con rollups de packs, docenas y facturación en cada nivel.

### R3 — Excel plano

El sistema **DEBE** exportar filas planas con las seis columnas indicadas, sin outline Excel.
