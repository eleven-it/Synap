# Tabla `sp_desc_saldo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sp_desc_saldo | BIGINT | No | ✓ |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| saldo_puntos | DOUBLE | Sí |  |  |  |
| vencimiento | DATE | Sí |  |  |  |

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
| Carga_Cliente.frm | 4534 | SELECT | rs_saldo.Open "SELECT * FROM sp_desc_saldo WHERE id_cliente … |
| Funciones.bas | 11304 | SELECT | " FROM sp_desc_saldo " & _ |
| Funciones.bas | 11539 | SELECT | " FROM sp_desc_saldo " & _ |
| Funciones.bas | 11766 | SELECT | " FROM sp_desc_saldo " & _ |
| Funciones.bas | 11863 | SELECT | rs_saldo.Open "SELECT * FROM sp_desc_saldo WHERE id_cliente … |
| Funciones.bas | 11951 | SELECT | rs_saldo.Open "SELECT * FROM sp_desc_saldo WHERE id_cliente … |
| Funciones.bas | 11991 | SELECT | rs_saldo.Open "SELECT * FROM sp_desc_saldo WHERE id_cliente … |
| Funciones.bas | 12083 | SELECT | rs_saldo.Open "SELECT * FROM sp_desc_saldo WHERE id_cliente … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)