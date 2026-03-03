# Tabla `crm_llamada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_llamada | DOUBLE | No | ✓ |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_cliente_potencial | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| descripcion | VARCHAR | Sí |  |  |  |
| fecha_llamada | TIMESTAMP | No |  |  |  |
| desc_requerimiento | MEDIUMTEXT | Sí |  |  |  |
| fecha_vto_llamada | DATETIME | Sí |  |  |  |
| id_vendedor | DOUBLE | Sí |  |  |  |
| tipo_cli | VARCHAR | Sí |  |  |  |
| fecha_prox_llamada | DATE | Sí |  |  |  |
| hora_prox_llamada | TIME | Sí |  |  |  |
| desc_accion | MEDIUMTEXT | Sí |  |  |  |
| origen | VARCHAR | Sí |  |  |  |
| llamada_efectuada | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| motivo | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| importancia | VARCHAR | Sí |  |  |  |
| envia_mail | VARCHAR | Sí |  |  |  |
| id_crm_cierre_tarea | BIGINT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_cierre_tarea | crm_llamada | Crm_CierreLlamada.frm | 483 | sql_motivo = "SELECT  c.id_crm_cierre_tarea, c.motivo , l.id_llamada FROM crm_ci… |
| crm_pre_llamada | crm_llamada | Crm_CargaLlamada.frm | 3002 | sql_llamada = "SELECT * FROM crm_pre_llamada p INNER JOIN crm_llamada c ON (c.id… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Crm_CierreLlamada.frm | 384 | SELECT | sql_verificacion = "SELECT id_llamada, id_crm_cierre_tarea F… |
| Crm_CierreLlamada.frm | 395 | UPDATE | sql_inserta = "UPDATE crm_llamada SET id_crm_cierre_tarea = … |
| Crm_CierreLlamada.frm | 405 | INSERT | 'sql_inserta = "INSERT INTO crm_llamada (id_llamada, id_crm_… |
| Crm_CierreLlamada.frm | 467 | SELECT | 'sql_estado = "SELECT  id_llamada, estado FROM crm_llamada W… |
| Crm_CierreLlamada.frm | 483 | JOIN | sql_motivo = "SELECT  c.id_crm_cierre_tarea, c.motivo , l.id… |
| trz_trazabilidad.frm | 2810 | JOIN | sql_rc = sql_rc & "INNER JOIN crm_llamada as cl ON (cpl.id_l… |
| trz_trazabilidad.frm | 3244 | JOIN | sql_rc = sql_rc & "INNER JOIN crm_llamada as cl ON (cpl.id_l… |
| Crm_CargaLlamada.frm | 2411 | INSERT | sql_inserta = "INSERT INTO crm_llamada (" & varI & ", fecha_… |
| Crm_CargaLlamada.frm | 2567 | SELECT | '        rs_datos.Open "SELECT  CONVERT( c.hora_prox_llamada… |
| Crm_CargaLlamada.frm | 3002 | JOIN | sql_llamada = "SELECT * FROM crm_pre_llamada p INNER JOIN cr… |
| Crm_AbmLlamada.frm | 672 | SELECT | "FROM crm_llamada " & _ |
| Crm_AbmLlamada.frm | 906 | SELECT | '                                   "FROM crm_llamada " & _ |
| Crm_AbmLlamada.frm | 920 | SELECT | '                                   "FROM crm_llamada " & _ |
| Crm_AbmLlamada.frm | 937 | SELECT | '                                       "FROM crm_llamada " … |
| Crm_AbmLlamada.frm | 949 | SELECT | '                                   "FROM crm_llamada " & _ |
| Crm_Presupuesto_Llamada.frm | 850 | SELECT | Sql = Sql & " FROM crm_llamada " |
| Principal.frm | 8493 | SELECT | rs_mensaje.Open "SELECT * FROM crm_llamada " & _ |
| Visualiza.bas | 8753 | SELECT | sql_llamada = sql_llamada & " From crm_llamada" |
| Funciones.bas | 8285 | SELECT | sql_rc = "SELECT * FROM crm_llamada WHERE id_llamada = " & r… |
| Funciones.bas | 13122 | SELECT | rs_datos.Open "SELECT CONVERT( c.hora_prox_llamada ,time) as… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)