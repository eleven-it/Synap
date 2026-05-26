# Especificación: Informe «Ventas por artículo»

Slug canónico: **`ventas-por-articulo`**. Nombre en catálogo/UI: **Ventas por artículo**.

**URL:** `/reports/dashboard/ventas-por-articulo/`. Atajo: `/reports/ventas-por-articulo/` → URL canónica.

**Origen funcional:** clon conceptual de [`ventas-por-vendedor`](SPEC_INFORME_VENTAS_POR_VENDEDOR.md) (mismo núcleo de ventas de período, sin BO/objetivos/remitos/PEA).

**Diseño técnico:** [`DESIGN_INFORME_VENTAS_POR_ARTICULO.md`](DESIGN_INFORME_VENTAS_POR_ARTICULO.md).

---

## 1. Objetivo

Informe histórico de **unidades** y **facturación** del período, agrupado por **artículo → proveedor → cliente**.

---

## 2. Jerarquía y exclusiones

| Nivel | Visible en árbol | Notas |
|-------|------------------|-------|
| Artículo | Sí | Raíz; `id_art`, nombre |
| Proveedor | Sí | Desde `articulo.CodigoProveedor`; sin código → **«Sin proveedor»** |
| Cliente | Sí | Hoja con métricas |
| Rubro / subrubro | No | Solo **filtros** (como en VO) |
| Vendedor | No | Solo **filtro** incluir/excluir |
| Con compra / Sin compra | No | No aplica |

---

## 3. Métricas y datos

- **Columnas:** UNIDADES (`cantidades_vendidas`), FACTURACIÓN (`facturacion`).
- **Sin KPIs** de cabecera.
- **Sin** objetivos, remitos, PEA, backorder, período backorder en UI ni consultas.
- **Mismo rango** `fecha_inicio_facturacion` / `fecha_fin_facturacion` y filtros sucursal, depósito, PV, clientes, vendedores, lista de precio, rubro/subrubro que ventas por vendedor.
- **Ordenar por:** Facturación período (`facturacion_periodo`), Unidades período (`unidades_periodo`); forma asc/desc; reorden local sin nueva consulta si hay dataset en memoria.

---

## 4. Requisitos (RFC 2119)

### R1 — Catálogo y acceso

El sistema **DEBE** exponer el informe con slug `ventas-por-articulo` en catálogo y `query_runner`.

#### Escenario: Apertura del informe

- **DADO** un usuario con acceso a reportes
- **CUANDO** abre `/reports/dashboard/ventas-por-articulo/`
- **ENTONCES** ve título «Ventas por artículo», filtros de período facturación (sin fila backorder) y tabla con columnas Unidades y Facturación
- **Y** no ve sección KPI de objetivos

### R2 — Árbol

El sistema **DEBE** devolver jerarquía `articulo` → `proveedor` → `cliente` con rollups de unidades y facturación en cada nivel.

#### Escenario: Desglose por artículo

- **DADO** ventas de un artículo a dos clientes del mismo proveedor en el período
- **CUANDO** el usuario expande artículo y proveedor
- **ENTONCES** ve dos filas cliente con totales coherentes con líneas `stock` del período

#### Escenario: Sin proveedor

- **DADO** un artículo con `CodigoProveedor` nulo o 0
- **CUANDO** se lista bajo ese artículo
- **ENTONCES** aparece un nodo proveedor etiquetado «Sin proveedor»

### R3 — Filtros

El sistema **DEBE** aplicar filtros de vendedor, rubro y subrubro sin mostrarlos como niveles del árbol.

#### Escenario: Filtro rubro

- **DADO** filtro rubro activo
- **CUANDO** se ejecuta la consulta
- **ENTONCES** solo aparecen artículos con ventas en ese rubro en el período
- **Y** el árbol no muestra nodos rubro/subrubro

### R4 — Exportación

El sistema **DEBE** exportar Excel con dimensiones `id_art`, `nombre_articulo`, `codigo_proveedor`, `nombre_proveedor`, `codigo_cliente`, `nombre_cliente`, más unidades y facturación.

#### Escenario: Export plano

- **DADO** datos cargados en el informe
- **CUANDO** el usuario exporta
- **ENTONCES** el archivo no incluye columnas de objetivo, BO, remitos ni vendedor como dimensión obligatoria de jerarquía

### R5 — Recarga de datos

El sistema **DEBE** seguir la política manual/tiempo real de informes VO (cambio de filtros no dispara consulta hasta Actualizar, salvo tiempo real activo).

### R6 — Paridad de métricas

La suma de facturación y unidades por cliente bajo un artículo **DEBE** coincidir con la suma del mismo artículo en ventas por vendedor para mismo período y filtros equivalentes.

---

## 5. UI

- Patrones canónicos: `dashboard_detail.html`, includes de filtros BO, fuente de verdad reportes/MPR.
- `localStorage` de expansión con clave que incluya slug `ventas-por-articulo`.
- Carga diferida: expandir proveedor materializa clientes (no todos los clientes al abrir artículo).

---

## 6. Rollback

Eliminar `ReportDefinition`, ramas de slug, JS, migración y documentación; sin DDL MySQL de negocio.
