-- MPR roster multi-turno: UK (fecha, id_operario, id_mpr_turno)
-- Documentación / referencia. La lógica idempotente se ejecuta en Python vía
-- proveedor legacy_mysql_schema ``mpr_roster_multi_turno`` (run_mpr_roster_multi_turno_mysql).
--
-- Pre-deploy checklist (manual):
--   SELECT COUNT(*) FROM mpr_roster_dia;
--   SELECT COUNT(*) FROM mpr_roster_dia WHERE id_mpr_linea IS NOT NULL;
--   SHOW INDEX FROM mpr_roster_dia;
--
-- Post-deploy checklist:
--   Recontar filas (debe ser igual).
--   SHOW INDEX: uk_mpr_roster_fecha_operario_turno presente; uk_mpr_roster_fecha_operario ausente.
--
-- IMPORTANTE: no DELETE / TRUNCATE / UPDATE masivo de datos de negocio en esta migración.

-- Guard idempotente (ejecutar solo si aplica; en prod usar el proveedor Python):

-- IF EXISTS uk_mpr_roster_fecha_operario AND NOT EXISTS uk_mpr_roster_fecha_operario_turno:
--   ALTER TABLE mpr_roster_dia DROP INDEX uk_mpr_roster_fecha_operario;
--   ALTER TABLE mpr_roster_dia
--     ADD UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno);

-- IF uk_mpr_roster_fecha_operario_turno already exists → no-op.
