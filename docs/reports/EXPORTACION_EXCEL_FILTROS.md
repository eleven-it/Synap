# Exportación Excel — bloque de filtros

## Comportamiento

En toda exportación `.xlsx` generada por `ExportService`, **antes de las notas y de la tabla de datos**, se escribe un bloque **«Filtros aplicados»** con pares etiqueta / valor en español.

- Los filtros por **código** (sucursal, punto de venta, depósito, cliente, vendedor, rubro, subrubro, marca) se resuelven a **nombre o descripción** consultando MySQL legacy (`base_empresa` del payload).
- Las **fechas** se muestran como `dd/MM/yyyy`.
- Lista de precio usa `lista_precio_label` del meta cuando existe.
- Ordenamiento y alcance Excel (Resumen / Detallado) se traducen a texto legible.

## Implementación

| Archivo | Rol |
|---------|-----|
| `reports/services/export_filter_labels.py` | `build_export_filter_lines()` |
| `reports/services/export_service.py` | `_append_excel_filter_block()` en Excel simple, BO multi-hoja y presupuesto |

## Extensión

Para filtros nuevos: añadir entrada en `_FILTER_SPECS` y, si aplica, consulta en `_MysqlLabelLookup`. Opcionalmente el frontend puede enviar `filters.filter_labels` con pares `{ "Etiqueta visible": "valor" }` adicionales.

## Tests

```bash
docker exec Synap_app python manage.py test reports.tests.test_export_filter_labels
```
