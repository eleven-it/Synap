# REP_INVENTARIOS — esquema y mapeo MPR

**Fecha:** 10/07/2026  
**Fuente:** Azure BEST (solo lectura) — vista `REP_INVENTARIOS`

## Columnas relevantes

| Columna BEST | Tipo | Uso en Synap |
|--------------|------|--------------|
| `[Id Deposito]` | int | `BestDepositoMap.best_id_deposito` |
| `Deposito` | varchar | Nombre depósito / etapa CC |
| `[Id Articulo]` | varchar (MMID) | `BestStockInicialMap.best_id_articulo` |
| `Articulo` | varchar | Descripción |
| `Stock` | float | **Pares** (UM = par). Usar `SUM(Stock)` — no convertir docenas×12 |
| `Docenas` | float | Referencia opcional (`best_docenas`) |
| `Disponible` | float | No usado en opening balance |

## Depósitos vigentes (~10/07/2026)

| Id | Nombre | tipo_mpr Admin |
|----|--------|----------------|
| 4000 | Depósito Producción | Produccion |
| 4002 | Semi-Embalado | SemiElaborado |
| 4003 | Terminado | Terminado |
| 4004 | Sobrante y Segunda | 2daSeleccion |

Admin `administranet1` (referencia): depósitos 1–7 con `tipo_mpr` a setear al validar mapeo.

## Consulta de sincronización

```sql
SELECT [Id Articulo] AS id_art, MAX(Articulo) AS articulo,
       [Id Deposito] AS id_dep, MAX(Deposito) AS deposito,
       SUM(COALESCE(Stock, 0)) AS stock_pares,
       SUM(COALESCE(Docenas, 0)) AS docenas
FROM REP_INVENTARIOS
WHERE COALESCE(Stock, 0) <> 0
GROUP BY [Id Articulo], [Id Deposito]
```

Destino: `stock_deposito` (`id_articulo`, `id_deposito`, `saldo`) vía `cargar_stock_inicial_best`.
