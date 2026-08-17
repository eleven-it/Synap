# Inventario por depósito y artículo (MPR)

**Change motor:** `mpr-inventario-deposito-articulo`  
**Change catálogo:** `reports-inventario-deposito-catalogo`  
**Ruta canónica (UI):** `/reports/dashboard/inventario-deposito-articulo/` — ver [`docs/reports/INVENTARIO_DEPOSITO_ARTICULO.md`](../reports/INVENTARIO_DEPOSITO_ARTICULO.md)  
**Hub legacy:** `/mpr/reportes/?grupo=demanda&reporte=inventario_deposito` → **302** al dashboard del catálogo.

Reporte alineado a Excel `Inventarios.xlsx` / `REP_INVENTARIOS`: jerarquía Depósito→Marca→Artículo, medidas **Stock** (UM nativa) y **Docenas**, total cabecera = **SUM(docenas)**.

## Reglas de medidas (decisión A)

| `tipo_mpr` depósito | UM Stock | Divisor docenas |
|---------------------|----------|-----------------|
| Produccion, SemiElaborado | pares | 12 |
| Terminado, 2daSeleccion | packs | `cantidad_promedio_bulto` → 12, 6 o 4 |

Implementación: `mpr/inventario_docenas.py` (`medidas_inventario_excel`). **No** reutiliza `_celda_stock_deposito` (divisor 12 global).

## Filtros

- `fecha_corte` (default hoy, UI dd/MM/yyyy).
- `depositos` (multi), `marcas_incluidos`, `q` (búsqueda), `incluir_2da=0|1` (default **OFF**).
- Desde/Hasta del shell **no** gobiernan este reporte (`fecha_corte` sí).

## Stock a fecha (decisión C — PR-2)

| Corte | Fuente | Servicio |
|-------|--------|----------|
| Hoy (o futuro) | `stock_deposito.saldo` | `consultar_inventario_deposito` |
| Pasado | `SUM(Entrada)-SUM(Salida)` en `stock` | `stock/services/stock_a_fecha.py` → `saldos_stock_a_fecha` |

**Campo temporal:** `stock.Fecha` con `DATE(Fecha) <= fecha_corte` y `Anulado <> 'Si'`.

**No confundir con inventario físico:** el módulo `/stock/inventario/fisico/` usa **`stock.FechaControl`** (timestamp de inserción post-snapshot). Ver `docs/stock/INVENTARIO_FISICO.md`.

### Evidencia diseño S3 (`stock.Fecha`)

| Fuente | Criterio fecha |
|--------|----------------|
| VB6 `Info_Stock.frm` — «Lista existencias valorizado» variante a fecha | Rango sobre **`stock.Fecha`** ([COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md](../reports/COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md) §3–§5) |
| Motor costo valorizado Synap §5.2 | Histórico: movimientos `stock` con **`Fecha <= corte`** ([DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md](best/DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md) §5.2) |
| Inventario físico Synap | **`FechaControl >= snapshot`** (contrato distinto) |

**Decisión apply PR-2:** se adopta **`stock.Fecha`** para este reporte MPR. No se encontró evidencia en repo que obligue `FechaControl` para existencias «a fecha» operativas MPR/Info_Stock.

## Export

- **CSV:** `?format=csv` (columnas hub: Depósito, Marca, Código, Descripción, Talle, Stock, UM, Docenas).
- **Excel:** `?format=xlsx` — columnas **Depósito, Marca, Artículo, Talle, Stock, Docenas** + fila **TOTAL** = SUM(docenas). Botón visible solo en reportes con flag `REPORTES_EXPORT_XLSX` en `mpr/reportes_hub.py`.

Implementación: `mpr/export.py` (`exportar_inventario_deposito_xlsx`), patrón `openpyxl` como `stock/services/inventario_fisico_export.py`.

## Spikes pre-apply

### §S1 — UM pack/pares (muestra real)

**Estado:** documentado sin validación live MySQL Best Sox en este entorno.

**Hallazgos desde documentación BEST (`docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md`, `BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md` §2):**

- En `REP_INVENTARIOS`, columna **Stock** en pipeline (Producción 4000, Semi 4002) se interpreta como **pares**; docenas = pares ÷ 12.
- En **Terminado** (4003) y **2da/Sobrante** (4004), Stock es **packs**; docenas usan divisor 12/6/4 según `cantidad_promedio_bulto` (equivalente PACK 1→12, 2→6, 3→4 en BEST).
- Synap aplica la misma regla vía `divisor_docena_inventario()` + `medidas_inventario_excel()`.

**Limitación:** sin acceso a `administranet1` / Best Sox en runtime de apply, no se contrastaron 5–10 SKUs reales contra movimientos armado/OPP. Validación operativa pendiente en UAT con base cliente.

### §S2 — Paridad SUM(docenas) vs `Inventarios.xlsx`

**Estado:** reglas implementadas; paridad numérica no ejecutada contra Excel en apply.

**Metodología acordada:**

1. Exportar/consultar mismo scope (depósitos MPR, 2da OFF) con `consultar_inventario_deposito`.
2. Comparar `total_docenas` por depósito vs hoja «Inventario Resumido TOTAL» del Excel.
3. Tolerancia objetivo: **≤ 0,01 docenas** por depósito.

**Limitación:** archivo `Inventarios.xlsx` no disponible en contenedor de tests; delta real se validará en tarea 4.4 (UAT).

### §S3 — Campo fecha stock a fecha

**Estado:** **cerrado** — ver sección «Stock a fecha» y evidencia arriba. Implementado en PR-2.

## UAT paridad Excel (tarea 4.4)

**Estado:** pendiente validación live Synap vs AdministraNET / `Inventarios.xlsx`.

**Metodología:**

1. Misma empresa, `fecha_corte` = hoy, depósitos MPR (4000/4002/4003), `incluir_2da=0`.
2. Export Synap `?format=xlsx` y comparar SUM(docenas) por depósito vs hoja «Inventario Resumido TOTAL».
3. Registrar delta por depósito; aceptar si ≤ 0,01 docenas.

**Referencias numéricas del análisis explore (no verificadas en runtime apply):**

| Depósito (referencia BEST) | TOTAL docenas Excel (explore) |
|----------------------------|-------------------------------|
| Scope agregado muestra | **53861,67** (hero resumido; pendiente desglose por depósito en UAT live) |

No se reportan deltas Synap↔Excel en este commit: UAT requiere base cliente y archivo `Inventarios.xlsx` fuera del contenedor de tests.

## Universo artículos (S4)

`tipo_art_fab=Tercero` **incluido** (decisión 14/08/2026). Sin filtro excluyente por `tipo_art_fab`.

## Archivos

| Archivo | Rol |
|---------|-----|
| `mpr/inventario_docenas.py` | Divisores y medidas Stock+Docenas |
| `mpr/services_inventario_deposito.py` | Query hoy/histórico, filtros, agrupación, totales |
| `stock/services/stock_a_fecha.py` | Reconstrucción histórica `saldos_stock_a_fecha` |
| `mpr/export.py` | CSV + Excel inventario |
| `mpr/reportes_hub.py` | Slug, partial, CSV, flag Excel |
| `mpr/views.py` | Rama `ReportesMPRView`, export xlsx |
| `mpr/reportes_presentacion.py` | `preparar_inventario_deposito_presentacion` |

## Tests

```bash
docker exec Synap_app python manage.py test mpr.tests.test_inventario_deposito_report stock.tests.test_stock_a_fecha --keepdb
```

## Referencias

- `docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md`
- `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md` §2.2, §4.3
- `docs/reports/COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md`
- `docs/mpr/best/DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md` §5.2
- `openspec/changes/mpr-inventario-deposito-articulo/`
