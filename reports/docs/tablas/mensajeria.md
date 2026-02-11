# Tabla `mensajeria`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_mensaje | DOUBLE | No | ✓ |  |  |
| id_usuario_origen | INT | Sí |  |  |  |
| id_usuario_destino | INT | Sí |  |  |  |
| fecha_escritura | TIMESTAMP | No |  |  |  |
| fecha_lectura | VARCHAR | Sí |  |  |  |
| importancia_mensaje | VARCHAR | Sí |  |  |  |
| asunto_mensaje | VARCHAR | Sí |  |  |  |
| texto_mensaje | MEDIUMTEXT | Sí |  |  |  |
| estado_mensaje | VARCHAR | Sí |  |  |  |
| tipo_mensaje | VARCHAR | Sí |  |  |  |
| adjunto | VARCHAR | Sí |  |  |  |
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
| mensaj_carga.frm | 601 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_mensaje =… |
| mensaj_carga.frm | 648 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_mensaje =… |
| mensaj_abm.frm | 565 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_mensaje =… |
| mensaj_abm.frm | 607 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 621 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 639 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 654 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 674 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 688 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 706 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 721 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 818 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 832 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 1031 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 1049 | SELECT | data_mensaje.RecordSource = "SELECT mensajeria.*,usuario_ori… |
| mensaj_abm.frm | 1162 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_mensaje =… |
| Principal.frm | 8454 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_usuario_d… |
| Principal.frm | 8471 | SELECT | rs_mensaje.Open "SELECT * FROM mensajeria WHERE id_usuario_d… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)