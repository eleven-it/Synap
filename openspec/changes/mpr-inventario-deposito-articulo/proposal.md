# Proposal: Inventario por depósito y artículo (MPR)

## Intent

Operación MPR necesita la vista de inventario alineada a Excel `Inventarios.xlsx` / `REP_INVENTARIOS`: jerarquía Depósito→Marca→Artículo, medidas **Stock** (UM nativa) y **Docenas** (derivada), total cabecera = **SUM(docenas)**, 2da OFF por defecto y **stock a fecha**. Hoy el hub `demanda/stock` limita 500 filas sin marca/talle/totales; `_celda_stock_deposito` fuerza divisor 12 global; `/stock/inventario/` pivotea por etapa MPR, no por depósito físico Excel.

**Referencia:** `docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md`, `openspec/changes/mpr-inventario-deposito-articulo/exploration.md`

## Decisiones de producto (cerradas)

| ID | Decisión |
|----|----------|
| A | Stock UM como Excel: **packs** en Terminado/2da, **pares** en pipeline (Producción, Semi). Docenas con divisor BEST **12/6/4** vía `cantidad_promedio_bulto`. |
| B | 2da/Sobrante **OFF por defecto** (paridad hoja «Inventario Resumido TOTAL»). |
| C | **Stock a fecha** incluido en **este mismo change** (PR-2 encadenado bajo `auto-chain`). |

## Scope

### In Scope

- Nuevo reporte hub MPR `inventario_deposito` (grupo Demanda o Inventario dedicado) — **no** reemplazar `stock` ni `/stock/inventario/`
- Servicio dedicado grano `(id_deposito, id_articulo)` + Marca, Talle (CE), Stock UM-native, Docenas reglas A
- UI partial canon MPR; filtros depósito(s), marca(s), búsqueda artículo, `incluir_2da=0` default, `fecha_corte`
- Total cabecera **SUM(docenas)** por scope; export Excel (`format=xlsx`)
- **PR-1:** consulta + docenas + UI + filtros + tests divisores/totales
- **PR-2:** `stock_a_fecha` (tabla `stock`, criterio VB6) + Excel + UAT paridad muestra vs Excel
- Spike S1–S3 (UM pack/pares, paridad docenas, campo fecha) documentado pre-apply
- Docs `docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md`

### Out of Scope

- Extender in-place `reporte_mpr_stock` / partial `stock.html`
- Base `stock-existencias` (reports), motor costo valorizado (`mpr_costo_*`)
- Fix global `_celda_stock_deposito` en inventario tabla (change posterior opcional)
- Enrutamiento IA NL «inventario por depósito» (post-MVP si presiona presupuesto)

## Capabilities

### New Capabilities

- `mpr-reporte-inventario-deposito`: consulta depósito×artículo, medidas Stock+Docenas, jerarquía Depósito→Marca→Artículo, filtros, totales SUM(docenas), stock a fecha, export Excel

### Modified Capabilities

- `mpr-reportes-shell`: registrar reporte `inventario_deposito` en hub; soporte export xlsx para el reporte activo

## Approach

**Enfoque 1 (recomendado en explore):** servicio `mpr/services_inventario_deposito.py` (nombre orientativo); registrar slug en `mpr/reportes_hub.py`; partial hub (patrón `stock.html` + filtros inventario tabla).

1. **Docenas:** `tipo_mpr IN (Produccion, SemiElaborado)` → divisor 12, etiqueta pares; Terminado/2da → `divisor_docena_pack(cantidad_promedio_bulto)`; nueva función `medidas_inventario_excel()` sin `unidades_por_docena_fijo=12`.
2. **Stock hoy:** `stock_deposito.saldo`; **histórico (PR-2):** reconstrucción desde `stock` con `Fecha <= corte` (confirmar vs VB6 `Info_Stock.frm` en spike S3).
3. **Filtro 2da:** excluir `tipo_mpr = 2daSeleccion` por default; param `incluir_2da=1` opt-in.
4. **Entrega encadenada** (`delivery_strategy=auto-chain`, presupuesto ~800 líneas): PR-1 ~350–450 auth.; PR-2 ~300–500 auth.

Universo artículos (S4, 14/08/2026): fabricación MPR + Terminado comercial + **`tipo_art_fab=Tercero` incluido**.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `mpr/services_inventario_deposito.py` | New | Query grano, docenas, totales, stock a fecha |
| `mpr/reportes_hub.py` | Modified | Slug `inventario_deposito`, columnas CSV/Excel |
| `mpr/views.py` (`ReportesMPRView`) | Modified | Rama GET, params corte/2da, export xlsx |
| `mpr/reportes_presentacion.py` | Modified | Medidas por `tipo_mpr`; etiquetas Stock vs Docenas |
| `mpr/templates/mpr/reportes/partials/` | Added | Jerarquía, subtotales Marca, fila TOTAL |
| `mpr/services.py` | Modified | Helper `divisor_docena_inventario` reutilizable |
| `docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md` | Added | Operativo + paridad Excel |
| `mpr/tests/test_inventario_deposito_report.py` | Added | Divisores 12/6/4, totales, stock_a_fecha |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UM mixta pack/pares sin etiqueta por depósito | High | Columna Stock + subtítulo UM por `tipo_mpr` |
| Campo fecha equivocado (`Fecha` vs `FechaControl`) | High | Spike S3; tests con movimientos conocidos |
| Reutilizar `_celda_stock_deposito` sin refactor | High | Función nueva; tests tabla-driven 12/6/4 |
| TOTAL ≠ SUM(docenas) en UI | Med | Total solo en capa servicio; test pack×3 + pipeline |
| Performance reconstrucción histórica | Med | Índices; acotar depósitos MPR; paginación |
| Presupuesto review 800 líneas | Med | PR encadenados; stock_a_fecha en PR-2 |

## Rollback Plan

- **Código:** revertir commits de PR-1/PR-2; quitar slug del hub; sin cambios en `/stock/inventario/` ni `stock-existencias`.
- **Datos:** reporte solo lectura; rollback de código seguro sin migraciones DDL.
- **PR-2:** revertir servicio `stock_a_fecha`; fecha default «hoy» sigue usando `stock_deposito`.

## Dependencies

- Spike S1 (UM pack/pares en muestra real), S2 (paridad SUM(docenas) vs Excel), S3 (campo fecha VB6)
- `docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md`
- Canon UI `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md`

## Success Criteria

- [ ] Paridad docenas vs Excel muestra (delta acordado, p. ej. 0,01 docenas)
- [ ] 2da excluida por default; toggle `incluir_2da` funcional
- [ ] TOTAL cabecera = SUM(docenas), no SUM(stock)/12
- [ ] Stock a fecha reconstruye desde `stock` con criterio VB6 confirmado
- [ ] Export Excel con Stock UM + Docenas por depósito
- [ ] UI español, fechas dd/MM/yyyy, modales Synap (sin alert/confirm)
- [ ] `/stock/inventario/` y hub `demanda/stock` sin regresión
