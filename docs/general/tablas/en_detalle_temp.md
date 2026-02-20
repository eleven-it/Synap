# Tabla `en_detalle_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_detalle_temp | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_en_detalle_abm_temp | DOUBLE | Sí |  |  |  |
| desc_detalle_temp | MEDIUMTEXT | Sí |  |  |  |
| fecha_en_detalle_temp | DATE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_usuario_temp | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombreReferencia_temp | VARCHAR | Sí |  |  |  |
| NombreUsuario_temp | VARCHAR | Sí |  |  |  |
| estado_en_detalle_temp | VARCHAR | Sí |  |  |  |
| IDArtE_temp | DOUBLE | Sí |  |  |  |
| id_proveedor_temp | DOUBLE | Sí |  |  |  |
| id_gasto_temp | DOUBLE | Sí |  |  |  |
| monto_temp | DECIMAL | Sí |  |  |  |
| id_en_abm_temp | DOUBLE | Sí |  |  |  |

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
| En_GeneraOE.frm | 2149 | SELECT | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_detall… |
| En_GeneraOE.frm | 2149 | DELETE | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_detall… |
| En_GeneraOE.frm | 2530 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| En_GeneraOE.frm | 2530 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| En_GeneraOE.frm | 2533 | SELECT | '    conn.Execute "delete from en_detalle_temp where id_usua… |
| En_GeneraOE.frm | 2533 | DELETE | '    conn.Execute "delete from en_detalle_temp where id_usua… |
| En_GeneraOE.frm | 2803 | SELECT | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_abm_te… |
| En_GeneraOE.frm | 2803 | DELETE | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_abm_te… |
| En_GeneraOE.frm | 2870 | SELECT | "FROM en_detalle_temp " & _ |
| En_GeneraOE.frm | 2917 | SELECT | '                                    "From en_detalle_temp "… |
| En_GeneraOE.frm | 2936 | SELECT | "From en_detalle_temp " & _ |
| En_GeneraOE.frm | 3364 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| En_GeneraOE.frm | 3449 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| En_GeneraOE.frm | 3505 | SELECT | rs_DetTemp.Open "SELECT * from en_detalle_temp WHERE id_usua… |
| En_GeneraOE.frm | 4757 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| En_GestionOE.frm | 1485 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| En_GestionOE.frm | 1485 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| En_GestionOE.frm | 1489 | SELECT | '            conn.Execute "delete from en_detalle_temp where… |
| En_GestionOE.frm | 1489 | DELETE | '            conn.Execute "delete from en_detalle_temp where… |
| En_GestionOE.frm | 1745 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| En_GestionOE.frm | 1788 | SELECT | '                Visualiza_En_GeneraOE.DataRef.RecordSource … |
| En_GestionOE.frm | 1793 | SELECT | '                Visualiza_En_GeneraOE.DataRef.RecordSource … |
| En_GestionOE.frm | 1807 | SELECT | "FROM en_detalle_temp " & _ |
| En_GestionOE.frm | 1815 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| Visualiza_En_GeneraOE.frm | 2272 | SELECT | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_detall… |
| Visualiza_En_GeneraOE.frm | 2272 | DELETE | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_detall… |
| Visualiza_En_GeneraOE.frm | 2650 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| Visualiza_En_GeneraOE.frm | 2650 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| Visualiza_En_GeneraOE.frm | 2653 | SELECT | '    conn.Execute "delete from en_detalle_temp where id_usua… |
| Visualiza_En_GeneraOE.frm | 2653 | DELETE | '    conn.Execute "delete from en_detalle_temp where id_usua… |
| Visualiza_En_GeneraOE.frm | 2967 | SELECT | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_abm_te… |
| Visualiza_En_GeneraOE.frm | 2967 | DELETE | conn.Execute "DELETE FROM en_detalle_temp WHERE id_en_abm_te… |
| Visualiza_En_GeneraOE.frm | 3061 | SELECT | "FROM en_detalle_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3130 | SELECT | "From en_detalle_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3149 | SELECT | "FROM en_detalle_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3157 | SELECT | "From en_detalle_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3171 | SELECT | "From en_detalle_temp " & _ |
| Visualiza_En_GeneraOE.frm | 3197 | SELECT | '                                    "From en_detalle_temp "… |
| Visualiza_En_GeneraOE.frm | 4495 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| Visualiza_En_GeneraOE.frm | 4603 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| Visualiza_En_GeneraOE.frm | 4665 | SELECT | rs_DetTemp.Open "SELECT * from en_detalle_temp WHERE id_usua… |
| Visualiza_En_GeneraOE.frm | 5772 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_abm_tem… |
| En_CargaOE_Ref.frm | 1324 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1363 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1398 | SELECT | En_GeneraOE.DataRef.RecordSource = "SELECT * FROM en_detalle… |
| En_CargaOE_Ref.frm | 1443 | SELECT | En_GeneraOE.DataRef.RecordSource = "SELECT * FROM en_detalle… |
| En_CargaOE_Ref.frm | 1493 | SELECT | En_GeneraOE.DataRef.RecordSource = "SELECT * FROM en_detalle… |
| En_CargaOE_Ref.frm | 1527 | INSERT | conn.Execute "INSERT INTO en_detalle_temp (codigo_movimiento… |
| En_CargaOE_Ref.frm | 1540 | UPDATE | conn.Execute "UPDATE en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1569 | SELECT | En_GeneraOE.DataRef.RecordSource = "SELECT * FROM en_detalle… |
| En_CargaOE_Ref.frm | 1596 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1635 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1670 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| En_CargaOE_Ref.frm | 1715 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| En_CargaOE_Ref.frm | 1739 | SELECT | '                            rs_ref.Open "SELECT * FROM en_d… |
| En_CargaOE_Ref.frm | 1792 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| En_CargaOE_Ref.frm | 1826 | INSERT | conn.Execute "INSERT INTO en_detalle_temp (codigo_movimiento… |
| En_CargaOE_Ref.frm | 1839 | UPDATE | conn.Execute "UPDATE en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 1868 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| En_CargaOE_Ref.frm | 2032 | SELECT | "FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 2089 | SELECT | "FROM en_detalle_temp " & _ |
| En_CargaOE_Ref.frm | 2257 | SELECT | rs_Ref.Open "SELECT id_en_detalle_abm_temp, estado_en_detall… |
| En_CargaOE_Ref.frm | 2263 | SELECT | rs_Ref.Open "SELECT id_en_detalle_abm_temp, estado_en_detall… |
| En_CargaOE_Ref.frm | 2278 | SELECT | rs_Ref.Open "SELECT id_en_detalle_abm_temp, estado_en_detall… |
| En_CargaOE_Ref.frm | 2284 | SELECT | rs_Ref.Open "SELECT id_en_detalle_abm_temp, estado_en_detall… |
| En_CargaOE_Ref.frm | 2325 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_detalle… |
| En_CargaOE_Ref.frm | 2340 | JOIN | "LEFT JOIN en_detalle_temp ON (en_detalle_temp.id_en_detalle… |
| En_CargaOE_Ref.frm | 2374 | SELECT | "FROM en_detalle_temp " & _ |
| Principal.frm | 6111 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario =… |
| Principal.frm | 6111 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario =… |
| Principal.frm | 6177 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario =… |
| Principal.frm | 6177 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario =… |
| Visualiza.bas | 8055 | SELECT | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| Visualiza.bas | 8055 | DELETE | conn.Execute "delete from en_detalle_temp where id_usuario_t… |
| Visualiza.bas | 8059 | SELECT | '            conn.Execute "delete from en_detalle_temp where… |
| Visualiza.bas | 8059 | DELETE | '            conn.Execute "delete from en_detalle_temp where… |
| Visualiza.bas | 8322 | SELECT | Visualiza_En_GeneraOE.DataRef.RecordSource = "SELECT * FROM … |
| Visualiza.bas | 8365 | SELECT | '                Visualiza_En_GeneraOE.DataRef.RecordSource … |
| Visualiza.bas | 8369 | SELECT | '                Visualiza_En_GeneraOE.DataRef.RecordSource … |
| Visualiza.bas | 8383 | SELECT | "FROM en_detalle_temp " & _ |
| … | … | … | *(1 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)