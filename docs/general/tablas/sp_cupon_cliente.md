# Tabla `sp_cupon_cliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| fecha_cupon | DATE | Sí |  |  |  |
| id_sp_cupon | BIGINT | No | ✓ |  |  |
| id_sp_desc | BIGINT | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| nro_cupon | BIGINT | Sí |  |  |  |
| datos_cliente_ocasional | VARCHAR | Sí |  |  |  |
| nombre_cliente_ocasional | VARCHAR | Sí |  |  |  |
| domicilio_cliente_ocasional | VARCHAR | Sí |  |  |  |
| documento_cliente_ocasional | VARCHAR | Sí |  |  |  |
| cel_wp_ocasional | VARCHAR | Sí |  |  |  |
| mail_ocasional | VARCHAR | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_voucher | VARCHAR | Sí |  |  |  |
| nro_voucher_serie | VARCHAR | Sí |  |  |  |
| voucher_usado | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| TPV.frm | 40385 | SELECT | rs_guardar.Open "SELECT * FROM sp_cupon_cliente WHERE id_sp_… |
| TPV.frm | 40452 | UPDATE | conn_interno.Execute "UPDATE sp_cupon_cliente SET sp_cupon_c… |
| FacturaB.frm | 27480 | SELECT | '    rs_guardar.Open "SELECT * FROM sp_cupon_cliente WHERE i… |
| FacturaB.frm | 27571 | SELECT | rs_guardar.Open "SELECT * FROM sp_cupon_cliente WHERE id_sp_… |
| FacturaB.frm | 27638 | UPDATE | conn_interno.Execute "UPDATE sp_cupon_cliente SET sp_cupon_c… |
| FacturaA.frm | 23298 | SELECT | '    rs_guardar.Open "SELECT * FROM sp_cupon_cliente WHERE i… |
| FacturaA.frm | 23389 | SELECT | rs_guardar.Open "SELECT * FROM sp_cupon_cliente WHERE id_sp_… |
| FacturaA.frm | 23455 | UPDATE | conn_interno.Execute "UPDATE sp_cupon_cliente SET sp_cupon_c… |
| Programa_Descuentos_Canje.frm | 967 | JOIN | "LEFT JOIN sp_cupon_cliente ON (sp_cupon_cliente.id_sp_desc … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)