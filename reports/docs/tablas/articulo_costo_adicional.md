# Tabla `articulo_costo_adicional`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_costo_adicional | BIGINT | No | ✓ |  |  |
| IDArt | BIGINT | No |  |  |  |
| descripcion_costo | VARCHAR | Sí |  |  |  |
| costo | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_costo | VARCHAR | Sí |  |  |  |
| porcentaje | DOUBLE | Sí |  |  |  |

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
| Articulo_Carga_datos_adicional.frm | 3351 | UPDATE | conn.Execute "UPDATE articulo_costo_adicional SET articulo_c… |
| Articulo_Costo_Adicional.frm | 529 | UPDATE | conn.Execute "UPDATE articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 542 | INSERT | conn.Execute "INSERT INTO articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 653 | SELECT | rs.Open "SELECT * FROM articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 667 | SELECT | conn.Execute "DELETE FROM articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 667 | DELETE | conn.Execute "DELETE FROM articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 852 | SELECT | "FROM articulo_costo_adicional " & _ |
| Articulo_Costo_Adicional.frm | 1271 | SELECT | rs_Tot.Open "SELECT SUM(costo) as suma FROM articulo_costo_a… |
| Articulo_Costo_Adicional.frm | 1302 | SELECT | rs_Tot.Open "SELECT SUM(costo) as suma FROM articulo_costo_a… |
| CargaArticulo.frm | 8243 | UPDATE | conn.Execute "UPDATE articulo_costo_adicional SET articulo_c… |
| Carga_Articulo_Costo_Adicional.frm | 487 | SELECT | '        rs_Tot.Open "SELECT SUM(costo) as suma FROM articul… |
| Funciones.bas | 4682 | SELECT | " FROM articulo_costo_adicional " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)