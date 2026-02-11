# Tabla `deposito_usr`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_deposito_usr | INT | No | ✓ |  |  |
| id_deposito | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| PNotaCred.frm | 4662 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| PNotaCred.frm | 4667 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| CargaUsuario.frm | 1707 | INSERT | conn.Execute "INSERT INTO deposito_usr (id_deposito,id_usuar… |
| NotaCred_COPIA.frm | 6975 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| NotaCred_COPIA.frm | 6980 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| AsigUsrDeposito.frm | 526 | SELECT | rs_exist.Open "SELECT * FROM deposito_usr WHERE id_deposito … |
| AsigUsrDeposito.frm | 585 | SELECT | conn.Execute "DELETE FROM Deposito_usr WHERE id_Deposito_usr… |
| AsigUsrDeposito.frm | 585 | DELETE | conn.Execute "DELETE FROM Deposito_usr WHERE id_Deposito_usr… |
| AsigUsrDeposito.frm | 629 | SELECT | "FROM deposito_usr " & _ |
| AsigUsrDeposito.frm | 759 | SELECT | conn.Execute "DELETE FROM Deposito_usr WHERE id_usuario = " … |
| AsigUsrDeposito.frm | 759 | DELETE | conn.Execute "DELETE FROM Deposito_usr WHERE id_usuario = " … |
| AsigUsrDeposito.frm | 770 | INSERT | conn.Execute "INSERT INTO Deposito_usr (id_deposito, id_usua… |
| Articulo.frm | 7219 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| Articulo.frm | 7224 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| PRemito.frm | 5348 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| PRemito.frm | 5353 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| NotaCred_SinCompO.frm | 8609 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| NotaCred_SinCompO.frm | 8614 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| NotaCredCopia.frm | 7586 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| NotaCredCopia.frm | 7591 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| Remito.frm | 8477 | SELECT | '    rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuar… |
| Remito.frm | 8482 | JOIN | '        "INNER JOIN deposito_usr ON (deposito_usr.id_deposi… |
| Remito.frm | 8658 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| Remito.frm | 8663 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| Pedido_Avanzado.frm | 3615 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| Pedido_Avanzado.frm | 3620 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| CargaUsuario_Copia.frm | 517 | INSERT | '                 conn.Execute "INSERT INTO deposito_usr (id… |
| CargaUsuario_Copia.frm | 519 | INSERT | '                 conn.Execute "INSERT INTO deposito_usr (id… |
| CargaUsuario_Copia.frm | 520 | SELECT | '                 " SELECT id_deposito,id_usuario FROM depos… |
| CargaUsuario_Copia.frm | 522 | INSERT | conn.Execute "INSERT INTO deposito_usr (id_deposito,id_usuar… |
| CargaUsuario_Copia.frm | 523 | SELECT | " SELECT id_deposito, '" & id_usr & "' FROM deposito_usr WHE… |
| Pedido_Interno.frm | 1302 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| Pedido_Interno.frm | 1307 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| NotaCred.frm | 7893 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| NotaCred.frm | 7898 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| PNotaCredCopia.frm | 4526 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| PNotaCredCopia.frm | 4531 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| CargaMovStock.frm | 3059 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| CargaMovStock.frm | 3064 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |
| ArticuloProv.frm | 4868 | SELECT | rs_depo.Open "SELECT * FROM deposito_usr WHERE id_usuario = … |
| ArticuloProv.frm | 4873 | JOIN | "INNER JOIN deposito_usr ON (deposito_usr.id_deposito = depo… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)