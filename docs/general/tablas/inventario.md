# Tabla `inventario`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_inventario | INT | No | ✓ |  |  |
| id_articulo | INT | No |  |  |  |
| id_deposito | INT | No |  |  |  |
| fecha_inventario | DATE | Sí |  |  |  |
| saldo_sistema | DECIMAL | Sí |  |  |  |
| saldo_manual | DECIMAL | Sí |  |  |  |
| diferencia | DECIMAL | Sí |  |  |  |
| id_inventario_id | INT | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| Inventario.frm | 1529 | SELECT | rs_inventario.Open "SELECT * FROM inventario", conn, adOpenD… |
| Inventario.frm | 2046 | SELECT | '    DataInventario.RecordSource = "SELECT * FROM inventario… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)