# Armado: fecha, borrador y rectificación híbrida

Documentación operativa del flujo de **Armado 1ra/2da** con fecha de realizado, borradores, anulación y corrección delta.

## Estados del lote (`mpr_armado_lote.estado`)

| Estado | Descripción | MSTOCK |
|--------|-------------|--------|
| `borrador` | Carrito persistido sin movimiento físico | No (`movimiento_fisico_ok=0`) |
| `aprobado` | Lote ejecutado con MSTOCK | Sí (`movimiento_fisico_ok=1`) |
| `anulado` | Reversión física completada | No |

## Flujo en pantalla tablero (`/mpr/armado/?vista=tablero`)

La vista POS/carrito (`?vista=pos`, plantilla `armado_surtido.html`) quedó **deprecada**: GET redirige a tablero.

### Armado 1ra (operativo)

1. **Chrome:** toggle 1ra/2da, búsqueda, **fecha realizado**, Actualizar, **Ejecutar armado**.
2. **Grilla:** cantidades en columna Armar (BOM fija) → POST `vista=tablero` con `fecha_realizado` (dd/MM/yyyy).
3. **Resultado:** modal Synap (grabados / fallidos).

### Borrador / anulación / carrito (legacy backend)

El POST con `lote_json` + `accion=borrador|aprobar|anular` sigue disponible en backend (tests / transición 2da). No hay UI POS para armarlo: Armado 2da en tablero aún no tiene composición libre.

## Armado 2da en tablero

Criterio de filas (no usa demanda PED):

1. Pack con `articulo.tipo_art_fab = 'Fabricado 2da'`.
2. **Armable** si:
   - tiene BOM y máx. packs > 0 en depósito 2da selección, **o**
   - no tiene BOM y hay stock `Fabricado` en ese depósito (composición libre).

Verificación: IDArt 1371 en base Best (`administranet`) debe listarse cuando hay componentes Fabricado en 2da.

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
2. Ir a `/mpr/armado/?modo=1ra&vista=tablero`, completar Armar + fecha, **Ejecutar armado** → verificar MSTOCK con esa fecha.
3. (Backend) POST `lote_json` con `accion=borrador` → fila en `mpr_armado_lote` estado=borrador sin filas en `mpr_armado_surtido_movimiento`.
4. Lote aprobado → anulación/corrección según candados de imputación.
5. Armado 1ra: catálogo packs solo muestra artículos `tipo_art_fab=Terminado`.
6. GET `?vista=pos` → redirect 302 a `vista=tablero`.

Ver también: `docs/mpr/GLOSARIO_MPR.md`, `docs/mpr/DISENO_ARMADO_TABLERO_PCP.md`.
