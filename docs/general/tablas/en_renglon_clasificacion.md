# Tabla `en_renglon_clasificacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_renglon_clasifica | BIGINT | No | ✓ |  |  |
| tipo_clasificacion | VARCHAR | Sí |  |  |  |
| id_tipo_clasificacion | BIGINT | Sí |  |  |  |
| valor_tipo_clasificacion | DECIMAL | Sí |  |  |  |
| por_tipo_clasificacion | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_clasificacion | BIGINT | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |

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
| En_Carga_Clasificacion_Pesaje.frm | 1069 | SELECT | data_item_clasificacion_temp.RecordSource = "SELECT * FROM e… |
| En_Carga_Clasificacion_Pesaje.frm | 1136 | UPDATE | conn.Execute "UPDATE en_renglon_clasificacion AS rc" & _ |
| En_Carga_Clasificacion_Pesaje.frm | 1146 | SELECT | rs_renglon_clasificacion.Open "SELECT * FROM en_renglon_clas… |
| En_Carga_Clasificacion_Pesaje.frm | 1254 | SELECT | rs_renglon.Open "SELECT * FROM en_renglon_clasificacion WHER… |
| En_Carga_Clasificacion_Pesaje.frm | 1324 | SELECT | conn.Execute "DELETE FROM en_renglon_clasificacion WHERE id_… |
| En_Carga_Clasificacion_Pesaje.frm | 1324 | DELETE | conn.Execute "DELETE FROM en_renglon_clasificacion WHERE id_… |
| En_Carga_Clasificacion_Pesaje.frm | 1511 | SELECT | conn.Execute "DELETE FROM en_renglon_clasificacion WHERE id_… |
| En_Carga_Clasificacion_Pesaje.frm | 1511 | DELETE | conn.Execute "DELETE FROM en_renglon_clasificacion WHERE id_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)