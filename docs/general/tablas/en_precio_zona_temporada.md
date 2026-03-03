# Tabla `en_precio_zona_temporada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_precio_zona_temporada | INT | No | ✓ |  |  |
| id_zona | INT | Sí |  |  |  |
| id_temporada | INT | Sí |  |  |  |
| valor_peso | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha | TIMESTAMP | No |  |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| tipo_vehiculo | VARCHAR | Sí |  |  |  |
| precio_fijo | VARCHAR | Sí |  |  |  |

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
| En_ABM_precio_zona_temporada2.frm | 507 | SELECT | consulta = "SELECT pzt.id_precio_zona_temporada, pzt.id_zona… |
| En_Carga_Precio_Zona_Temporada.frm | 1021 | SELECT | rs_EnArt.Open "SELECT * FROM en_precio_zona_temporada WHERE … |
| En_Carga_Precio_Zona_Temporada.frm | 1072 | SELECT | rs_EnArt.Open "SELECT * FROM en_precio_zona_temporada WHERE … |
| En_Carga_Precio_Zona_Temporada.frm | 1141 | SELECT | registro.Open "SELECT count(*) as TOTAL FROM en_precio_zona_… |
| En_Carga_Precio_Zona_Temporada.frm | 1163 | SELECT | registro.Open "SELECT count(*) as TOTAL FROM en_precio_zona_… |
| En_Carga_Precio_Zona_Temporada.frm | 1221 | SELECT | cargo_data_abm = "SELECT pzt.id_precio_zona_temporada, pzt.i… |
| En_ABM_precio_zona_temporada.frm | 521 | SELECT | 'SELECT pzt.id_precio_zona_temporada, pzt.id_zona, pzt.id_te… |
| En_ABM_precio_zona_temporada.frm | 534 | SELECT | " FROM  en_precio_zona_temporada pzt, erp_zona z, en_tempora… |
| En_Carga_Pesaje.frm | 6989 | SELECT | " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Pesaje.frm | 7216 | SELECT | '                " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Pesaje.frm | 7348 | SELECT | " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Vale.frm | 5714 | SELECT | " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Vale.frm | 6081 | SELECT | " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Vale.frm | 6284 | SELECT | '                " FROM en_precio_zona_temporada AS pz" & _ |
| En_Carga_Vale.frm | 6444 | SELECT | " FROM en_precio_zona_temporada AS pz" & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)