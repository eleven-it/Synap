# Tabla `cliente_contacto_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cliente_contacto_temp | DOUBLE | No | ✓ |  |  |
| nombre_cliente_contacto | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| nro_doc | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| diasContacto | VARCHAR | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_cliente_contacto | DOUBLE | Sí |  |  |  |
| whatsapp | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 3008 | SELECT | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Cliente.frm | 3008 | DELETE | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Cliente.frm | 3010 | INSERT | conn.Execute "INSERT INTO cliente_contacto_temp " & _ |
| Cliente.frm | 3018 | SELECT | Carga_Cliente.DataContactos.RecordSource = "SELECT * FROM cl… |
| Carga_ClienteContacto.frm | 572 | SELECT | rs_consulta.Open "SELECT * FROM cliente_contacto_temp WHERE … |
| Carga_ClienteContacto.frm | 585 | SELECT | rs_consulta.Open "SELECT * FROM cliente_contacto_temp WHERE … |
| Carga_ClienteContacto.frm | 603 | SELECT | DataContacto.RecordSource = "SELECT * FROM cliente_contacto_… |
| Carga_ClienteContacto.frm | 627 | SELECT | Carga_Cliente.DataContactos.RecordSource = "SELECT * FROM cl… |
| Carga_ClienteContacto.frm | 657 | SELECT | Carga_Cliente.DataContactos.RecordSource = "SELECT * FROM cl… |
| Facturacion.frm | 3507 | SELECT | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Facturacion.frm | 3507 | DELETE | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Facturacion.frm | 3509 | INSERT | conn.Execute "INSERT INTO cliente_contacto_temp " & _ |
| Facturacion.frm | 3517 | SELECT | Carga_Cliente.DataContactos.RecordSource = "SELECT * FROM cl… |
| Carga_Cliente.frm | 4664 | SELECT | conn.Execute "DELETE FROM cliente_contacto_temp WHERE id_cli… |
| Carga_Cliente.frm | 4664 | DELETE | conn.Execute "DELETE FROM cliente_contacto_temp WHERE id_cli… |
| Carga_Cliente.frm | 5608 | SELECT | "FROM cliente_contacto_temp " & _ |
| Carga_Cliente.frm | 6067 | SELECT | "FROM cliente_contacto_temp " & _ |
| Carga_Cliente.frm | 6071 | SELECT | "FROM cliente_contacto_temp " & _ |
| Carga_Cliente.frm | 6101 | SELECT | '            conn.Execute "delete from cliente_contacto_temp… |
| Carga_Cliente.frm | 6101 | DELETE | '            conn.Execute "delete from cliente_contacto_temp… |
| Carga_Cliente.frm | 7234 | SELECT | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Carga_Cliente.frm | 7234 | DELETE | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Principal.frm | 6106 | SELECT | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Principal.frm | 6106 | DELETE | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Principal.frm | 6172 | SELECT | conn.Execute "delete from cliente_contacto_temp where id_usu… |
| Principal.frm | 6172 | DELETE | conn.Execute "delete from cliente_contacto_temp where id_usu… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)