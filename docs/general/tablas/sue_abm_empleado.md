# Tabla `sue_abm_empleado`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sue_abm_empleado | DOUBLE | No | ✓ |  |  |
| nombre_empleado | VARCHAR | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
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
| CargaMovCaja.frm | 1677 | SELECT | data_empleado.RecordSource = "SELECT * FROM sue_abm_empleado… |
| Info_Caja.frm | 2006 | SELECT | data_empleado.RecordSource = "SELECT * FROM sue_abm_empleado… |
| Carga_Cliente.frm | 5614 | INSERT | conn.Execute "INSERT INTO sue_abm_empleado " & _ |
| Carga_Cliente.frm | 6123 | UPDATE | conn.Execute "UPDATE sue_abm_empleado SET nombre_empleado = … |
| Carga_Cliente.frm | 6128 | UPDATE | conn.Execute "UPDATE sue_abm_empleado SET anulado = 'Si' " &… |
| Carga_Cliente.frm | 6133 | UPDATE | conn.Execute "UPDATE sue_abm_empleado SET anulado = 'No' " &… |
| Caja.frm | 2278 | SELECT | rs_usuario.Open "SELECT * FROM sue_abm_empleado WHERE id_sue… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)