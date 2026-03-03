# Tabla `imputacion_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_imputacion_temp | DOUBLE | No | ✓ |  |  |
| fecha_fac_nd | DATE | Sí |  |  |  |
| tipo_comp_fac_nd | VARCHAR | Sí |  |  |  |
| nro_comp_fac_nd | VARCHAR | Sí |  |  |  |
| codmov_fac_nd | DECIMAL | Sí |  |  |  |
| importe_fac_nd | DECIMAL | Sí |  |  |  |
| importe_cancelado_fac_nd | DECIMAL | Sí |  |  |  |
| importe_saldo_fac_nd | DECIMAL | Sí |  |  |  |
| estado_fac_nd | VARCHAR | Sí |  |  |  |
| fecha_nc_rec | DATE | Sí |  |  |  |
| tipo_comp_nc_rec | VARCHAR | Sí |  |  |  |
| nro_comp_nc_rec | VARCHAR | Sí |  |  |  |
| codmov_nc_rec | DECIMAL | Sí |  |  |  |
| importe_nc_rec | DECIMAL | Sí |  |  |  |
| importe_cancelado_nc_rec | DECIMAL | Sí |  |  |  |
| importe_saldo_nc_rec | DECIMAL | Sí |  |  |  |
| estado_nc_rec | VARCHAR | Sí |  |  |  |
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
| Principal.frm | 6089 | SELECT | conn.Execute "delete from imputacion_temp where id_usuario =… |
| Principal.frm | 6089 | DELETE | conn.Execute "delete from imputacion_temp where id_usuario =… |
| Principal.frm | 6155 | SELECT | conn.Execute "delete from imputacion_temp where id_usuario =… |
| Principal.frm | 6155 | DELETE | conn.Execute "delete from imputacion_temp where id_usuario =… |
| AsigCobranza.frm | 1229 | SELECT | rs_imputacion_temp.Open "SELECT * FROM imputacion_temp WHERE… |
| AsigCobranza.frm | 1458 | SELECT | '    rs_imputacion.Open "SELECT * FROM imputacion_temp WHERE… |
| AsigCobranza.frm | 1618 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_temp WHERE id_i… |
| AsigCobranza.frm | 1734 | SELECT | conn.Execute "delete from imputacion_temp where id_usuario =… |
| AsigCobranza.frm | 1734 | DELETE | conn.Execute "delete from imputacion_temp where id_usuario =… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)