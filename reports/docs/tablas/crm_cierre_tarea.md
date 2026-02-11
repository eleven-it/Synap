# Tabla `crm_cierre_tarea`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_crm_cierre_tarea | BIGINT | No | ✓ |  |  |
| motivo | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_cierre_tarea | crm_llamada | Crm_CierreLlamada.frm | 483 | sql_motivo = "SELECT  c.id_crm_cierre_tarea, c.motivo , l.id_llamada FROM crm_ci… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Crm_CierreLlamada.frm | 446 | SELECT | DataCierre.RecordSource = "SELECT * FROM crm_cierre_tarea; " |
| Crm_CierreLlamada.frm | 483 | SELECT | sql_motivo = "SELECT  c.id_crm_cierre_tarea, c.motivo , l.id… |
| Configuracion_Adicional2.frm | 4468 | SELECT | '                    Permisos_Complejos 126, "motivo", "SELE… |
| Crm_CargaMotivoCierre.frm | 202 | INSERT | conn.Execute "INSERT INTO crm_cierre_tarea (motivo) VALUES (… |
| Crm_CargaMotivoCierre.frm | 205 | UPDATE | conn.Execute "UPDATE crm_cierre_tarea SET " & _ |
| trz_trazabilidad.frm | 2811 | JOIN | sql_rc = sql_rc & "INNER JOIN crm_cierre_tarea as cct ON (cl… |
| Crm_CargaLlamada.frm | 3265 | SELECT | DataCierre.RecordSource = "SELECT * FROM crm_cierre_tarea; " |
| CargaPermiso_Sistema_Puesto.frm | 3435 | SELECT | sql_adicional = " , COALESCE((SELECT crm.motivo FROM  crm_ci… |
| CargaPermiso_Sistema_Puesto.frm | 3838 | SELECT | Permisos_Complejos 126, "motivo", "SELECT * FROM crm_cierre_… |
| CargaPermiso_Sistema_Puesto.frm | 3841 | SELECT | '                    CargaPermiso_Sistema_Puesto_Valor.DataP… |
| Crm_Info.frm | 1454 | SELECT | DataCierre.RecordSource = "SELECT * FROM crm_cierre_tarea ;" |
| Configuracion_Adicional.frm | 4711 | SELECT | '                    Permisos_Complejos 126, "motivo", "SELE… |
| Crm_AbmMotivoCierre.frm | 383 | SELECT | "FROM crm_cierre_tarea " & _ |
| Crm_AbmMotivoCierre.frm | 409 | SELECT | "FROM crm_cierre_tarea  " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)