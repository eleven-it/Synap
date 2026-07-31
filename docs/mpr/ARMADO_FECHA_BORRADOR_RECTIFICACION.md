# Armado: fecha, borrador y rectificación híbrida

Documentación operativa del flujo de **Armado 1ra/2da** con fecha de realizado, borradores, anulación y corrección delta.

## Estados del lote (`mpr_armado_lote.estado`)

| Estado | Descripción | MSTOCK |
|--------|-------------|--------|
| `borrador` | Carrito persistido sin movimiento físico | No (`movimiento_fisico_ok=0`) |
| `aprobado` | Lote ejecutado con MSTOCK | Sí (`movimiento_fisico_ok=1`) |
| `anulado` | Reversión física completada | No |

## Flujo en pantalla POS (`/mpr/armado/`)

1. **Cabecera:** origen, destino, operario, detalle, **fecha realizado** (dd/MM/yyyy, default hoy).
2. **Carrito:** packs + composición (BOM 1ra o libre 2da).
3. **Guardar borrador:** persiste lote + ítems en `mpr_armado_lote_item` / `_linea` sin llamar a stock.
4. **Guardar armado:** ejecuta MSTOCK por ítem (commit parcial), marca lote `aprobado`.
5. **Reutilizar borrador:** si POST trae `id_mpr_armado_lote` de un borrador, se actualiza el mismo lote.
6. **Anular lote** (solo aprobado): modal Synap → POST `accion=anular` → reversión MSTOCK espejo por movimiento.

## Fecha de realizado

- Campo `fecha_realizado` en cabecera (acepta dd/MM/yyyy o yyyy-MM-dd).
- Se usa como `fecha` del comprobante MSTOCK (puede ser fecha pasada).
- En anulación/rectificación se reutiliza la fecha del lote o hoy.

## Rectificación híbrida (`corregir_lote_armado_aprobado`)

Solo sobre lotes **aprobados** sin imputación bloqueante:

- Compara cantidades por `id_articulo_pack` vs movimientos actuales del lote.
- **Delta > 0:** armado adicional del delta (mismo `id_mpr_armado_lote`).
- **Delta < 0:** reversión de |delta| packs (valida saldo Terminado en destino).
- **Composición distinta:** error — «Cambió la composición; anulá el lote y armá de nuevo».
- Actualiza snapshot de ítems del lote.

## Candados de imputación (Armado 1ra)

No se puede **anular** ni **corregir** si algún movimiento del lote tiene `estado_imputacion` en `parcial` o `completo`. Hay que revertir la imputación primero (pantalla Imputación de pedido).

## Catálogo `tipo_art_fab`

| Modo | Pack (terminado) | Componentes composición libre |
|------|------------------|-------------------------------|
| **1ra** | `Terminado` + ensamblado=Si + BOM MSTOCK | BOM fijo (semi) |
| **2da** | `Fabricado 2da` (sin cambio) | Búsqueda stock origen filtra `Fabricado` |

## Tablas MySQL

- DDL: `mpr/sql/007_mpr_armado_lote_fecha_estado.sql`
- Migración idempotente: `core/services/legacy_mysql_schema/catalog.py` → `run_mpr_core_tables_mysql`
- Espejo Postgres opcional: modelo `MprArmadoLote` (campos `fecha_realizado`, `estado`, `movimiento_fisico_ok`, `detalle`)

## Prueba manual

1. Aplicar esquema MySQL si falta (`manage.py` herramienta global o catalog).
2. Ir a `/mpr/armado/?modo=2da`, armar carrito, **Guardar borrador** → verificar fila en `mpr_armado_lote` estado=borrador sin filas en `mpr_armado_surtido_movimiento`.
3. Recargar con `?id_lote=<id>` → carrito precargado.
4. **Guardar armado** con fecha ayer → MSTOCK con esa fecha.
5. Lote aprobado → **Anular lote** (sin imputación previa).
6. Armado 1ra: catálogo packs solo muestra artículos `tipo_art_fab=Terminado`.

Ver también: `docs/mpr/GLOSARIO_MPR.md`, `docs/mpr/DISENO_ARMADO_TABLERO_PCP.md`.
