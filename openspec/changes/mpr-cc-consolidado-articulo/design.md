# Design: Control de calidad consolidado por artículo (Synap / MPR)

**Change:** `mpr-cc-consolidado-articulo`  
**Plan vinculante:** `docs/mpr/PLAN_CC_CONSOLIDADO_POR_ARTICULO.md`

## Enfoque

Tres cortes: (1) módulo `mpr/services_cc_consolidado.py` con builder de bloques por artículo, parser del POST y confirmación atómica por artículo; (2) lecturas agregadas y bloqueo dual en `mpr/repositories/`; (3) tablas de borrador nuevas (007) que conviven con las viejas. `mpr_transicion_lote`, `stock_deposito` y MSTOCK no cambian de esquema ni de datos históricos.

## Decisiones de arquitectura

1. **Wrapper CC atómico sin tocar `transferir_stock_lote`**. Rechazado: `atomic()` en `transferir_stock_lote` y `atomic()` de Django alrededor de N llamadas (`transferir_stock_entre_etapas` abre su propia conexión MySQL). Elegido: una conexión y una TX por artículo con `_transferir_etapa_en_cursor` y ledger en cursor (`crear_transicion_lote_en_cursor`, `cantidad_extra = 0`).

2. **Un solo camino de grilla**. `construir_grilla_clasificacion_produccion` delega al builder nuevo; `turno_id` se acepta y documenta como ignorado. El flujo CC deja de usar `_extra_pool_clasificacion_por_articulo`, `_max_clasificable_celda`, `_atribuible_clasificacion_por_celda`.

3. **Tablas de borrador nuevas**. `mpr_cc_borrador` / `mpr_cc_borrador_linea` (007); las viejas quedan intactas. Semi usa centinela `0` en `id_operario`/`id_mpr_turno`; el repositorio mapea `0 → NULL` al escribir ledger.

4. **Bloqueo dual**: `turnos_con_control_calidad` filtra `tipo_destino IN ('2daSeleccion','Scrap') OR (tipo_destino = 'SemiElaborado' AND id_operario IS NOT NULL)`. Semi nuevo con `id_operario NULL` no bloquea turnos.

## Flujo de confirmación

parser POST → payload por artículo → por artículo: BEGIN, `SELECT saldo stock_deposito Producción FOR UPDATE`, validar tope, MSTOCK + stock + ledger, COMMIT (y borrar líneas de borrador de ese artículo) o ROLLBACK. Resultado `{ok, errores}` → `mprShowAviso`.

## Contratos

- `construir_bloques_cc_articulo(base_empresa, fecha, *, solo_pendiente=False, marcas_incluidos=None)`
- `parsear_post_cc_consolidado(post, *, unidades_por_docena=12)`
- `confirmar_cc_consolidado(base_empresa, id_usuario, fecha, payload)`
- Claves POST: `semi_{art}`, `seg2da_{art}_op_{op}_t_{t}`, `scrap_…`; ignorar `semi_*_op_*`

## Testing

Runner `docker exec Synap_app python manage.py test mpr`. Unit: parser, tope, huérfano, bloqueo dual, centinela 0↔NULL. Integración: S1–S9, B1–B8. Regresión: etapa10, docenas, reporte operario.

## Migración / rollout

`apply_mpr_core_tables` por empresa (007 + índice) → deploy conjunto grilla + POST + templates → sin job de datos → borradores viejos no se convierten. Rollback previo al primer confirm nuevo es limpio; posterior deja Semi sin operario invisible en grilla vieja.
