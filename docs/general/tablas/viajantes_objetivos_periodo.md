# Tabla `viajantes_objetivos_periodo`

Cabecera de **intervalo de fechas** para objetivos de venta (Synap). Una fila representa un período editable; la anulación lógica sigue el criterio AdministraNET (`anulado` = `Si` / `No`), sin borrar el detalle en `viajantes_objetivos_ventas`.

## Campos

| Campo | Tipo | Uso |
|-------|------|-----|
| `id` | BIGINT PK AI | Identificador del período. |
| `fecha_desde` | DATE | Inicio inclusive. |
| `fecha_hasta` | DATE | Fin inclusive. |
| `descripcion` | VARCHAR(120) | Etiqueta legible del período (ej. «Abril 2026»). Valor reservado `"-"` cuando no se informa (paridad campos opcionales AdministraNET). En Synap se puede editar en la pantalla de detalle del período (`/ventas/objetivos-venta/<id>/`) con permiso `ventas.editar` y período no anulado. |
| `anulado` | VARCHAR | `No` = activo; `Si` = período anulado (no aplica en informes ni edición). |

## Reglas

- No deben solaparse dos períodos **activos** (`anulado = No`) en el mismo rango; la validación está en `ventas.services.objetivos_mysql.crear_periodo_objetivos`.
- DDL idempotente: proveedor `viajantes_objetivos_ventas` en `core/services/legacy_mysql_schema/catalog.py`.

## SQL de referencia

- DDL completo: [`docs/general/sql/viajantes_objetivos_periodo.sql`](../sql/viajantes_objetivos_periodo.sql).
- Solo columna `descripcion` en bases ya creadas: [`docs/general/sql/alter_viajantes_objetivos_periodo_descripcion.sql`](../sql/alter_viajantes_objetivos_periodo_descripcion.sql) (Synap también intenta el `ALTER` al primer uso vía `ventas.services.objetivos_mysql`).
