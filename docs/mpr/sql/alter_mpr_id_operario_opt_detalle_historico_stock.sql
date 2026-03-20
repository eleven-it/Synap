-- MPR: id_operario_opt en detalle, histórico y stock (referencia sue_abm_empleado.id_sue_abm_empleado).
-- Ejecutar en la base administranet de cada empresa (ej. administranet92).
-- Synap escribe estos campos en OPT (crear/liberar), OPP y OPA (armado).

-- Detalle de pedidos vinculado a OPT: operario asignado al confirmar OPT (y actualizable en OPP/OPA según lógica Synap).
ALTER TABLE lista_produccion_detalle
  ADD COLUMN id_operario_opt INT NULL DEFAULT NULL COMMENT 'sue_abm_empleado.id_sue_abm_empleado';

-- Histórico: mismo significado que id_operario (trazabilidad); id_operario_opt unifica nomenclatura con agrupada/stock.
ALTER TABLE lista_produccion_historico
  ADD COLUMN id_operario_opt INT NULL DEFAULT NULL COMMENT 'sue_abm_empleado.id_sue_abm_empleado';

-- Renglones de stock generados por MPR (OPT/OPP/OPA).
ALTER TABLE stock
  ADD COLUMN id_operario_opt INT NULL DEFAULT NULL COMMENT 'sue_abm_empleado.id_sue_abm_empleado';
