# Tabla `ped_prep_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ped_prep_temp | DOUBLE | No | ✓ |  |  |
| CodigoMovimiento_prep | DOUBLE | Sí |  |  |  |
| id_responsable | DOUBLE | Sí |  |  |  |
| ped_numeracion | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombre_cliente_temp | VARCHAR | Sí |  |  |  |
| nro_comp_temp | VARCHAR | Sí |  |  |  |
| fecha_ped_temp | DATE | Sí |  |  |  |
| estado_ped_temp | VARCHAR | Sí |  |  |  |
| id_cliente_temp | DOUBLE | Sí |  |  |  |
| id_cliente_manual_temp | VARCHAR | Sí |  |  |  |

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
| Pedido_prep_consulta.frm | 1464 | SELECT | '                                "From ped_prep_temp WHERE i… |
| Pedido_prep.frm | 3455 | SELECT | '                       "From ped_prep_temp " & _ |
| Pedido_prep.frm | 3463 | SELECT | '                       "From ped_prep_temp " & _ |
| Pedido_prep.frm | 3471 | SELECT | " From ped_prep_temp " & _ |
| Pedido_prep.frm | 3482 | JOIN | '        INNER JOIN ped_prep_temp b ON a.CodigoMovimiento_pr… |
| Pedido_prep.frm | 3498 | JOIN | "INNER JOIN ped_prep_temp b ON " & _ |
| Pedido_prep.frm | 3510 | JOIN | "INNER JOIN ped_prep_temp b ON " & _ |
| Pedido_prep.frm | 3665 | SELECT | "From ped_prep_temp " & _ |
| Pedido_prep.frm | 3673 | JOIN | "INNER JOIN ped_prep_temp b ON " & _ |
| Pedido_prep.frm | 3748 | SELECT | rs_existe.Open "SELECT ped_numeracion From ped_prep_temp WHE… |
| Pedido_prep.frm | 3762 | SELECT | DataComprobanteA.RecordSource = "SELECT * FROM ped_prep_temp… |
| Pedido_prep.frm | 3795 | SELECT | DataComprobanteA.RecordSource = "SELECT * From ped_prep_temp… |
| Pedido_prep.frm | 3871 | SELECT | rs_ultimo.Open "SELECT * From ped_prep_temp WHERE id_usuario… |
| Pedido_prep.frm | 3886 | SELECT | conn.Execute "DELETE From ped_prep_temp WHERE id_ped_prep_te… |
| Pedido_prep.frm | 3886 | DELETE | conn.Execute "DELETE From ped_prep_temp WHERE id_ped_prep_te… |
| Pedido_prep.frm | 3898 | SELECT | ''                DataComprobanteA.RecordSource = "SELECT * … |
| Pedido_prep.frm | 3909 | SELECT | conn.Execute "DELETE From ped_prep_temp WHERE id_ped_prep_te… |
| Pedido_prep.frm | 3909 | DELETE | conn.Execute "DELETE From ped_prep_temp WHERE id_ped_prep_te… |
| Pedido_prep.frm | 3912 | SELECT | DataComprobanteA.RecordSource = "SELECT * From ped_prep_temp… |
| Pedido_prep.frm | 4152 | SELECT | "From ped_prep_temp WHERE id_usuario= " & Principal.idUsuari… |
| Pedido_prep.frm | 4176 | INSERT | conn.Execute "INSERT INTO ped_prep_temp (CodigoMovimiento_pr… |
| Pedido_prep.frm | 4192 | SELECT | "From ped_prep_temp WHERE id_usuario= " & Principal.idUsuari… |
| Pedido_prep.frm | 4348 | UPDATE | conn.Execute "UPDATE ped_prep_temp " & _ |
| Pedido_prep.frm | 4388 | UPDATE | conn.Execute "UPDATE ped_prep_temp " & _ |
| Pedido_prep.frm | 4450 | INSERT | conn.Execute "INSERT INTO ped_prep_temp (id_responsable, ped… |
| Pedido_prep.frm | 4486 | SELECT | '    DataComprobanteA.RecordSource = "SELECT * From ped_prep… |
| Pedido_prep.frm | 4507 | SELECT | conn.Execute "delete From ped_prep_temp where id_usuario = "… |
| Pedido_prep.frm | 4507 | DELETE | conn.Execute "delete From ped_prep_temp where id_usuario = "… |
| Principal.frm | 6120 | SELECT | conn.Execute "delete from ped_prep_temp where id_usuario = "… |
| Principal.frm | 6120 | DELETE | conn.Execute "delete from ped_prep_temp where id_usuario = "… |
| Principal.frm | 6186 | SELECT | conn.Execute "delete from ped_prep_temp where id_usuario = "… |
| Principal.frm | 6186 | DELETE | conn.Execute "delete from ped_prep_temp where id_usuario = "… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)