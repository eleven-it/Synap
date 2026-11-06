-- Inventario físico: saldo_snapshot inmutable después de crear la campaña.
-- Aditivo y no destructivo (no altera columnas ni datos). Aplicar manualmente por entorno.
-- Rollback: DROP TRIGGER IF EXISTS trg_inv_fisico_linea_snapshot_inmutable;
DROP TRIGGER IF EXISTS trg_inv_fisico_linea_snapshot_inmutable;
DELIMITER $$
CREATE TRIGGER trg_inv_fisico_linea_snapshot_inmutable
BEFORE UPDATE ON inv_fisico_linea
FOR EACH ROW
BEGIN
  IF NOT (NEW.saldo_snapshot <=> OLD.saldo_snapshot) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'inv_fisico_linea.saldo_snapshot es inmutable';
  END IF;
END$$
DELIMITER ;
