# Mapeo de ingresos de terceros (informe Compras)

El informe **Compras por marca y SuperArtículo** (`compras-marca-superart`) incluye:

1. **Compras estándar**: líneas `stock` con `TipoComp` Compra o Remito Entrada, `Tipo='Proveedor'`, comprobantes no anulados, artículos terminados (no insumos ni Gasto).
2. **Exclusiones**: facturas a artículo genérico `1805` Mercaderías Terminadas con cantidad 1; anticipos; artículos tipo Gasto.
3. **Ingresos agregados por regla**: movimientos en depósito terminado identificados por **proveedor** (`cuentaproveedor.Codigo`) o **texto en `movimiento_stock.detalle`**, con rango de fechas en `movimiento_stock.Fecha`.

## Configuración

Reglas en `reports/services/compras_terceros_config.py`, override opcional:

```python
REPORTS_COMPRAS_TERCEROS_REGLAS = [
    {
        "id": "selene_import",
        "match": {"detalle_contains": "INGRESO EXPORTACION SELENE"},
        "deposito_id": 6,
        "require_tipo_comp": "Mov. Interno Entrada",
    },
    {
        "id": "mys_underwear",
        "match": {"codigo_proveedor": 640},
        "deposito_id": 6,
    },
]
```

| Campo | Uso |
| --- | --- |
| `match.detalle_contains` | Subcadena en `movimiento_stock.detalle` (parametrizada) |
| `require_tipo_comp` | Opcional; Selene exige `stock.TipoComp = 'Mov. Interno Entrada'`; MYS/JIMMY no |
| `deposito_id` | Restringe `stock.CodDeposito` |

Ejemplos default: Selene `INGRESO EXPORTACION SELENE`; MYS `MYS UNDERWEAR`; Jimmy `INGRESO DE JIMMY`.
Los movimientos internos **no** tienen fila en `cuentaproveedor`; el match es solo por detalle + depósito + fechas.

## Dedupe

Cada línea se trae con `stock.id_stock`. Al combinar estándar + reglas se **deduplica por id_stock** (no suma). La compra estándar además excluye líneas que ya cumplen alguna regla (`NOT EXISTS`).

## Validación BestSox Ago–Oct 2026

Totales de referencia: **30.182 packs / 34.005 prendas / 2.833,75 docenas**.
