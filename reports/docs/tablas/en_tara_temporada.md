# Tabla `en_tara_temporada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tara | BIGINT | No | ✓ |  |  |
| id_temporada | BIGINT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_en_vehiculo | BIGINT | Sí |  |  |  |
| tara | DECIMAL | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| fecha_hora | TIMESTAMP | No |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| En_ABM_Tara_Temporada.frm | 551 | SELECT | " FROM en_tara_temporada t, en_temporada s ,en_vehiculo v " … |
| En_Carga_Tara_Temporada.frm | 1335 | SELECT | rs_control_tara.Open "SELECT * FROM en_tara_temporada WHERE … |
| En_Carga_Tara_Temporada.frm | 1348 | SELECT | rs_EnArt.Open "SELECT * FROM en_tara_temporada WHERE  id_tar… |
| En_Carga_Tara_Temporada.frm | 1391 | SELECT | rs_EnArt.Open "SELECT * FROM en_tara_temporada WHERE id_tara… |
| En_Carga_Tara_Temporada.frm | 1587 | SELECT | cargo_data_abm = "SELECT t.id_tara, t.id_temporada, t.fecha,… |
| En_Carga_Pesaje.frm | 5459 | JOIN | "LEFT JOIN en_tara_temporada AS tt ON tt.id_tara=vv.id_tara_… |
| En_Carga_Pesaje.frm | 7123 | SELECT | rs_tara_vehiculo.Open "SELECT * FROM en_tara_temporada WHERE… |
| En_Carga_Vale.frm | 4043 | JOIN | " LEFT JOIN en_tara_temporada AS tt ON tt.id_tara = vv.id_ta… |
| En_Carga_Vale.frm | 4753 | JOIN | "LEFT JOIN en_tara_temporada AS tt ON tt.id_tara=vv.id_tara_… |
| En_Carga_Vale.frm | 5778 | JOIN | " LEFT JOIN en_tara_temporada AS tt ON tt.id_tara = vv.id_ta… |
| En_Carga_Vale.frm | 6196 | SELECT | rs_tara_vehiculo.Open "SELECT * FROM en_tara_temporada WHERE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)