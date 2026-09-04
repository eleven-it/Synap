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
| Ajustes sin mercadería | Sí (al pie) | Fila descriptiva: FA/NC de cabecera **sin renglón de stock vigente**. Hojas = cliente. Packs/docenas = 0. Solo si **no** hay filtro de catálogo (marca/rubro/subrubro/SuperArt). Alinea el total de facturación con **Ventas Netas**. |
| Rubro / subrubro / marca | No (marca sí en árbol) | Rubro/subrubro solo **filtros**; marca también filtro incluir/excluir |
| Proveedor / Cliente / Vendedor | No | Solo filtros (vendedor incluir/excluir) |

---

## 3. Métricas y datos

- **Columnas UI:** Packs, Docenas, Facturación (siempre las tres; sin toggle).
- **Packs:** `SUM(Cantidad)` con signo FA/NC.
- **Docenas:** packs / factor U.M. (mismo mapa que Ventas marcas mensual: P1→12, P2→6, …).
- **Facturación:** `SUM(signo × PrecioNetoxR × factor cabecera)` — mismo motor post-pie que Ventas marcas mensual (`SubtotalDesc / SubTotal1` por comprobante). Ver `comprobante_descuento_cabecera.py` y `ventas_marcas_mensual_rules.sql_signo_imp_post_pie_expr()`.
- **Ajustes de cabecera:** si no hay filtro de catálogo, se suma una marca sintética **«Ajustes sin mercadería»** con SuperArt **«FA/NC de cabecera»** y una hoja por cliente (`cuentacliente.SubtotalDesc` con signo FA/NC) para las cabeceras **sin** renglón SuperArt vigente (`stock.Anulado='No'`, TipoComp venta/devolución, `tipo_art ≠ Gasto`). Pares FA/NC del mismo cliente que netean a ~0 no aparecen. Con filtro de catálogo esa fila **no** se agrega (no alinearían con Ventas Netas).
- **Sin KPIs** de cabecera; sin BO/objetivos/remitos/PEA.
- **Filtros:** período facturación, PV/sucursal/depósito, clientes, vendedores, rubro/subrubro/marca (incluir/excluir) y **SuperArt** (`superarts_incluidos`).
- **Ordenar por:** Facturación período, Packs, Docenas; forma asc/desc; reorden local si hay dataset.
- **Exclusión fija:** `articulo.tipo_art <> 'Gasto'` ([FILTRO_TIPO_ART_GASTO.md](FILTRO_TIPO_ART_GASTO.md)).

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

### R4 — Facturación post-pie

El sistema **DEBE** calcular la facturación de renglón con el mismo motor post-pie que Ventas marcas mensual (`sql_signo_imp_post_pie_expr`).

### R5 — Ajustes sin mercadería

Sin filtro de catálogo, el sistema **DEBE** incluir al pie una marca descriptiva **«Ajustes sin mercadería»** (SuperArt **«FA/NC de cabecera»**, hojas = cliente) con el neto de cabecera de FA/NC que no tienen renglón SuperArt vigente, para que el total de facturación coincida con Ventas Netas. Con filtro de marca/rubro/subrubro/SuperArt **NO DEBE** incluir esa fila.

#### Escenario: Cabeceras sin renglón de stock

- **DADO** el mismo período y PV que Ventas Netas, sin filtros de catálogo
- **CUANDO** existen NCA (u otras FA/NC) de cabecera sin líneas de `stock` vigentes
- **ENTONCES** aparecen al pie bajo «Ajustes sin mercadería», packs/docenas en 0, y el total de facturación coincide con Ventas Netas

