# Tabla `deposito_reposicion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_deposito_reposicion | DOUBLE | No | ✓ |  |  |
| id_articulo | DECIMAL | Sí |  |  |  |
| id_deposito | DECIMAL | Sí |  |  |  |
| stock_minimo | DECIMAL | Sí |  |  |  |
| stock_maximo | DECIMAL | Sí |  |  |  |
| punto_pedido | DECIMAL | Sí |  |  |  |
| pasillo | VARCHAR | Sí |  |  |  |
| estanteria | VARCHAR | Sí |  |  |  |
| nivel | VARCHAR | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 17617 | SELECT | "FROM deposito_reposicion " & _ |
| TPV.frm | 35407 | SELECT | "FROM deposito_reposicion " & _ |
| Visualiza_Pedido.frm | 3948 | JOIN | " LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_a… |
| Visualiza_Pedido.frm | 11080 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Visualiza_Pedido.frm | 11109 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Visualiza_Pedido.frm | 11127 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| CargaArticulo_Original.frm | 7083 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo_Original.frm | 7109 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo_Original.frm | 7125 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo_Original.frm | 7140 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo_Original.frm | 7172 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo_Original.frm | 7199 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo_Original.frm | 7214 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo_Original.frm | 7230 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo_Original.frm | 7507 | SELECT | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo_Original.frm | 7507 | DELETE | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo_Original.frm | 7941 | SELECT | rs_ConsulExiste.Open "select * from deposito_reposicion wher… |
| CargaArticulo_Original.frm | 13479 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo_Original.frm | 13498 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo_Original.frm | 13519 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| Lista_Confeccion_OC_Gral.frm | 1098 | JOIN | " LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_a… |
| FacturaB.frm | 24272 | SELECT | "FROM deposito_reposicion " & _ |
| FacturaA.frm | 20885 | SELECT | "FROM deposito_reposicion " & _ |
| En_GeneraOE.frm | 2994 | JOIN | "LEFT JOIN deposito_reposicion ON ( " & _ |
| En_GeneraOE.frm | 2997 | JOIN | "LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_ar… |
| En_GeneraOE.frm | 3005 | JOIN | "LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_ar… |
| En_GeneraOE.frm | 4137 | SELECT | "FROM deposito_reposicion " & _ |
| En_GeneraOE.frm | 5118 | SELECT | " FROM deposito_reposicion" & _ |
| stock_consulta_avanzada.frm | 2065 | JOIN | " LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_a… |
| Remito.frm | 12339 | SELECT | "FROM deposito_reposicion " & _ |
| CargaArticulo2.frm | 6974 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo2.frm | 7000 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo2.frm | 7016 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo2.frm | 7031 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo2.frm | 7063 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo2.frm | 7090 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo2.frm | 7105 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo2.frm | 7121 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo2.frm | 7398 | SELECT | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo2.frm | 7398 | DELETE | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo2.frm | 7838 | SELECT | rs_ConsulExiste.Open "select * from deposito_reposicion wher… |
| CargaArticulo2.frm | 13385 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo2.frm | 13404 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo2.frm | 13425 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| Visualiza_En_GeneraOE.frm | 3246 | JOIN | "LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_ar… |
| Visualiza_En_GeneraOE.frm | 3975 | SELECT | "FROM deposito_reposicion " & _ |
| AltaArticulo.frm | 6852 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| CargaArticulo.frm | 7714 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo.frm | 7740 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo.frm | 7756 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo.frm | 7771 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo.frm | 7803 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo.frm | 7830 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo.frm | 7845 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo.frm | 7861 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo.frm | 8265 | SELECT | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo.frm | 8265 | DELETE | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo.frm | 8877 | SELECT | rs_ConsulExiste.Open "select * from deposito_reposicion wher… |
| CargaArticulo.frm | 15498 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo.frm | 15517 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo.frm | 15538 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| VisualizarFichaArt.frm | 2114 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| TPV_2.frm | 32857 | SELECT | "FROM deposito_reposicion " & _ |
| Principal.frm | 10182 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Principal.frm | 10211 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Principal.frm | 10229 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Principal.frm | 10894 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Principal.frm | 10923 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Principal.frm | 10941 | JOIN | '            " LEFT JOIN deposito_reposicion ON (deposito_re… |
| Lista_Confeccion_OC.frm | 1276 | JOIN | " LEFT JOIN deposito_reposicion ON (deposito_reposicion.id_a… |
| CargaArticulo2.frm | 6974 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo2.frm | 7000 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo2.frm | 7016 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion", conn, a… |
| CargaArticulo2.frm | 7031 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo2.frm | 7063 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo2.frm | 7090 | SELECT | "From deposito_reposicion " & _ |
| CargaArticulo2.frm | 7105 | SELECT | rs_ActRepo.Open "select * from deposito_reposicion where id_… |
| CargaArticulo2.frm | 7121 | SELECT | DataConsRepo.RecordSource = "SELECT * From deposito_reposici… |
| CargaArticulo2.frm | 7398 | SELECT | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| CargaArticulo2.frm | 7398 | DELETE | conn.Execute "DELETE FROM deposito_reposicion " & _ |
| … | … | … | *(8 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)