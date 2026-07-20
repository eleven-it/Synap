# Documentación Stock / Inventario (Synap)

Módulo **Stock**: movimientos, inventario por etapa MPR y consultas relacionadas.

## Índice

| Documento | Audiencia | Descripción |
|-----------|-----------|-------------|
| [MANUAL_USUARIO_STOCK.md](MANUAL_USUARIO_STOCK.md) | **Usuario** | Uso de Inventario por etapa y orientación al alta de movimientos. |
| [manual_usuario_stock.html](manual_usuario_stock.html) | **Usuario** | Manual HTML navegable (generado desde el MD). En la app: **`/stock/manual/`** (requiere login). Regenerar: `python scripts/generar_manuales_html.py`. |
| [INVENTARIO_TABLA_MPR.md](INVENTARIO_TABLA_MPR.md) | Desarrollo + usuario técnico | Inventario pivoteado por `tipo_mpr`, columnas Talle/Color CE, filtros, API. |
| [ALTA_MOVIMIENTO_UX.md](ALTA_MOVIMIENTO_UX.md) | Desarrollo | Notas de UX del alta de movimiento de stock. |

## Relacionado (otros módulos)

- Campos CE TALLES/COLOR: [../mpr/ARTICULO_CE_TALLES_COLOR.md](../mpr/ARTICULO_CE_TALLES_COLOR.md)
- Depósitos MPR (`tipo_mpr`): docs MPR / `ALTER_deposito_tipo_mpr.sql`
- Búsqueda predictiva en movimientos: [../general/BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md](../general/BUSQUEDA_PREDICTIVA_ARTICULO_MOVIMIENTO_STOCK.md)
