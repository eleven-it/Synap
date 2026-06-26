# Especificación (delta): Informe «Ventas por vendedor»

Slug canónico: **`ventas-por-vendedor`**. Nombre en catálogo/UI: **Ventas por vendedor**.

**URL del dashboard:** `/reports/dashboard/ventas-por-vendedor/` (nombre `reports:dashboard_detail`). Atajo sin el segmento `dashboard/`: `/reports/ventas-por-vendedor/` redirige a la URL canónica. Tras desplegar, ejecutar migraciones para crear `ReportDefinition` (`0031_add_ventas_por_vendedor_report`).

Documento para el flujo SDD (propuesta → spec → diseño → implementación). Si se deshace el cambio, revertir: entrada de catálogo/`ReportDefinition`, rama en `query_runner`, runner o flag, plantilla, `dashboard.js`, JS de tabla, tests y este archivo.

---

## 1. Objetivo del producto

Informe **histórico de facturación por vendedor** con la **misma jerarquía y filtros** que el informe VO (`ventas-objetivos-vs-bo`): vendedor → estado compra (con/sin compra en el período) → cliente → rubro → subrubro → artículo.

En pantalla **solo dos columnas** bajo el concepto de ventas de período: **UNIDADES** y **FACTURACIÓN** (importe alineado a renglón como hoy VO en detalle).

No se muestran KPIs de cabecera (objetivo / falta / resumen numérico superior). La página puede omitir por completo la sección de KPIs del bloque VO o equivalente.

---

## 2. Carga de datos: qué **no** ejecutar

En la implementación backend (`run_ventas_objetivos_vs_bo` con `solo_ventas_periodo` cuando `report.slug == "ventas-por-vendedor"` en [`reports/services/ventas_objetivos_bo_runner.py`](../../reports/services/ventas_objetivos_bo_runner.py)), para ese slug **no** se ejecutan las fases que solo alimentan columnas o totales eliminados:

| Fase en VO hoy | Uso en VO | En «Ventas por vendedor» |
|----------------|-----------|---------------------------|
| Objetivos (`viajantes_objetivos_ventas`, solape período) | `objetivo`, `falta`, orden por meta/falta | **Omitir** |
| Remitos por cliente (`comp_ped` REM cabecera) | columna remitos, total consolidado VO | **Omitir** |
| Pedidos en armado por cliente (`comp_ped` PED estados preparación) | columna PEA, total | **Omitir** |
| Líneas REM por artículo (`stockp` + `comp_ped` REM) | `remitos_lineas` en árbol | **Omitir** |
| Líneas PED en armado por artículo (`stockp` + `comp_ped` PED) | `pedidos_armado_lineas` en árbol | **Omitir** |
| BO por cliente/artículo (`stockp`, `stock_deposito`, reservas, OC…) | columnas y rollups BO | **Omitir** |
| Cualquier merge `_merge_rem_ped_lineas_en_detalle_arbol` si no hay REM/PED | detalle jerárquico | **No llamar** si esas consultas no corren |

**Criterio:** menos consultas SQL, menos CPU y menos ancho de respuesta; los campos que el VO rellena para BO/remitos/PEA/objetivo pueden **no calcularse** (o ir fijados a cero solo si algún contrato JSON obliga a claves presentes — preferible **payload mínimo** documentado en diseño).

---

## 3. Carga de datos: qué **sí** mantener (joins necesarios)

Para **unidades** y **facturación** por cliente y por **rubro / subrubro / artículo**, el runner ya usa el núcleo siguiente (mismo rango de facturación y mismos filtros sucursal/PV/cliente/vendedor que VO):

1. **Facturación por cliente** (`cuentacliente` + `cliente` + `viajantes`): agrega `SubtotalDesc` FA/FB/… neto de NC en el rango `fecha_inicio_facturacion` / `fecha_fin_facturacion`. Sirve para totales por cliente y para consistencia con el árbol.

2. **Clientes con histórico de ventas** (consulta sin rango de fechas en facturas): en VO sirve para incluir clientes con movimiento fuera del período; **decidir en diseño** si el informe «solo período» la mantiene (paridad listado) o la simplifica para reducir coste.

3. **Unidades por cliente** (`stock` + `cuentacliente` + `cliente`): suma cantidades FA/NC en el mismo rango y filtros que el detalle por artículo.

4. **Detalle por artículo** (`sql_venta_por_art`): `stock` ⋈ `cuentacliente` ⋈ `cliente` ⋈ `articulo` ⋈ `rubro` ⋈ `subrubro`, agregando `PrecioNetoxR` (facturación línea) y cantidades (unidades línea), agrupado por cliente + rubro + subrubro + artículo. **Imprescindible** para el árbol bajo cliente.

No hace falta **join a `stockp` de REM/PED** para este informe si no mostramos esas métricas ni las fusionamos al árbol.

---

## 4. UI / UX

- **Período:** solo el bloque **Periodo Facturación** (`filters_period_bo_dual.html`): para `ventas-por-vendedor` **no** se renderiza la fila «Periodo Backorder». El resumen bajo cabecera usa la línea «Periodo facturación: …» (`syncBoDualSummaryPeriod` en `dashboard.js`). La jerarquía **Con compra / Sin compra** se mantiene en datos (igual que VO); no depende del rango de backorder.
- Misma barra de **filtros** (sucursales, depósitos, clientes/vendedores incluir/excluir, lista de precio, rubro/subrubro/marca incluir/excluir, ordenación).
- Tabla: solo cabeceras **UNIDADES** y **FACTURACIÓN** (sin grupo OBJETIVO, sin REM/PEA/TOTAL, sin BACKORDER).
- **Sin KPIs** (sin `#vo-kpis-section` o equivalente para este slug).
- `localStorage` de expansión de jerarquía con **clave distinta** a VO (incluir slug en la clave), para no mezclar estado entre informes.

---

## 5. Ordenación

En VO, `ordenar_por` incluye `objetivo_meta`, `objetivo_falta`, `total_ventas_periodo`. Para **Ventas por vendedor** (implementado):

- En plantilla (`dashboard_detail.html`): **Facturación período** (`facturacion_periodo`), **Unidades período** (`unidades_periodo`), **Total ventas período** (`total_ventas_periodo`). Si llega `objetivo_meta` / `objetivo_falta` por compatibilidad, el runner las remapea a orden por facturación del período.
- En backend: `_METRIC_ORDER_MAP` incluye `facturacion_periodo` → `facturacion` y `unidades_periodo` → `cantidades_vendidas`.

---

## 6. Exportación Excel

**Implementado:** `_resolve_export_headers` en `export_service.py` para el slug `ventas-por-vendedor` exporta solo dimensiones de jerarquía visibles + `cantidades_vendidas` + `facturacion` (sin objetivo, remitos, PEA, BO ni total consolidado VO).

---

## 7. Escenarios (Given / When / Then) — borrador

- **E1:** Dado el slug `ventas-por-vendedor`, cuando se abre el informe, entonces **no** se muestran KPIs de objetivo/falta y la tabla solo tiene dos columnas numéricas de período.
- **E2:** Dado un cliente con ventas solo en rubro X, cuando se expande el vendedor y el cliente, entonces se ve el desglose por rubro/subrubro/artículo con unidades e importe coherentes con `cuentacliente`/`stock` en el rango de facturación.
- **E3:** Dado el mismo período y filtros en VO y en Ventas por vendedor, cuando se compara facturación y unidades a nivel cliente (suma), entonces coinciden con la parte de ventas de período del VO (sin remitos/PEA/BO).
- **E4:** Dado tiempo real desactivado, cuando el usuario cambia un filtro, entonces los datos **no** se recargan hasta «Actualizar» (misma política que VO/BO dual si aplica este slug a `isInformeQuerySoloManualORealtime`).

---

## 8. Rollback

Eliminar el informe del catálogo y las ramas de código; no requiere migración de datos de negocio si solo se añadió `ReportDefinition` y código. Conservar este archivo en `docs/reports/` como registro histórico o marcar sección «Archivado» si se revierte.

---

## 9. Relación con otros trabajos

Independiente de: paridad Stock vs VO, comprobantes en ruta, columna PED en total consolidado. Si el runner se implementa como **función dedicada** `run_ventas_por_vendedor` con SQL recortado, el VO actual no debería cambiar de comportamiento (solo posible extracción de helpers compartidos para facturación + detalle artículo).
