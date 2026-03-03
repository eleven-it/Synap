# Tabla `erp_pd_recurso_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_erp_pd_temp | INT | No | ✓ |  |  |
| id_usuario_rh | INT | Sí |  |  |  |
| id_recurso_proyecto | INT | Sí |  |  |  |
| id_articulo | INT | Sí |  |  |  |
| nombre_recurso | VARCHAR | Sí |  |  |  |
| tipo_recurso | VARCHAR | Sí |  |  |  |
| nombre_recurso_pd | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| desde | TIME | Sí |  |  |  |
| hasta | TIME | Sí |  |  |  |
| cant_horas | DECIMAL | Sí |  |  |  |
| id_tarea | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| coeficiente | DOUBLE | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| id_pd_recurso | INT | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| id_art_pre | INT | Sí |  |  |  |
| codigomovimiento_pre | INT | Sí |  |  |  |
| unidad_medida | VARCHAR | Sí |  |  |  |
| tipo_unidad_medida | VARCHAR | Sí |  |  |  |
| dia_semana | VARCHAR | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 3372 | SELECT | rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_temp… |
| Erp_Carga_Parte_Diario.frm | 3384 | SELECT | 'rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_tem… |
| Erp_Carga_Parte_Diario.frm | 3392 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3473 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3497 | SELECT | rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_temp… |
| Erp_Carga_Parte_Diario.frm | 3507 | SELECT | 'rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_tem… |
| Erp_Carga_Parte_Diario.frm | 3520 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3589 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3709 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Erp_Carga_Parte_Diario.frm | 3709 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Erp_Carga_Parte_Diario.frm | 3717 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3733 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Erp_Carga_Parte_Diario.frm | 3733 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Erp_Carga_Parte_Diario.frm | 3736 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3869 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 4321 | SELECT | '                       "FROM  `erp_pd_recurso_temp` AS rec … |
| Erp_Carga_Parte_Diario.frm | 4386 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_usuar… |
| Erp_Carga_Parte_Diario.frm | 4386 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_usuar… |
| ConsultaComprobante.frm | 13468 | SELECT | conn.Execute "DELETE  FROM erp_pd_recurso_temp WHERE id_usua… |
| ConsultaComprobante.frm | 13468 | DELETE | conn.Execute "DELETE  FROM erp_pd_recurso_temp WHERE id_usua… |
| ConsultaComprobante.frm | 13492 | SELECT | rs_pd_recurso_temp.Open "SELECT * FROM erp_pd_recurso_temp W… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2973 | SELECT | rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_temp… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2983 | SELECT | 'rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_tem… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2991 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3074 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3098 | SELECT | rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_temp… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3108 | SELECT | 'rs_parte_diario_temp.Open "SELECT * FROM erp_pd_recurso_tem… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3121 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3193 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3298 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3298 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3306 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3322 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3322 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_erp_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3325 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3446 | SELECT | Data_Parte_Temp.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3869 | SELECT | '                       "FROM  `erp_pd_recurso_temp` AS rec … |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3931 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_usuar… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3931 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso_temp WHERE id_usuar… |
| Principal.frm | 6084 | SELECT | conn.Execute "delete from erp_pd_recurso_temp where id_usuar… |
| Principal.frm | 6084 | DELETE | conn.Execute "delete from erp_pd_recurso_temp where id_usuar… |
| Principal.frm | 6150 | SELECT | conn.Execute "delete from erp_pd_recurso_temp where id_usuar… |
| Principal.frm | 6150 | DELETE | conn.Execute "delete from erp_pd_recurso_temp where id_usuar… |
| Visualiza.bas | 8532 | SELECT | conn.Execute "DELETE  FROM erp_pd_recurso_temp WHERE id_usua… |
| Visualiza.bas | 8532 | DELETE | conn.Execute "DELETE  FROM erp_pd_recurso_temp WHERE id_usua… |
| Visualiza.bas | 8592 | SELECT | Visualiza_Erp_Carga_Parte_Diario.Data_Parte_Temp.RecordSourc… |
| Visualiza.bas | 8638 | SELECT | Visualiza_Erp_Carga_Parte_Diario.Data_Parte_Temp.RecordSourc… |
| Visualiza.bas | 8648 | SELECT | '                            "FROM  `erp_pd_recurso_temp` AS… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)