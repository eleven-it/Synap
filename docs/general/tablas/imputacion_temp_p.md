# Tabla `imputacion_temp_p`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_imputacion_temp_p | DOUBLE | No | ✓ |  |  |
| fecha_fac_nd | DATE | Sí |  |  |  |
| tipo_comp_fac_nd | VARCHAR | Sí |  |  |  |
| nro_comp_fac_nd | VARCHAR | Sí |  |  |  |
| codmov_fac_nd | DECIMAL | Sí |  |  |  |
| importe_fac_nd | DECIMAL | Sí |  |  |  |
| importe_cancelado_fac_nd | DECIMAL | Sí |  |  |  |
| importe_saldo_fac_nd | DECIMAL | Sí |  |  |  |
| estado_fac_nd | VARCHAR | Sí |  |  |  |
| fecha_nc_op | DATE | Sí |  |  |  |
| tipo_comp_nc_op | VARCHAR | Sí |  |  |  |
| nro_comp_nc_op | VARCHAR | Sí |  |  |  |
| codmov_nc_op | DECIMAL | Sí |  |  |  |
| importe_nc_op | DECIMAL | Sí |  |  |  |
| importe_cancelado_nc_op | DECIMAL | Sí |  |  |  |
| importe_saldo_nc_op | DECIMAL | Sí |  |  |  |
| estado_nc_op | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| AsigPago.frm | 1219 | SELECT | rs_imputacion_temp.Open "SELECT * FROM imputacion_temp_p WHE… |
| AsigPago.frm | 1448 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_temp_p WHERE id… |
| AsigPago.frm | 1557 | SELECT | conn.Execute "delete from imputacion_temp_p where id_usuario… |
| AsigPago.frm | 1557 | DELETE | conn.Execute "delete from imputacion_temp_p where id_usuario… |
| Principal.frm | 6090 | SELECT | conn.Execute "delete from imputacion_temp_p where id_usuario… |
| Principal.frm | 6090 | DELETE | conn.Execute "delete from imputacion_temp_p where id_usuario… |
| Principal.frm | 6156 | SELECT | conn.Execute "delete from imputacion_temp_p where id_usuario… |
| Principal.frm | 6156 | DELETE | conn.Execute "delete from imputacion_temp_p where id_usuario… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)