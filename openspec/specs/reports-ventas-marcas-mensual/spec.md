# Especificación — Informe Ventas marcas mensual (facturación post-pie)

**Capability:** `reports-ventas-marcas-mensual`  
**Slug:** `ventas-marcas-mensual`

Incorporado desde el cambio archivado `vmm-dto-pie-facturacion` (10/08/2026). Fuente de verdad OpenSpec para el informe pivot mensual **Ventas marcas mensual**.

## Purpose

El informe pivot mensual **Ventas marcas mensual** agrega facturación neta por vendedor, cliente y mes desde renglones `stock` con signo FA/NC. AdministraNET aplica descuento al pie en cabecera (`cuentacliente.SubTotal1`, `SubtotalDesc`); las líneas conservan `PrecioNetoxR` pre-pie. El sistema **MUST** alinear importes de facturación, KPIs, regalías, proyección monetaria y export con la base **post-pie** proporcional por comprobante, reutilizando el criterio validado en DABRA.

---

## Requirements

### REQ-VMM-PIE-01 — Importe de facturación post-pie

El importe de cada renglón elegible **MUST** calcularse como `signo_comprobante × PrecioNetoxR × factor_cabecera`, donde `signo_comprobante` es positivo para FA/FB/FC/FE/FM y negativo para NC*, y `factor_cabecera = SubtotalDesc / SubTotal1` del mismo `CodigoMovimiento` (`cuentacliente`). La agregación de facturación (KPIs, matriz, modo comparar, export Detalle) **MUST** usar `SUM` de esa expresión sobre el universo filtrado.

#### Scenario: FA con dto al pie 20 %

- GIVEN una FA con `SubTotal1=1000`, `SubtotalDesc=800` y renglones filtrados cuya Σ `PrecioNetoxR` = 1000
- WHEN se ejecuta el informe con los mismos filtros
- THEN la facturación del informe es 800 (factor 0,8 sobre cada línea)

#### Scenario: Signo NC preservado

- GIVEN una NC con `SubTotal1=500`, `SubtotalDesc=400` y un renglón con `PrecioNetoxR=500`
- WHEN se agrega al informe
- THEN el importe del renglón es −400 (signo NC × factor 0,8)

---

### REQ-VMM-PIE-02 — Factor cabecera y casos límite

El factor **MUST** resolverse por comprobante: si `SubTotal1` es 0 o nulo, el factor **MUST** ser 1; si `SubtotalDesc` es nulo, **MUST** tratarse como igual a `SubTotal1` (factor 1). Valores numéricos **MUST** normalizarse con `core.utils.administranet_types` (`to_decimal_or_none`) en el helper Python.

#### Scenario: SubTotal1 cero

- GIVEN un comprobante con `SubTotal1=0` y `SubtotalDesc=0`
- WHEN se calcula el importe de sus renglones
- THEN el factor es 1 y el importe es `signo × PrecioNetoxR`

#### Scenario: Sin dto al pie

- GIVEN un comprobante con `SubtotalDesc` ≈ `SubTotal1` (sin descuento material al pie)
- WHEN se ejecuta el informe
- THEN la facturación coincide con el comportamiento previo (`signo × PrecioNetoxR` sin ajuste)

---

### REQ-VMM-PIE-03 — Coherencia matriz, comparar y export

La misma expresión post-pie **MUST** alimentar: KPI de cabecera `facturacion`, celdas `f` de la matriz, totales y modo comparar (marcas A/B y delta), columna Monto de export Matriz y columna monto de export Detalle. El factor **MUST** derivarse de la cabecera del `CodigoMovimiento` completo (todas las líneas del FA), aunque el filtro de marca restrinja renglones visibles.

#### Scenario: Paridad pantalla vs export Detalle

- GIVEN una consulta con filtros fijos y al menos un FA con dto al pie
- WHEN se exporta Excel Detalle con los mismos filtros
- THEN la suma de montos Detalle es coherente con `data[]` y con la facturación KPI

#### Scenario: Modo comparar

- GIVEN modo comparar entre dos marcas en el mismo período
- WHEN se leen KPIs y celdas `a`/`b` por mes
- THEN ambas marcas usan importe post-pie y el delta % refleja la misma base

---

### REQ-VMM-PIE-04 — Regalías, regalías/TC y proyección monetaria

**Regalías** **MUST** calcularse como `facturacion_post_pie × tasa_regalia` (sin lógica adicional). **Regalías / TC** **MUST** ser `regalias / tc_efectivo` (0 si TC ≈ 0). **Precio medio** **MUST** usar facturación post-pie sobre unidades. Con proyección activa, **`pf`** **MUST** aplicarse sobre facturación ya post-pie (`round(f × coef, 2)`); **`pu`** **MUST NOT** aplicar el factor de pie (solo unidades).

#### Scenario: Regalías sobre base post-pie

- GIVEN `tasa_regalia_pct=13`, facturación post-pie 800 y TC efectivo 14,5817
- WHEN se consultan KPIs
- THEN regalías = 104 y regalías/TC ≈ 104 / 14,5817

#### Scenario: Proyección $ post-pie

- GIVEN proyección ON, `coef_proyeccion=1,07` y facturación post-pie 800 en un mes
- WHEN se muestra la matriz
- THEN `pf` = 856,00 y las unidades proy no cambian por el factor de pie

---

### REQ-VMM-PIE-05 — Unidades sin cambio

Packs, docenas y expresiones de cantidad (`sql_signo_qty_expr`, factor docenas U.M.) **MUST NOT** multiplicarse por `factor_cabecera`. Solo los importes monetarios de facturación **MUST** aplicar el factor.

#### Scenario: Unidades invariantes con dto pie

- GIVEN un FA con dto al pie 20 % y renglones con cantidad total 100 packs
- WHEN se ejecuta el informe en modo packs
- THEN unidades KPI y matriz `u` = 100 (sin × 0,8)

---

### REQ-VMM-PIE-06 — Helper compartido y paridad DABRA

La lógica de `factor_descuento_cabecera(subtotal1, subtotal_desc)` **MUST** residir en un módulo compartido (`reports/services/comprobante_descuento_cabecera.py`) y **MUST** ser importada por VMM y DABRA. DABRA **MUST NOT** cambiar comportamiento observable tras el refactor (re-export o import equivalente). Tests **MUST** ejecutarse en contenedor: `docker exec Synap_app python manage.py test reports.tests.test_ventas_marcas_mensual reports.tests.test_dabra_consolidado_remitos`.

#### Scenario: Regresión DABRA

- GIVEN la suite `test_dabra_consolidado_remitos` existente
- WHEN se mueve el helper al módulo compartido
- THEN todos los tests DABRA permanecen verdes sin cambio de salida

#### Scenario: Tests factor VMM

- GIVEN casos unitarios: factor 1 (sin pie), 0,8 (20 % pie), `SubTotal1=0`, `SubtotalDesc` nulo
- WHEN se ejecutan tests VMM del factor y un fixture FA integrado
- THEN los resultados coinciden con las reglas REQ-VMM-PIE-01 y REQ-VMM-PIE-02
