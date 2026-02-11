# Tabla `crm_categoria`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_categoria | DOUBLE | No | ✓ |  |  |
| descripcion | VARCHAR | Sí |  |  |  |
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
| Crm_AbmCategoria.frm | 399 | SELECT | "FROM crm_categoria " & _ |
| Crm_AbmCategoria.frm | 427 | SELECT | "FROM crm_categoria " |
| Crm_CargaCliPot.frm | 2182 | SELECT | DataCategoria.RecordSource = "SELECT * FROM crm_categoria WH… |
| Carga_Cliente.frm | 6380 | SELECT | DataCategoria.RecordSource = "SELECT * FROM crm_categoria WH… |
| Crm_CargaCategoria.frm | 220 | INSERT | conn.Execute "INSERT INTO crm_categoria (descripcion, anulad… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)