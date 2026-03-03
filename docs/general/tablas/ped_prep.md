# Tabla `ped_prep`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ped_prep | DOUBLE | No | ✓ |  |  |
| CodigoMovimiento_prep | DOUBLE | Sí |  |  |  |
| id_responsable | DOUBLE | Sí |  |  |  |
| ped_numeracion | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| total_peso_actual | DOUBLE | Sí |  |  |  |
| ruta | VARCHAR | Sí |  |  |  |
| vehiculo | VARCHAR | Sí |  |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |

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
| Pedido_prep_consulta.frm | 1444 | SELECT | '    DataNro.RecordSource = "SELECT * FROM ped_prep " & _ |
| Pedido_prep_consulta.frm | 1451 | SELECT | ''    DataNro.RecordSource = "SELECT * FROM ped_prep " & _ |
| Pedido_prep_consulta.frm | 1639 | SELECT | "From ped_prep " & _ |
| Pedido_prep_consulta.frm | 1685 | SELECT | '                                    " CONCAT(logi_unidad.no… |
| Pedido_prep_consulta.frm | 1701 | SELECT | '                                        "From ped_prep " & … |
| Pedido_prep_consulta.frm | 1719 | SELECT | '            DataNro.RecordSource = "SELECT * FROM ped_prep … |
| Pedido_prep_consulta.frm | 1734 | SELECT | '                                    "From ped_prep " & _ |
| Pedido_prep_consulta.frm | 1750 | SELECT | " CONCAT(logi_unidad.nombre_unidad, ' - ' ,logi_unidad.paten… |
| Pedido_prep_consulta.frm | 1765 | SELECT | DataNro.RecordSource = "SELECT CAST(SUBSTRING(ped_prep.NroCo… |
| Pedido_prep_consulta.frm | 1792 | SELECT | DataDetalle.RecordSource = "SELECT * from ped_prep WHERE " &… |
| Pedido_prep_consulta.frm | 1935 | UPDATE | '    conn.Execute "UPDATE ped_prep " & _ |
| Pedido_prep_consulta.frm | 1970 | SELECT | "FROM ped_prep as r,(SELECT @curRank := '')as p " & _ |
| Pedido_prep_consulta.frm | 1975 | SELECT | "From ped_prep " & _ |
| Pedido_prep_consulta.frm | 2045 | SELECT | '                conn.Execute "delete from ped_prep where pe… |
| Pedido_prep_consulta.frm | 2045 | DELETE | '                conn.Execute "delete from ped_prep where pe… |
| Pedido_prep_consulta.frm | 2048 | UPDATE | conn.Execute "UPDATE ped_prep " & _ |
| Stock_Control.frm | 2070 | SELECT | " FROM ped_prep " & _ |
| Stock_Control.frm | 2085 | SELECT | " FROM ped_prep " & _ |
| Pedido_prep.frm | 3453 | INSERT | '        conn.Execute "INSERT INTO ped_prep (CodigoMovimient… |
| Pedido_prep.frm | 3457 | SELECT | '                       "NOT IN(SELECT ped_prep.ped_numeraci… |
| Pedido_prep.frm | 3461 | INSERT | '         conn.Execute "INSERT INTO ped_prep (CodigoMovimien… |
| Pedido_prep.frm | 3465 | SELECT | '                       "NOT IN(SELECT ped_prep.ped_numeraci… |
| Pedido_prep.frm | 3469 | INSERT | conn.Execute "INSERT INTO ped_prep (CodigoMovimiento_prep, i… |
| Pedido_prep.frm | 3473 | SELECT | "NOT IN(SELECT ped_prep.ped_numeracion From ped_prep " & _ |
| Pedido_prep.frm | 3481 | UPDATE | '        UPDATE ped_prep a |
| Pedido_prep.frm | 3489 | UPDATE | conn.Execute "UPDATE ped_prep " & _ |
| Pedido_prep.frm | 3663 | INSERT | conn.Execute "INSERT INTO ped_prep (CodigoMovimiento_prep, i… |
| Pedido_prep.frm | 3680 | SELECT | rs_ped_prep.Open "select * from ped_prep where CodigoMovimie… |
| Pedido_prep.frm | 4180 | SELECT | "From ped_prep " & _ |
| Pedido_prep.frm | 4606 | SELECT | conn.Execute "delete From ped_prep where ped_numeracion = " … |
| Pedido_prep.frm | 4606 | DELETE | conn.Execute "delete From ped_prep where ped_numeracion = " … |
| Pedido_prep.frm | 4930 | JOIN | '    /*LEFT JOIN ped_prep ON (ped_prep.ped_numeracion = comp… |
| Pedido_prep.frm | 4934 | JOIN | '            LosLeft = " LEFT JOIN ped_prep ON (ped_prep.ped… |
| Pedido_Avanzado.frm | 9912 | JOIN | LosLeft = " LEFT JOIN ped_prep ON (ped_prep.ped_numeracion =… |
| Principal.frm | 11126 | SELECT | rs_informe.Open "SELECT * FROM ped_prep WHERE ped_prep.Codig… |
| Funciones.bas | 3683 | SELECT | "From ped_prep " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)