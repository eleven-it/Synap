# Tabla `viajantes_objetivos_ventas`

Tabla **por base de datos de empresa** (MySQL AdministraNET compartido con VB6). Almacena **objetivos de venta monetarios por cliente** ligados a un período de cabecera (`viajantes_objetivos_periodo`) mediante `id_periodo`. Las filas antiguas pueden tener `id_periodo` NULL y fechas propias; el flujo actual en Synap crea siempre período + detalle. El informe **Objetivos vs BO** ignora objetivos cuyo período esté anulado.

## Convenciones

- Escritura desde Synap debe usar [`core.utils.administranet_types`](../../core/utils/administranet_types.py) según [`docs/general/TIPOS_DATOS_ADMINISTRANET.md`](../TIPOS_DATOS_ADMINISTRANET.md).
- **`CodViajante`** en la fila es **snapshot** al guardar (desde `cliente.CodViajante`); no se actualiza automáticamente si el cliente cambia de vendedor.

## Campos

| Campo | Tipo | Uso |
|-------|------|-----|
| `id` | BIGINT PK AI | Identificador interno. |
| `Codigo` | INT (o tipo alineado a `cliente.Codigo`) | Cliente. |
| `CodViajante` | INT | Vendedor (viajante) **al momento de guardar** el objetivo. |
| `id_periodo` | BIGINT NULL | FK lógica a `viajantes_objetivos_periodo.id`; NULL en datos heredados. |
| `fecha_desde` | DATE | Denormalizado (coincide con cabecera cuando hay `id_periodo`). |
| `fecha_hasta` | DATE | Denormalizado (coincide con cabecera cuando hay `id_periodo`). |
| `objetivo` | DECIMAL(15,2) | Importe objetivo; `0` o ausencia de fila → informe muestra 0. |

## Índices recomendados

- `INDEX idx_vov_cliente (Codigo)`
- `INDEX idx_vov_viajante (CodViajante)`
- `INDEX idx_vov_periodo (fecha_desde, fecha_hasta)` — consultas de solape / legado.
- `INDEX idx_vov_periodo_id (id_periodo)` — filas por cabecera.

## Reglas

- Con cabecera: un objetivo vigente por `Codigo` dentro del mismo `id_periodo` (último `id` por cliente en ese período).
- Períodos anulados: no aplican en informe (filtro por cabecera).
- DDL de referencia: [`docs/general/sql/viajantes_objetivos_ventas.sql`](../sql/viajantes_objetivos_ventas.sql).
