# Tabla `cot`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cot | BIGINT | No | ✓ |  |  |
| nro_cot_interno | VARCHAR | Sí |  |  |  |
| nro_cot_interno_busq | DOUBLE | Sí |  |  |  |
| nro_cot_webservice | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |
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
| Cot.bas | 1230 | INSERT | conn.Execute "INSERT INTO cot " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)