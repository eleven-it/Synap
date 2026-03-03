# Tabla `auditoria_general`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_auditoria_general | BIGINT | No | ✓ |  |  |
| tipo_proceso | VARCHAR | Sí |  |  |  |
| descripcion_proceso | VARCHAR | Sí |  |  |  |
| id_vendedor | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| id_usuario_supervisor | INT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |

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
| Funciones.bas | 9291 | SELECT | rs_consulta.Open "SELECT * FROM auditoria_general WHERE id_a… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)