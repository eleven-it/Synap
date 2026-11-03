# Validación informes BestSox Marca — Ago–Oct 2026

**Período:** 2026-08-01 … 2026-10-31 (consignación: corte facturas 2026-11-03).

**Referencias:** `Produccion_Ago-Oct2026_b6c9.xlsx`, `Compras_Ago-Oct2026_28e0.xlsx`, `Consignacion_Ago-Oct2026_0aa0.xlsx`.

**Entorno de esta corrida:** Cloud Agent **sin** pool MySQL BestSox (`BESTSOX_BASE_EMPRESA` no configurada). 
Los números «Informe (Synap)» provienen de ejecutar los **runners** con consultas mockeadas usando filas del Excel (fixture `reports/tests/fixtures/bestsox_ago_oct_2026_reference.json`). 
CI/Docker debe pasar `reports.tests.test_bestsox_marca_reports_reference_totals`.

Para validación contra administraNET real: exportar `BESTSOX_BASE_EMPRESA` y correr tests tag `bestsox_mysql`.

## Producción

### Totales generales

| Métrica | Referencia Excel | Informe (Synap, fixture) | Δ |
|---------|------------------:|-------------------------:|---|
| Pares total | 1.087.464 | 1.087.464 | 0 |
| Docenas total | 90.622 | 90.622 | 0 |

### Por mes (pares)

| Mes | Referencia | Informe | Δ |
|-----|----------:|--------:|---|
| Ago | 341.232 | 341.232 | 0 |
| Sep | 356.251 | 356.251 | 0 |
| Oct | 389.981 | 389.981 | 0 |

### Por marca (pares total)

| Marca | Referencia | Informe | Δ |
|-------|----------:|--------:|---|
| PUM | 949.943 | 949.943 | 0 |
| AT | 33.582 | 33.582 | 0 |
| REE | 24.701 | 24.701 | 0 |
| VAR | 23.289 | 23.289 | 0 |
| LEV | 16.391 | 16.391 | 0 |
| -Ninguno- | 11.758 | 11.758 | 0 |
| TP | 6.531 | 6.531 | 0 |
| MATEU | 6.514 | 6.514 | 0 |
| HD | 5.026 | 5.026 | 0 |
| BN | 2.731 | 2.731 | 0 |
| BULL | 2.206 | 2.206 | 0 |
| BP | 2.106 | 2.106 | 0 |
| KP | 1.326 | 1.326 | 0 |
| RS | 870 | 870 | 0 |
| PUB | 292 | 292 | 0 |
| TEI | 198 | 198 | 0 |

## Compras

### Totales generales

| Métrica | Referencia | Informe | Δ |
|---------|----------:|--------:|---|
| Packs | 30182 | 30182 | 0 |
| Prendas | 34005 | 34005 | 0 |
| Docenas | 2833.75 | 2833.75 | 0 |

### Por mes

| Mes | Packs ref | Packs inf | Prendas ref | Prendas inf | Docenas ref | Docenas inf |
|-----|----------:|----------:|------------:|------------:|------------:|------------:|
| Ago | 1422 | 1422 | 2599 | 2599 | 216.5833333333333 | 216.5833333333333 |
| Sep | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| Oct | 28760 | 28760 | 31406 | 31406 | 2617.166666666667 | 2617.166666666667 |

### Por marca (packs total)

| Marca | Referencia | Informe | Δ |
|-------|----------:|--------:|---|
| LB | 3823 | 3823 | 0 |
| PUS | 5534 | 5534 | 0 |
| PUW | 19952 | 19952 | 0 |
| RW | 873 | 873 | 0 |

## Consignación

*(El Excel de referencia no desglosa por mes; solo saldo del período de remitos.)*

| Métrica | Referencia | Informe | Δ |
|---------|----------:|--------:|---|
| Packs saldo | 696 | 696 | 0 |
| Prendas saldo | 1782 | 1782 | 0 |
| Docenas saldo | 148.5 | 148.5 | 0 |

### Por marca

| Marca | Packs ref | Packs inf | Prendas ref | Prendas inf | Docenas ref | Docenas inf |
|-------|----------:|----------:|------------:|------------:|------------:|------------:|
| PUM | 696 | 696 | 1782 | 1782 | 148.5 | 148.5 |

## Cambios de consulta en el PR

- Join marca: `m.CodMarca = a.CodigoMarca` (tabla `marca`).
- Fasón / Selene: filtro por `stock.TipoComp = 'Mov. Interno Entrada'`; fasón incluye detalle `FABRICA S Y M`.
- Compras terceros: reglas por proveedor/detalle + rango de fechas (sin IDs fijos); dedupe por `id_stock`.
- Consignación: `cliente.nombre_cliente`, LIKE parametrizado, subquery `rem_fact` correlacionada en WHERE.
- Errores SQL: ya no se tragan en `consultar_*` (propagan al runner con log `error`).

Para revalidar en BestSox: `BESTSOX_BASE_EMPRESA=<base> python manage.py test reports.tests.test_bestsox_marca_sql_contract --tag=bestsox_mysql`.
