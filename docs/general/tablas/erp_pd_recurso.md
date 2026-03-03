# Tabla `erp_pd_recurso`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pd_recurso | INT | No | ✓ |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_articulo | INT | Sí |  |  |  |
| id_recurso_proyecto | INT | Sí |  |  |  |
| hora_inicio | TIME | Sí |  |  |  |
| hora_fin | TIME | Sí |  |  |  |
| cant_horas | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| tipo_recurso | VARCHAR | Sí |  |  |  |
| nombre_recurso | VARCHAR | Sí |  |  |  |
| coeficiente | DECIMAL | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| id_art_pre | INT | Sí |  |  |  |
| codigomovimiento_pre | INT | Sí |  |  |  |
| unidad_medida | VARCHAR | Sí |  |  |  |
| tipo_unidad_medida | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| dia_semana | VARCHAR | Sí |  |  |  |
| nro_semana | INT | Sí |  |  |  |
| year | INT | Sí |  |  |  |
| id_recurso | INT | Sí |  |  |  |
| cant_horas_planificada | DECIMAL | Sí |  |  |  |
| estado_recurso | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 2523 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_pd_recurso WHERE… |
| Erp_Carga_Parte_Diario.frm | 2562 | UPDATE | conn.Execute "UPDATE erp_pd_recurso SET Year=MID(YEARWEEK(er… |
| Erp_Carga_Parte_Diario.frm | 3009 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_pd_recurso WHERE… |
| Erp_Carga_Parte_Diario.frm | 3044 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_pd_recurso WHERE… |
| Erp_Carga_Parte_Diario.frm | 3059 | UPDATE | conn.Execute "UPDATE erp_pd_recurso SET Year=MID(YEARWEEK(er… |
| Erp_Carga_Parte_Diario.frm | 3321 | SELECT | '                                            "FROM erp_pd_re… |
| Erp_Carga_Parte_Diario.frm | 3329 | SELECT | '                                            "FROM erp_pd_re… |
| Erp_Carga_Parte_Diario.frm | 3707 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso WHERE id_pd_recurso… |
| Erp_Carga_Parte_Diario.frm | 3707 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso WHERE id_pd_recurso… |
| ConsultaComprobante.frm | 3069 | JOIN | " LEFT JOIN  erp_pd_recurso AS recu ON recu.`CodigoMovimient… |
| ConsultaComprobante.frm | 5022 | UPDATE | conn.Execute "UPDATE erp_pd_recurso SET anulado = 'Si' WHERE… |
| ConsultaComprobante.frm | 13490 | SELECT | rs_pd_recurso.Open "SELECT * FROM erp_pd_recurso WHERE erp_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2454 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_pd_recurso WHERE… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2489 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_pd_recurso WHERE… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2504 | UPDATE | conn.Execute "UPDATE erp_pd_recurso SET Year=MID(YEARWEEK(er… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2920 | SELECT | '                                            "FROM erp_pd_re… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2928 | SELECT | '                                            "FROM erp_pd_re… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3296 | SELECT | conn.Execute "DELETE FROM erp_pd_recurso WHERE id_pd_recurso… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3296 | DELETE | conn.Execute "DELETE FROM erp_pd_recurso WHERE id_pd_recurso… |
| Erp_Busqueda_PD.frm | 1158 | SELECT | data_pd_recurso.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Busqueda_PD.frm | 1168 | JOIN | " LEFT JOIN erp_pd_recurso AS rec ON (rec.`id_recurso_proyec… |
| Erp_Busqueda_PD.frm | 1174 | SELECT | '"FROM  `erp_pd_recurso` AS rec " & _ |
| Erp_Busqueda_PD.frm | 1185 | SELECT | data_pd_recurso.RecordSource = "SELECT * FROM erp_pd_recurso… |
| Erp_Busqueda_PD.frm | 1194 | JOIN | " LEFT JOIN erp_pd_recurso AS rec ON (rec.`id_recurso_proyec… |
| Erp_Costeo_Proyecto.frm | 1269 | SELECT | rs_parte_diario.Open "SELECT id_pd_recurso FROM erp_pd_recur… |
| Visualiza.bas | 8534 | SELECT | rs_pd_recurso.Open "SELECT * FROM erp_pd_recurso WHERE erp_p… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)