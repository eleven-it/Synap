-- Cuaternas Vendedor → Cliente → Sucursal → Marca (extensión territorio comercial).
-- Proveedor catálogo: ecom_vendedor_cliente_marca (aplica 001 + 002 + migración datos).
-- Ver docs/ecom/VENDEDOR_CLIENTE_MARCA.md

-- Columna sucursal (cliente_domicilio.id_cliente_domicilio). Idempotente vía catálogo.
ALTER TABLE ecom_vendedor_cliente_marca
    ADD COLUMN id_cliente_domicilio INT NOT NULL DEFAULT 0
        COMMENT 'cliente_domicilio.id_cliente_domicilio — 0 = sin sucursal (edge case)'
        AFTER id_cliente;

-- Unique activo: (cliente, sucursal, marca) — la misma marca puede ir a otro vendedor en otra sucursal.
ALTER TABLE ecom_vendedor_cliente_marca
    DROP INDEX uk_evcm_cliente_marca_activo;

ALTER TABLE ecom_vendedor_cliente_marca
    ADD UNIQUE KEY uk_evcm_cliente_sucursal_marca_activo (
        id_cliente, id_cliente_domicilio, CodMarca, anulado_activo
    );

ALTER TABLE ecom_vendedor_cliente_marca
    ADD KEY idx_evcm_domicilio (id_cliente_domicilio);
