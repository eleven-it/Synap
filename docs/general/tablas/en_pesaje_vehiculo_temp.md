# Tabla `en_pesaje_vehiculo_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_vehiculo_pesaje_temp | BIGINT | No | ✓ |  |  |
| id_en_vehiculo | BIGINT | Sí |  |  |  |
| vehiculo_patente | VARCHAR | Sí |  |  |  |
| tipo_vehiculo | VARCHAR | Sí |  |  |  |
| id_en_tara_vehiculo | BIGINT | Sí |  |  |  |
| bruto_vehiculo | DECIMAL | Sí |  |  |  |
| tara_vehiculo | DECIMAL | Sí |  |  |  |
| neto_vehiculo | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| id_en_precio_zona_temporada | BIGINT | Sí |  |  |  |
| tara_bin | DECIMAL | Sí |  |  |  |
| precio_kg | DECIMAL | Sí |  |  |  |
| total_viaje_vehiculo | DECIMAL | Sí |  |  |  |
| nombre_vehiculo | VARCHAR | Sí |  |  |  |
| nombre_zona | VARCHAR | Sí |  |  |  |

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
| En_Carga_Pesaje.frm | 5422 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Pesaje.frm | 6453 | SELECT | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Pesaje.frm | 6453 | DELETE | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Pesaje.frm | 6765 | SELECT | rs_temp_bines_unidad.Open "SELECT * FROM en_pesaje_vehiculo_… |
| En_Carga_Pesaje.frm | 6813 | SELECT | rs_temp_bines_unidad.Open "SELECT * FROM en_pesaje_vehiculo_… |
| En_Carga_Pesaje.frm | 6853 | SELECT | '                                   " FROM en_pesaje_vehicul… |
| En_Carga_Pesaje.frm | 6861 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Pesaje.frm | 6922 | SELECT | rs_total_auto.Open "SELECT * FROM en_pesaje_vehiculo_temp AS… |
| En_Carga_Pesaje.frm | 7177 | UPDATE | conn.Execute "UPDATE en_pesaje_vehiculo_temp AS pt SET pt.ta… |
| En_Carga_Pesaje.frm | 7186 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Vale.frm | 4035 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Vale.frm | 4515 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Vale.frm | 5382 | SELECT | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Vale.frm | 5382 | DELETE | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Vale.frm | 5685 | SELECT | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Vale.frm | 5685 | DELETE | conn.Execute "DELETE FROM en_pesaje_vehiculo_temp WHERE en_p… |
| En_Carga_Vale.frm | 5784 | SELECT | rs_temp_bines_unidad.Open "SELECT * FROM en_pesaje_vehiculo_… |
| En_Carga_Vale.frm | 5813 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Vale.frm | 5857 | SELECT | rs_temp_bines_unidad.Open "SELECT * FROM en_pesaje_vehiculo_… |
| En_Carga_Vale.frm | 5905 | SELECT | rs_temp_bines_unidad.Open "SELECT * FROM en_pesaje_vehiculo_… |
| En_Carga_Vale.frm | 5945 | SELECT | '                                   " FROM en_pesaje_vehicul… |
| En_Carga_Vale.frm | 5953 | SELECT | " FROM en_pesaje_vehiculo_temp AS pv " & _ |
| En_Carga_Vale.frm | 6013 | SELECT | rs_total_auto.Open "SELECT * FROM en_pesaje_vehiculo_temp AS… |
| En_Carga_Vale.frm | 6253 | UPDATE | '    conn.Execute "UPDATE en_pesaje_vehiculo_temp AS pt SET … |
| En_Carga_Vale.frm | 6470 | UPDATE | conn.Execute "UPDATE en_pesaje_vehiculo_temp as vv SET " & _ |
| Principal.frm | 6114 | SELECT | conn.Execute "delete from en_pesaje_vehiculo_temp where id_u… |
| Principal.frm | 6114 | DELETE | conn.Execute "delete from en_pesaje_vehiculo_temp where id_u… |
| Principal.frm | 6180 | SELECT | conn.Execute "delete from en_pesaje_vehiculo_temp where id_u… |
| Principal.frm | 6180 | DELETE | conn.Execute "delete from en_pesaje_vehiculo_temp where id_u… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)