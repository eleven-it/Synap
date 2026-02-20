# Tabla `logi_gestion_comp_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_logi_gestion_comp_temp | DOUBLE | No | ✓ |  |  |
| CodigoMovimiento | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombre_cliente_temp | VARCHAR | Sí |  |  |  |
| nro_comp_temp | VARCHAR | Sí |  |  |  |
| fecha_comp_temp | DATE | Sí |  |  |  |
| estado_ped_temp | VARCHAR | Sí |  |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| estado_temp | VARCHAR | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| codigo_movimiento_fact | DOUBLE | Sí |  |  |  |
| id_caja_efectivo | DOUBLE | Sí |  |  |  |
| tot_peso | DOUBLE | Sí |  |  |  |
| tot_dolar | DOUBLE | Sí |  |  |  |
| cancelado | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| tot_gestion_rec | DOUBLE | Sí |  |  |  |
| saldo_gestion_rec | DOUBLE | Sí |  |  |  |
| detalle_temp | MEDIUMTEXT | Sí |  |  |  |

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
| Logi_Gestion2.frm | 3290 | SELECT | '            rs_comprobantes_temp.Open "SELECT id_logi_gesti… |
| Logi_Gestion2.frm | 4466 | SELECT | rs_existe.Open "SELECT CodigoMovimiento FROM logi_gestion_co… |
| Logi_Gestion2.frm | 4485 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion2.frm | 4540 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion2.frm | 4541 | SELECT | '"SELECT * FROM logi_gestion_comp_temp WHERE id_logi_gestion… |
| Logi_Gestion2.frm | 4602 | SELECT | 'DataComprobanteA.RecordSource = "SELECT * From logi_gestion… |
| Logi_Gestion2.frm | 5054 | SELECT | '            conn.Execute "DELETE From logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 5054 | DELETE | '            conn.Execute "DELETE From logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 5125 | SELECT | 'DataComprobanteA.RecordSource = "SELECT * From logi_gestion… |
| Logi_Gestion2.frm | 5213 | SELECT | '                conn.Execute "DELETE From logi_gestion_comp… |
| Logi_Gestion2.frm | 5213 | DELETE | '                conn.Execute "DELETE From logi_gestion_comp… |
| Logi_Gestion2.frm | 5217 | SELECT | '                'DataComprobanteA.RecordSource = "SELECT * … |
| Logi_Gestion2.frm | 5809 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 5822 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion2.frm | 5848 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 5867 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion2.frm | 5879 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion2.frm | 5889 | JOIN | "LEFT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_temp… |
| Logi_Gestion2.frm | 5896 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion2.frm | 5923 | SELECT | conn.Execute "DELETE From logi_gestion_comp_temp where id_us… |
| Logi_Gestion2.frm | 5923 | DELETE | conn.Execute "DELETE From logi_gestion_comp_temp where id_us… |
| Logi_Gestion2.frm | 9519 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 9526 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion2.frm | 9606 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 9639 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion2.frm | 9773 | SELECT | '                "From logi_gestion_comp_temp " & _ |
| Logi_Gestion2.frm | 9785 | SELECT | "From logi_gestion_comp_temp " & _ |
| Logi_Gestion2.frm | 10926 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion2.frm | 10931 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Facturacion_Ciclica.frm | 2549 | SELECT | 'DataClienteD.RecordSource = "SELECT * From logi_gestion_com… |
| Facturacion_Ciclica.frm | 2591 | SELECT | 'DataClienteD.RecordSource = "SELECT * From logi_gestion_com… |
| Logi_Gestion.frm | 3966 | JOIN | '                        "INNER JOIN logi_gestion_comp_temp … |
| Logi_Gestion.frm | 3978 | SELECT | rs_comprobantes_temp.Open "SELECT id_logi_gestion_comp_temp,… |
| Logi_Gestion.frm | 5488 | SELECT | rs_existe.Open "SELECT CodigoMovimiento FROM logi_gestion_co… |
| Logi_Gestion.frm | 5507 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion.frm | 5564 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion.frm | 5565 | SELECT | '"SELECT * FROM logi_gestion_comp_temp WHERE id_logi_gestion… |
| Logi_Gestion.frm | 5590 | SELECT | 'DataComprobanteA.RecordSource = "SELECT * From logi_gestion… |
| Logi_Gestion.frm | 5602 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion.frm | 5603 | SELECT | '"SELECT * FROM logi_gestion_comp_temp WHERE id_logi_gestion… |
| Logi_Gestion.frm | 5704 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion.frm | 6332 | SELECT | conn.Execute "DELETE From logi_gestion_comp_temp WHERE id_lo… |
| Logi_Gestion.frm | 6332 | DELETE | conn.Execute "DELETE From logi_gestion_comp_temp WHERE id_lo… |
| Logi_Gestion.frm | 6368 | SELECT | 'DataComprobanteA.RecordSource = "SELECT * From logi_gestion… |
| Logi_Gestion.frm | 6422 | SELECT | conn.Execute "DELETE From logi_gestion_comp_temp WHERE id_lo… |
| Logi_Gestion.frm | 6422 | DELETE | conn.Execute "DELETE From logi_gestion_comp_temp WHERE id_lo… |
| Logi_Gestion.frm | 6426 | SELECT | 'DataComprobanteA.RecordSource = "SELECT * From logi_gestion… |
| Logi_Gestion.frm | 6622 | SELECT | "From logi_gestion_comp_temp WHERE id_usuario= " & Principal… |
| Logi_Gestion.frm | 7133 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion.frm | 7146 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion.frm | 7172 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion.frm | 7191 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion.frm | 7203 | INSERT | conn.Execute "INSERT INTO logi_gestion_comp_temp (CodigoMovi… |
| Logi_Gestion.frm | 7213 | JOIN | "LEFT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_temp… |
| Logi_Gestion.frm | 7220 | SELECT | DataComprobanteA.RecordSource = "SELECT * From logi_gestion_… |
| Logi_Gestion.frm | 7247 | SELECT | conn.Execute "DELETE From logi_gestion_comp_temp where id_us… |
| Logi_Gestion.frm | 7247 | DELETE | conn.Execute "DELETE From logi_gestion_comp_temp where id_us… |
| Logi_Gestion.frm | 7984 | SELECT | " FROM logi_gestion_comp_temp WHERE logi_gestion_comp_temp.i… |
| Logi_Gestion.frm | 11173 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion.frm | 11180 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion.frm | 11257 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| Logi_Gestion.frm | 11304 | SELECT | "FROM logi_gestion_comp_temp " & _ |
| Logi_Gestion.frm | 11438 | SELECT | '                "From logi_gestion_comp_temp " & _ |
| Logi_Gestion.frm | 11450 | SELECT | "From logi_gestion_comp_temp " & _ |
| Logi_Gestion.frm | 12521 | JOIN | "RIGHT JOIN logi_gestion_comp_temp ON (logi_gestion_comp_tem… |
| ReciboCobro.frm | 8155 | SELECT | Logi_Gestion.DataComprobanteA.RecordSource = "SELECT * FROM … |
| ReciboCobro.frm | 8176 | SELECT | Logi_Gestion.DataComprobanteA.RecordSource = "SELECT * FROM … |
| Principal.frm | 6117 | SELECT | conn.Execute "delete from logi_gestion_comp_temp where id_us… |
| Principal.frm | 6117 | DELETE | conn.Execute "delete from logi_gestion_comp_temp where id_us… |
| Principal.frm | 6183 | SELECT | conn.Execute "delete from logi_gestion_comp_temp where id_us… |
| Principal.frm | 6183 | DELETE | conn.Execute "delete from logi_gestion_comp_temp where id_us… |
| Logi_GestionRec.frm | 1633 | UPDATE | conn.Execute "UPDATE logi_gestion_comp_temp " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)