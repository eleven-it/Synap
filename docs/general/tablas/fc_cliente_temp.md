# Tabla `fc_cliente_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_fc_cliente_temp | DOUBLE | No | ✓ |  |  |
| Codigo | INT | No |  |  |  |
| nombre_cliente | VARCHAR | Sí |  |  |  |
| TipoCliente | VARCHAR | Sí |  |  |  |
| telefono | VARCHAR | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| iva | VARCHAR | Sí |  |  |  |
| detalle_temp | MEDIUMTEXT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| Calle | VARCHAR | Sí |  |  |  |
| NroCalle | VARCHAR | Sí |  |  |  |
| Dpto | VARCHAR | Sí |  |  |  |
| IDDistrito | INT | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| Email | VARCHAR | Sí |  |  |  |
| Fax | VARCHAR | Sí |  |  |  |
| NombreContacto | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| Credito | DECIMAL | Sí |  |  |  |
| Descuento | DECIMAL | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| Observaciones | MEDIUMTEXT | Sí |  |  |  |
| ListaPrecio | VARCHAR | Sí |  |  |  |
| FechaAlta | DATE | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| NroIngBrutos | VARCHAR | Sí |  |  |  |
| NroAgenteRetencion | VARCHAR | Sí |  |  |  |
| id_manual_cli | VARCHAR | Sí |  |  |  |
| id_cv | INT | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| credito_cheque | DECIMAL | Sí |  |  |  |
| credito_limite_dias | DECIMAL | Sí |  |  |  |
| credito_cheque_tercero | DECIMAL | Sí |  |  |  |
| cliente_ecommerce | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| aviso | MEDIUMTEXT | Sí |  |  |  |
| habilita_aviso | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| id_cobrador | INT | Sí |  |  |  |
| descuento_por_cli | DECIMAL | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| id_categoria | DOUBLE | Sí |  |  |  |

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
| Facturacion_Ciclica.frm | 2021 | SELECT | "From fc_cliente_temp WHERE id_usuario= " & Principal.idUsua… |
| Facturacion_Ciclica.frm | 2476 | SELECT | rs_existe.Open "SELECT Codigo FROM fc_cliente_temp WHERE Cod… |
| Facturacion_Ciclica.frm | 2490 | SELECT | "FROM fc_cliente_temp " & _ |
| Facturacion_Ciclica.frm | 2523 | SELECT | DataClienteD.RecordSource = "SELECT * From fc_cliente_temp W… |
| Facturacion_Ciclica.frm | 2526 | SELECT | '    DataClienteD.RecordSource = "SELECT * FROM fc_cliente_t… |
| Facturacion_Ciclica.frm | 2584 | SELECT | conn.Execute "DELETE From fc_cliente_temp WHERE id_fc_client… |
| Facturacion_Ciclica.frm | 2584 | DELETE | conn.Execute "DELETE From fc_cliente_temp WHERE id_fc_client… |
| Facturacion_Ciclica.frm | 2670 | JOIN | "RIGHT JOIN fc_cliente_temp ON (fc_cliente_temp.Codigo = cli… |
| Facturacion_Ciclica.frm | 2683 | INSERT | conn.Execute "INSERT INTO fc_cliente_temp (Codigo, nombre_cl… |
| Facturacion_Ciclica.frm | 2693 | SELECT | DataClienteD.RecordSource = "SELECT * From fc_cliente_temp W… |
| Facturacion_Ciclica.frm | 4266 | SELECT | conn.Execute "DELETE FROM fc_cliente_temp WHERE id_usuario =… |
| Facturacion_Ciclica.frm | 4266 | DELETE | conn.Execute "DELETE FROM fc_cliente_temp WHERE id_usuario =… |
| Principal.frm | 6102 | SELECT | conn.Execute "delete from fc_cliente_temp where id_usuario =… |
| Principal.frm | 6102 | DELETE | conn.Execute "delete from fc_cliente_temp where id_usuario =… |
| Principal.frm | 6168 | SELECT | conn.Execute "delete from fc_cliente_temp where id_usuario =… |
| Principal.frm | 6168 | DELETE | conn.Execute "delete from fc_cliente_temp where id_usuario =… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)