-- =============================================================================
-- cantidad_asignada_opt: cantidad de packs asignada a esta OPT al crearla (para restante por armar).
-- =============================================================================
-- Ejecutar en la base de la empresa (ej. administranet92).
-- Permite mostrar "Armar más" y habilitar armado en detalle cuando queda restante por armar
-- tras un armado parcial (ej. 50 de 60), aunque cantidad_pendiente_prod ya sea 0.
-- =============================================================================

-- cantidad_asignada_opt: al crear la OPT se guarda la cantidad; no se modifica al registrar OPP.
ALTER TABLE lista_produccion_agrupada ADD COLUMN cantidad_asignada_opt INT NULL DEFAULT NULL;
