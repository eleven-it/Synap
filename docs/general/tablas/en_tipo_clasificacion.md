# Tabla `en_tipo_clasificacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tipo_clasificacion | BIGINT | No | ✓ |  |  |
| IDArt | BIGINT | Sí |  |  |  |
| tipo_clasificacion | VARCHAR | Sí |  |  |  |
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
| En_ABM_tipo_clasificacion.frm | 462 | SELECT | consulta = "SELECT t.id_tipo_clasificacion, t.IDArt, a.Nombr… |
| En_Carga_Clasificacion_Pesaje.frm | 1085 | SELECT | " FROM en_tipo_clasificacion AS cl" & _ |
| En_Carga_Clasificacion_Pesaje.frm | 1091 | SELECT | " FROM en_tipo_clasificacion AS cl" & _ |
| En_Carga_Clasificacion_Pesaje.frm | 1504 | SELECT | " FROM en_tipo_clasificacion AS cl" & _ |
| En_Carga_Tipo_Clasificacion.frm | 526 | SELECT | rs_banco.Open "SELECT * FROM en_tipo_clasificacion WHERE  id… |
| En_Carga_Tipo_Clasificacion.frm | 548 | SELECT | En_ABM_tipo_clasificacion.DataClasificacion.RecordSource = "… |
| En_Carga_Tipo_Clasificacion.frm | 570 | SELECT | rs_banco.Open "SELECT * FROM en_tipo_clasificacion WHERE id_… |
| En_Carga_Tipo_Clasificacion.frm | 590 | SELECT | En_ABM_tipo_clasificacion.DataClasificacion.RecordSource = "… |
| En_Carga_Tipo_Clasificacion.frm | 782 | SELECT | registro.Open "SELECT count(*) as TOTAL FROM en_tipo_clasifi… |
| En_Carga_Tipo_Clasificacion.frm | 804 | SELECT | registro.Open "SELECT count(*) as TOTAL FROM en_tipo_clasifi… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)