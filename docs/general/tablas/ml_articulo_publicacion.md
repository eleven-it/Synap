# Tabla `ml_articulo_publicacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_publicacion | BIGINT | No | ✓ |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| id_publicacion_ml | VARCHAR | Sí |  |  |  |
| sincronizado | VARCHAR | Sí |  |  |  |
| fecha_sincronizado | DATETIME | Sí |  |  |  |
| lista_precio | VARCHAR | Sí |  |  |  |
| detalle_ml | LONGTEXT | Sí |  |  |  |
| precio_final | DOUBLE | Sí |  |  |  |
| comision_ml | DOUBLE | Sí |  |  |  |
| comision_convenio | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| titulo_publicacion_ml | VARCHAR | Sí |  |  |  |
| estado_publicacion_ml | VARCHAR | Sí |  |  |  |
| stock_publicacion_ml | DOUBLE | Sí |  |  |  |
| url_publicacion_ml | VARCHAR | Sí |  |  |  |
| id_deposito | DOUBLE | Sí |  |  |  |

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
| ecom_datos_articulo.frm | 3216 | JOIN | " LEFT JOIN ml_articulo_publicacion ON (ml_articulo_publicac… |
| ecom_datos_articulo.frm | 4015 | SELECT | rs.Open "SELECT * FROM ml_articulo_publicacion " & _ |
| ecom_datos_articulo.frm | 4026 | SELECT | rs.Open "SELECT * FROM ml_articulo_publicacion " & _ |
| ecom_datos_articulo.frm | 4033 | SELECT | rs.Open "SELECT * FROM ml_articulo_publicacion " & _ |
| ecom_datos_articulo.frm | 4574 | UPDATE | conn.Execute "UPDATE ml_articulo_publicacion " & _ |
| ml_sincronizacion.frm | 1578 | SELECT | "FROM ml_articulo_publicacion " & _ |
| ml_sincronizacion.frm | 1885 | SELECT | rs.Open "SELECT * FROM ml_articulo_publicacion " & _ |
| ml_modificacion_articulo.frm | 1297 | UPDATE | conn.Execute "UPDATE ml_articulo_publicacion " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)