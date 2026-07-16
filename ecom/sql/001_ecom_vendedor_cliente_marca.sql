-- Cuaternas Vendedor → Cliente → Sucursal → Marca (territorio comercial ecom).
-- Proveedor catálogo: ecom_vendedor_cliente_marca
-- Ver docs/ecom/VENDEDOR_CLIENTE_MARCA.md

CREATE TABLE IF NOT EXISTS ecom_vendedor_cliente_marca (
    id BIGINT NOT NULL AUTO_INCREMENT,
    CodViajante INT NOT NULL COMMENT 'viajantes.CodViajante',
    id_cliente INT NOT NULL COMMENT 'cliente.Codigo',
    id_cliente_domicilio INT NOT NULL DEFAULT 0 COMMENT 'cliente_domicilio.id_cliente_domicilio — 0 = sin sucursal',
    CodMarca INT NOT NULL COMMENT 'marca.CodMarca',
    anulado CHAR(2) NOT NULL DEFAULT 'No' COMMENT 'Si | No',
    -- Unique parcial: solo filas activas (anulado=No). Varias anuladas pueden repetir cliente+sucursal+marca.
    anulado_activo TINYINT
        GENERATED ALWAYS AS (IF(anulado = 'No', 1, NULL)) VIRTUAL,
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_mod DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    usuario_mod VARCHAR(60) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_evcm_cliente_sucursal_marca_activo (
        id_cliente, id_cliente_domicilio, CodMarca, anulado_activo
    ),
    KEY idx_evcm_viajante (CodViajante),
    KEY idx_evcm_cliente (id_cliente),
    KEY idx_evcm_domicilio (id_cliente_domicilio),
    KEY idx_evcm_marca (CodMarca)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Cuaterna vendedor-cliente-sucursal-marca (pedido masivo / filtro catálogo)';

CREATE TABLE IF NOT EXISTS ecom_usuario_viajante (
    id BIGINT NOT NULL AUTO_INCREMENT,
    id_usuario INT NOT NULL COMMENT 'usuarios.id_usuario',
    CodViajante INT NOT NULL COMMENT 'viajantes.CodViajante',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_mod DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
    usuario_mod VARCHAR(60) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_euv_usuario (id_usuario),
    KEY idx_euv_viajante (CodViajante)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Mapeo usuario login <-> viajante (complementa usuarios.CodViajante)';
