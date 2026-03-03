# Tabla `erp_calidad_registro`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_observacion | INT | No | ✓ |  |  |
| fecha_observacion | DATE | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| origen | VARCHAR | Sí |  |  |  |
| clase | VARCHAR | Sí |  |  |  |
| condicion | VARCHAR | Sí |  |  |  |
| ubicacion | VARCHAR | Sí |  |  |  |
| descripcion | TEXT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario_accion | INT | Sí |  |  |  |
| como_accion | TEXT | Sí |  |  |  |
| cuando_accion | DATE | Sí |  |  |  |
| analisis_causa | TEXT | Sí |  |  |  |
| ap_correctiva | VARCHAR | Sí |  |  |  |
| id_usuario_correctiva | INT | Sí |  |  |  |
| como_correctiva | TEXT | Sí |  |  |  |
| cuando_correctiva | DATE | Sí |  |  |  |
| id_usuario_eficacia | INT | Sí |  |  |  |
| como_eficacia | TEXT | Sí |  |  |  |
| cuando_eficacia | DATE | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| id_usuario_responsable | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| fecha_cierre | DATE | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |

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
| Erp_Carga_Observaciones.frm | 1679 | SELECT | rs_observacion.Open "SELECT * FROM erp_calidad_registro WHER… |
| Erp_Carga_Observaciones.frm | 1767 | SELECT | Erp_ABM_Observaciones.data_observaciones.RecordSource = "SEL… |
| Erp_Carga_Observaciones.frm | 1806 | SELECT | rs_observacion.Open "SELECT * FROM erp_calidad_registro WHER… |
| Erp_ABM_Observaciones.frm | 850 | SELECT | data_observaciones.RecordSource = "SELECT erp_calidad_regist… |
| Erp_ABM_Observaciones.frm | 900 | SELECT | " FROM erp_calidad_registro " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)