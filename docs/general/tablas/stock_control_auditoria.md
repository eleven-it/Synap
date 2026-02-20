# Tabla `stock_control_auditoria`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_stock_control_auditoria | BIGINT | No | ✓ |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| id_control_stock | BIGINT | Sí |  |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| tipo_error | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
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
| Stock_Control.frm | 1525 | SELECT | '    rs_control_auditoria.Open "SELECT * FROM stock_control_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)