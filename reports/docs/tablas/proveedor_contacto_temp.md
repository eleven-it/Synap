# Tabla `proveedor_contacto_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_proveedor_contacto_temp | DOUBLE | No | ✓ |  |  |
| nombre_proveedor_contacto | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| nro_doc | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| diasContacto | VARCHAR | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_proveedor_contacto | DOUBLE | Sí |  |  |  |

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
| CargaProveedorContacto.frm | 550 | SELECT | rs_consulta.Open "SELECT * FROM proveedor_contacto_temp WHER… |
| CargaProveedorContacto.frm | 563 | SELECT | rs_consulta.Open "SELECT * FROM proveedor_contacto_temp WHER… |
| CargaProveedorContacto.frm | 581 | SELECT | DataContacto.RecordSource = "SELECT * FROM proveedor_contact… |
| CargaProveedorContacto.frm | 607 | SELECT | CargaProveedor.DataContactos.RecordSource = "SELECT * FROM p… |
| CargaProveedorContacto.frm | 636 | SELECT | CargaProveedor.DataContactos.RecordSource = "SELECT * FROM p… |
| CargaProveedor.frm | 3321 | SELECT | conn.Execute "DELETE FROM proveedor_contacto_temp WHERE id_p… |
| CargaProveedor.frm | 3321 | DELETE | conn.Execute "DELETE FROM proveedor_contacto_temp WHERE id_p… |
| CargaProveedor.frm | 3913 | SELECT | "FROM proveedor_contacto_temp " & _ |
| CargaProveedor.frm | 4133 | SELECT | "FROM proveedor_contacto_temp " & _ |
| CargaProveedor.frm | 4139 | SELECT | "FROM proveedor_contacto_temp " & _ |
| CargaProveedor.frm | 5062 | SELECT | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| CargaProveedor.frm | 5062 | DELETE | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Proveedor.frm | 1198 | SELECT | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Proveedor.frm | 1198 | DELETE | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Proveedor.frm | 1200 | INSERT | conn.Execute "INSERT INTO proveedor_contacto_temp " & _ |
| Proveedor.frm | 1208 | SELECT | CargaProveedor.DataContactos.RecordSource = "SELECT * FROM p… |
| Principal.frm | 6121 | SELECT | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Principal.frm | 6121 | DELETE | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Principal.frm | 6187 | SELECT | conn.Execute "delete from proveedor_contacto_temp where id_u… |
| Principal.frm | 6187 | DELETE | conn.Execute "delete from proveedor_contacto_temp where id_u… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)