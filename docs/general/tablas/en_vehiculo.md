# Tabla `en_vehiculo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_vehiculo | BIGINT | No | ✓ |  |  |
| nombre_vehiculo | VARCHAR | Sí |  |  |  |
| patente_vehiculo | VARCHAR | Sí |  |  |  |
| tipo_vehiculo | VARCHAR | Sí |  |  |  |
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
| En_Carga_Tara_Temporada.frm | 1599 | SELECT | 'consulta = "Select id_en_vehiculo,CONCAT(nombre_vehiculo,' … |
| En_Carga_Tara_Temporada.frm | 1601 | SELECT | consulta = "SELECT id_en_vehiculo,CONCAT(nombre_vehiculo,' '… |
| En_Carga_Tara_Temporada.frm | 1629 | SELECT | 'consulta = "Select id_en_vehiculo,CONCAT(nombre_vehiculo,' … |
| En_Carga_Tara_Temporada.frm | 1633 | SELECT | consulta = "Select id_en_vehiculo,CONCAT(nombre_vehiculo,' '… |
| En_CargaVehiculo.frm | 277 | SELECT | rs_banco.Open "SELECT * FROM en_vehiculo WHERE patente_vehic… |
| En_CargaVehiculo.frm | 293 | SELECT | rs_banco.Open "SELECT * FROM en_vehiculo WHERE  id_en_vehicu… |
| En_CargaVehiculo.frm | 316 | SELECT | En_ABM_Vehiculo.DataVehiculo.RecordSource = "SELECT * FROM e… |
| En_CargaVehiculo.frm | 330 | SELECT | rs_banco.Open "SELECT * FROM en_vehiculo WHERE id_en_vehicul… |
| En_CargaVehiculo.frm | 351 | SELECT | En_ABM_Vehiculo.DataVehiculo.RecordSource = "SELECT * FROM e… |
| En_Carga_Pesaje.frm | 7247 | JOIN | '                " LEFT JOIN en_vehiculo AS vh ON vh.id_en_v… |
| En_Carga_Pesaje.frm | 7396 | JOIN | " LEFT JOIN en_vehiculo AS vh ON vh.id_en_vehiculo = tt.id_e… |
| En_ABM_Vehiculo.frm | 450 | SELECT | consulta = "SELECT * FROM en_vehiculo WHERE " & _ |
| En_Carga_Vale.frm | 6315 | JOIN | '                " LEFT JOIN en_vehiculo AS vh ON vh.id_en_v… |
| En_Carga_Vale.frm | 6528 | JOIN | " LEFT JOIN en_vehiculo AS vh ON vh.id_en_vehiculo = tt.id_e… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)