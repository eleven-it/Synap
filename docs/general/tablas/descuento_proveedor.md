# Tabla `descuento_proveedor`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_descuento_proveedor | BIGINT | No | ✓ |  |  |
| id_proveedor | BIGINT | Sí |  |  |  |
| importe_descuento | DOUBLE | Sí |  |  |  |
| composicion_descuento | MEDIUMTEXT | Sí |  |  |  |
| descripcion_descuento | VARCHAR | Sí |  |  |  |
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
| Articulo_Carga_datos_adicional.frm | 2436 | SELECT | " FROM descuento_proveedor " & _ |
| Carga_Descuento_Proveedor.frm | 401 | SELECT | rs.Open "SELECT * FROM descuento_proveedor WHERE descripcion… |
| Carga_Descuento_Proveedor.frm | 417 | SELECT | rs.Open "SELECT * FROM descuento_proveedor WHERE id_descuent… |
| Carga_Descuento_Proveedor.frm | 445 | SELECT | rs.Open "SELECT * FROM descuento_proveedor WHERE id_descuent… |
| ActDescuento_Prov.frm | 1861 | JOIN | " LEFT JOIN descuento_proveedor ON (descuento_proveedor.id_d… |
| ActDescuento_Prov.frm | 2003 | SELECT | " FROM descuento_proveedor " & _ |
| ActDescuento_Prov.frm | 2251 | JOIN | '                        " LEFT JOIN descuento_proveedor ON … |
| CargaArticulo.frm | 9670 | SELECT | " FROM descuento_proveedor " & _ |
| ABM_Descuento_Proveedor.frm | 400 | SELECT | consulta = "SELECT descuento_proveedor.*,proveedor.Nombre as… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)