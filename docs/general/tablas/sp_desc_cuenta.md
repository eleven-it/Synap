# Tabla `sp_desc_cuenta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sp_desc_cuenta | BIGINT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| id_sp_desc | BIGINT | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| codigo_movimiento_anul | BIGINT | Sí |  |  |  |
| punto_consumo | DOUBLE | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |

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
| Funciones.bas | 11550 | SELECT | " FROM sp_desc_cuenta " & _ |
| Funciones.bas | 11923 | SELECT | rs_sp_desc_cuenta.Open "SELECT * FROM sp_desc_cuenta WHERE i… |
| Funciones.bas | 11975 | SELECT | rs_sp_desc_cuenta.Open "SELECT * FROM sp_desc_cuenta WHERE i… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)