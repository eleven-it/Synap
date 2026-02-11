# Tabla `inventario_temp`

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
| nombrearticulo | VARCHAR | Sí |  |  |  |
| nombredeposito | VARCHAR | Sí |  |  |  |
| Codusuario | INT | Sí |  |  |  |
| PrecioCosto | DECIMAL | Sí |  |  |  |

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
| Inventario.frm | 1720 | SELECT | '    DataInventario.RecordSource = "SELECT * FROM inventario… |
| Inventario.frm | 1735 | SELECT | conn.Execute "DELETE FROM inventario_temp WHERE id_inventari… |
| Inventario.frm | 1735 | DELETE | conn.Execute "DELETE FROM inventario_temp WHERE id_inventari… |
| Inventario.frm | 1744 | SELECT | dataInventario.RecordSource = "SELECT * FROM inventario_temp… |
| Inventario.frm | 1804 | SELECT | dataInventario.RecordSource = "SELECT * FROM inventario_temp… |
| Inventario.frm | 1969 | SELECT | dataInventario.RecordSource = "SELECT * FROM inventario_temp… |
| Inventario.frm | 2093 | SELECT | dataInventario.RecordSource = "SELECT * FROM inventario_temp… |
| Inventario.frm | 2109 | SELECT | rs_consulta.Open "select * from inventario_temp where id_art… |
| Inventario.frm | 2155 | SELECT | conn.Execute "delete from inventario_temp where Codusuario =… |
| Inventario.frm | 2155 | DELETE | conn.Execute "delete from inventario_temp where Codusuario =… |
| Inventario.frm | 3916 | SELECT | dataInventario.RecordSource = "SELECT * FROM inventario_temp… |
| Inventario.frm | 3932 | SELECT | rs_consulta.Open "select * from inventario_temp where id_art… |
| Principal.frm | 6093 | SELECT | conn.Execute "delete from inventario_temp where CodUsuario =… |
| Principal.frm | 6093 | DELETE | conn.Execute "delete from inventario_temp where CodUsuario =… |
| Principal.frm | 6159 | SELECT | conn.Execute "delete from inventario_temp where CodUsuario =… |
| Principal.frm | 6159 | DELETE | conn.Execute "delete from inventario_temp where CodUsuario =… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)