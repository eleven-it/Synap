# Tabla `logi_gestion_renglon_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_logi_gestion_renglon_temp | DOUBLE | No | ✓ |  |  |
| id_cuentacliente | DOUBLE | Sí |  |  |  |
| id_stock | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| nombre_cliente_temp | VARCHAR | Sí |  |  |  |
| nro_comp_temp | VARCHAR | Sí |  |  |  |
| fecha_comp_temp | DATE | Sí |  |  |  |
| estado_ped_temp | VARCHAR | Sí |  |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| estado_temp | VARCHAR | Sí |  |  |  |

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
| Logi_Gestion2.frm | 4015 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion2.frm | 4028 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion2.frm | 4344 | SELECT | rs_existe.Open "SELECT id_stock FROM logi_gestion_renglon_te… |
| Logi_Gestion2.frm | 4358 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion2.frm | 4381 | SELECT | Data_RenglonA.RecordSource = "SELECT * FROM logi_gestion_ren… |
| Logi_Gestion2.frm | 4398 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion2.frm | 4403 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion2.frm | 4621 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp (id_stoc… |
| Logi_Gestion2.frm | 5097 | SELECT | '                conn.Execute "DELETE From logi_gestion_reng… |
| Logi_Gestion2.frm | 5097 | DELETE | '                conn.Execute "DELETE From logi_gestion_reng… |
| Logi_Gestion2.frm | 5174 | SELECT | '            conn.Execute "DELETE From logi_gestion_renglon_… |
| Logi_Gestion2.frm | 5174 | DELETE | '            conn.Execute "DELETE From logi_gestion_renglon_… |
| Logi_Gestion2.frm | 5208 | SELECT | '            rs_ultimo.Open "SELECT * FROM logi_gestion_reng… |
| Logi_Gestion2.frm | 5674 | SELECT | '    data_renglon_temp.RecordSource = "SELECT * FROM logi_ge… |
| Logi_Gestion2.frm | 5886 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp(id_stock… |
| Logi_Gestion2.frm | 5927 | SELECT | conn.Execute "DELETE From logi_gestion_renglon_temp where id… |
| Logi_Gestion2.frm | 5927 | DELETE | conn.Execute "DELETE From logi_gestion_renglon_temp where id… |
| Logi_Gestion2.frm | 7057 | JOIN | '                                                 "RIGHT JOI… |
| Logi_Gestion2.frm | 7408 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion2.frm | 10756 | JOIN | '"INNER JOIN logi_gestion_renglon_temp ON (logi_gestion_reng… |
| Logi_Gestion2.frm | 11144 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp (id_stoc… |
| Logi_Gestion.frm | 4244 | JOIN | "INNER JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 5036 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion.frm | 5049 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion.frm | 5365 | SELECT | rs_existe.Open "SELECT id_stock FROM logi_gestion_renglon_te… |
| Logi_Gestion.frm | 5379 | SELECT | "From logi_gestion_renglon_temp " & _ |
| Logi_Gestion.frm | 5402 | SELECT | Data_RenglonA.RecordSource = "SELECT * FROM logi_gestion_ren… |
| Logi_Gestion.frm | 5419 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 5424 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 5723 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp (id_stoc… |
| Logi_Gestion.frm | 6338 | SELECT | conn.Execute "DELETE From logi_gestion_renglon_temp WHERE Co… |
| Logi_Gestion.frm | 6338 | DELETE | conn.Execute "DELETE From logi_gestion_renglon_temp WHERE Co… |
| Logi_Gestion.frm | 6410 | SELECT | conn.Execute "DELETE From logi_gestion_renglon_temp WHERE id… |
| Logi_Gestion.frm | 6410 | DELETE | conn.Execute "DELETE From logi_gestion_renglon_temp WHERE id… |
| Logi_Gestion.frm | 6417 | SELECT | rs_ultimo.Open "SELECT * FROM logi_gestion_renglon_temp WHER… |
| Logi_Gestion.frm | 6998 | SELECT | '    data_renglon_temp.RecordSource = "SELECT * FROM logi_ge… |
| Logi_Gestion.frm | 7210 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp(id_stock… |
| Logi_Gestion.frm | 7251 | SELECT | conn.Execute "DELETE From logi_gestion_renglon_temp where id… |
| Logi_Gestion.frm | 7251 | DELETE | conn.Execute "DELETE From logi_gestion_renglon_temp where id… |
| Logi_Gestion.frm | 8589 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 8601 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 8927 | JOIN | "RIGHT JOIN logi_gestion_renglon_temp ON (logi_gestion_rengl… |
| Logi_Gestion.frm | 12122 | INSERT | conn.Execute "INSERT INTO logi_gestion_renglon_temp (id_stoc… |
| Principal.frm | 6118 | SELECT | conn.Execute "delete from logi_gestion_renglon_temp where id… |
| Principal.frm | 6118 | DELETE | conn.Execute "delete from logi_gestion_renglon_temp where id… |
| Principal.frm | 6184 | SELECT | conn.Execute "delete from logi_gestion_renglon_temp where id… |
| Principal.frm | 6184 | DELETE | conn.Execute "delete from logi_gestion_renglon_temp where id… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)