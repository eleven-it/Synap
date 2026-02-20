# Tabla `articulo_categoria`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_categoria | BIGINT | No | ✓ |  |  |
| nombre_articulo_categoria | VARCHAR | Sí |  |  |  |
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
| Carga_ABMArticulo_Categoria.frm | 240 | SELECT | rs_articulo_categoria.Open "SELECT * FROM articulo_categoria… |
| Carga_ABMArticulo_Categoria.frm | 256 | SELECT | rs_articulo_categoria.Open "SELECT * FROM articulo_categoria… |
| Carga_ABMArticulo_Categoria.frm | 291 | SELECT | rs_articulo_categoria.Open "SELECT * FROM articulo_categoria… |
| ABMArticulo_Datos_Adicional.frm | 1249 | SELECT | "FROM articulo_categoria WHERE anulado='No'" |
| ABMArticulo_Categoria.frm | 474 | SELECT | consulta = "SELECT * FROM articulo_categoria WHERE nombre_ar… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)