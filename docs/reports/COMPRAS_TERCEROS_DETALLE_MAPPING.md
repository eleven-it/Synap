# Mapeo de ingresos de terceros (informe Compras)

El informe **Compras por marca y SuperArtículo** (`compras-marca-superart`) incluye:

1. **Compras estándar**: líneas `stock` con `TipoComp` Compra o Remito Entrada, `Tipo='Proveedor'`, comprobantes no anulados, artículos terminados (no insumos ni Gasto).
2. **Exclusiones**: facturas a artículo genérico `1805` Mercaderías Terminadas con cantidad 1; anticipos; artículos tipo Gasto.
3. **Ingresos agregados por regla**: movimientos internos/ajustes en depósito terminado identificados por proveedor o texto en `movimiento_stock.Detalle` / `comp_ped.Detalle`.

## Configuración

Lista de reglas en código (`reports/services/compras_terceros_config.py`) con override opcional:

```python
# settings.py
REPORTS_COMPRAS_TERCEROS_REGLAS = [
    {
        "id": "selene_import",
        "match": {"detalle_contains": "INGRESO EXPORTACION SELENE"},
        "deposito_id": 6,
        "tipo_movimiento": "Mov. Interno Entrada",
    },
    {
        "id": "mys_underwear",
        "match": {"codigo_proveedor": 640},
        "movimiento_ids": [17219, 17221, 17222, 18677],
        "deposito_id": 6,
    },
]
```

Campos soportados por regla:

| Campo | Uso |
| --- | --- |
| `match.detalle_contains` | Subcadena case-insensitive en detalle del movimiento |
| `match.codigo_proveedor` | Código proveedor en cabecera cuando exista |
| `movimiento_ids` | Lista explícita de `movimiento_stock.codigo_movimiento` |
| `deposito_id` | Restringe líneas al depósito indicado |
| `tipo_movimiento` | Ej. `Mov. Interno Entrada`, `Ajuste` |

Las reglas son **solo lectura** en runtime; cambios requieren despliegue o override en settings.

## Validación BestSox Ago–Oct 2026

Totales de referencia: **30.182 packs / 34.005 prendas / 2.833,75 docenas** (Excel adjunto).
