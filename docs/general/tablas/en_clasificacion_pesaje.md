# Tabla `en_clasificacion_pesaje`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_clasificacion | BIGINT | No | ✓ |  |  |
| id_pesaje | BIGINT | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| observacion | TEXT | Sí |  |  |  |
| codmov_pesaje | BIGINT | Sí |  |  |  |

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
| En_Carga_Clasificacion_Pesaje.frm | 1123 | SELECT | rs_clasificacion.Open "SELECT * FROM en_clasificacion_pesaje… |
| En_Carga_Clasificacion_Pesaje.frm | 1133 | SELECT | rs_clasificacion.Open "SELECT * FROM en_clasificacion_pesaje… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)