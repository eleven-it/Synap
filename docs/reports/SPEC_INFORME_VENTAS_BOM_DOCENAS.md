# Especificación: Informe «Ventas BOM en docenas»

Slug canónico: **`ventas-bom-docenas`**. Nombre en catálogo/UI: **Ventas BOM en docenas**.

**URL:** `/reports/dashboard/ventas-bom-docenas/`. Atajo: `/reports/ventas-bom-docenas/` → URL canónica.

**Diseño técnico:** [`DESIGN_INFORME_VENTAS_BOM_DOCENAS.md`](DESIGN_INFORME_VENTAS_BOM_DOCENAS.md).

---

## 1. Objetivo

Obtener cuántos **artículos BOM (componentes)** tuvieron salida atribuible a **venta facturada**, explosionando el pack terminado según la receta (`en_abm_formula`). Unidad principal: **docenas** (pares ÷ 12). Columna de control: **pares**.

No hay informe VB6/Crystal equivalente; es un informe **nuevo**.

---

## 2. Regla de negocio

| Concepto | Definición |
|----------|------------|
| Evento comercial | FA/NC del **pack** (línea visible en `stock`) |
| Explosión | `pares_componente = signo × Cantidad_pack × cantidad_articulo` |
| Docenas | `pares_componente / 12` |
| Grano | Una fila por **artículo BOM** (componente) |
| Dinero | Sin facturación `$` en v1 |

Circuito MPR (`descuenta_en = Mstock`): los componentes salen en armado, no en la factura. El informe **reconstruye** la equivalencia a partir de packs facturados; no lee líneas TPV con `visualiza_ensamble = 'Si'`.

---

## 3. Universo de datos

- `stock` ⋈ `cuentacliente` (FA/FB/FC/FE/FM + NC*), `Anulado = 'No'`.
- `st.TipoComp` ∈ `Venta`, `Venta TPV`, `Devol - Cliente`, `ND Anul NC`.
- `COALESCE(st.visualiza_ensamble, 'No') = 'No'`.
- Pack con receta: `articulo.id_en_abm` no nulo y filas vigentes en `en_abm_formula` (`anulado` distinto de `'Si'`).
- Packs sin BOM: se omiten; el resultado puede incluir una nota.

---

## 4. Filtros

- Período: `fecha_inicio` / `fecha_fin` (atajos día/mes/año).
- Sucursales, punto de venta.
- Clientes a excluir (opcional).
- Marcas / rubros / subrubros del **pack vendido** (si se envían en payload).

---

## 5. Requisitos (RFC 2119)

### R1 — Catálogo y acceso

El sistema **DEBE** exponer el informe con slug `ventas-bom-docenas` en catálogo y `query_runner`, categoría operacional.

#### Escenario: Apertura

- **DADO** un usuario con `reports.view_operational`
- **CUANDO** abre `/reports/dashboard/ventas-bom-docenas/`
- **ENTONCES** ve título «Ventas BOM en docenas», filtros de período y tabla con código, artículo BOM, marca, pares y docenas

### R2 — Explosión BOM

El sistema **DEBE** agregar por componente: `SUM(signo × Cantidad_pack × cantidad_articulo)` y docenas = pares / 12.

#### Escenario: Pack con dos componentes

- **DADO** 10 packs FA de un artículo con BOM (comp A ×2, comp B ×1)
- **CUANDO** se ejecuta el informe
- **ENTONCES** A muestra 20 pares / 1,67 docenas y B 10 pares / 0,83 docenas (redondeo a 2 decimales en docenas)

#### Escenario: Nota de crédito

- **DADO** una NC que anula packs vendidos
- **CUANDO** se ejecuta el informe
- **ENTONCES** las cantidades BOM restan (signo negativo)

### R3 — Exclusión de líneas de ensamble

El sistema **DEBE** excluir `visualiza_ensamble = 'Si'` para no duplicar explosión TPV.

### R4 — Exportación Excel

El sistema **DEBE** exportar `.xlsx` con columnas código BOM, nombre, marca, pares, docenas; fechas `dd/MM/yyyy` en notas/filtros; nombre `Ventas_BOM_docenas_{ddMMyyyy}_{ddMMyyyy}.xlsx`.

### R5 — Recarga

Cambio de filtros **NO** dispara consulta hasta **Actualizar** (salvo tiempo real activo).

---

## 6. UI

- Patrones canónicos: `dashboard_detail.html`, includes de período y sucursal/PV.
- KPIs: total docenas, cantidad de artículos BOM.
- Tabla plana ordenable; totales al pie.
- Modales/toast Synap; sin `alert`/`confirm`.

---

## 7. Fuera de alcance v1

- Desglose pack origen / cliente / vendedor.
- Facturación `$`.
- Toggle packs/docenas comerciales (P1–P6).
- Kardex MPR / OPT/OPA.
- Armado surtido sin BOM.

---

## 8. Rollback

Eliminar `ReportDefinition`/`ReportWidget` del slug, ramas de dispatch/export/UI, seed, migración y documentación; sin DDL MySQL de negocio.
