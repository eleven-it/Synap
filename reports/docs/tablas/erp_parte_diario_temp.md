# Tabla `erp_parte_diario_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_parte_diario | INT | No |  |  |  |
| fecha | DATE | Sí |  |  |  |
| fecha_carga | DATE | Sí |  |  |  |
| nro_ot_cliente | VARCHAR | Sí |  |  |  |
| nro_parte_diario | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_tarea | INT | Sí |  |  |  |
| detalle | TEXT | Sí |  |  |  |
| equipo | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| NroCompBusq | INT | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| adjunto | VARCHAR | Sí |  |  |  |
| id_parte_diario_temp | INT | No | ✓ |  |  |
| Seleccionado | CHAR | Sí |  |  |  |
| id_usuario_temp | DOUBLE | Sí |  |  |  |
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
| Erp_Busqueda_PD.frm | 1321 | INSERT | '    conn.Execute "INSERT INTO erp_parte_diario_temp (id_par… |
| Erp_Busqueda_PD.frm | 1340 | SELECT | data_pd.RecordSource = "SELECT erp_parte_diario_temp.*,erp_z… |
| Erp_Busqueda_PD.frm | 1368 | SELECT | data_pd.RecordSource = "SELECT erp_parte_diario_temp.*,erp_z… |
| Erp_Busqueda_PD.frm | 1394 | SELECT | data_pd.RecordSource = "SELECT erp_parte_diario_temp.*,erp_z… |
| Erp_Busqueda_PD.frm | 1420 | SELECT | '    data_pd.RecordSource = "SELECT * FROM erp_parte_diario_… |
| Erp_Busqueda_PD.frm | 1429 | SELECT | '        data_pd.RecordSource = "SELECT * FROM erp_parte_dia… |
| Erp_Busqueda_PD.frm | 1481 | SELECT | '            data_pd.RecordSource = "SELECT * from erp_parte… |
| Erp_Busqueda_PD.frm | 1555 | INSERT | conn.Execute "INSERT INTO erp_parte_diario_temp (id_parte_di… |
| Erp_Busqueda_PD.frm | 1612 | SELECT | conn.Execute "delete from erp_parte_diario_temp where id_usu… |
| Erp_Busqueda_PD.frm | 1612 | DELETE | conn.Execute "delete from erp_parte_diario_temp where id_usu… |
| Principal.frm | 6082 | SELECT | conn.Execute "delete from erp_parte_diario_temp where id_usu… |
| Principal.frm | 6082 | DELETE | conn.Execute "delete from erp_parte_diario_temp where id_usu… |
| Principal.frm | 6148 | SELECT | conn.Execute "delete from erp_parte_diario_temp where id_usu… |
| Principal.frm | 6148 | DELETE | conn.Execute "delete from erp_parte_diario_temp where id_usu… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)