# Tabla `articulo_foto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_foto | DOUBLE | No | ✓ |  |  |
| idArt | DOUBLE | Sí |  |  |  |
| url_interno | VARCHAR | Sí |  |  |  |
| url_externo | VARCHAR | Sí |  |  |  |
| descripcion_ext | MEDIUMTEXT | Sí |  |  |  |
| nombre_archivo | VARCHAR | Sí |  |  |  |
| fecha_creacion | TIMESTAMP | Sí |  |  |  |
| foto_principal | VARCHAR | Sí |  |  |  |
| foto_base | LONGBLOB | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 8086 | SELECT | 'Sql = "select url_externo AS URL from articulo_foto WHERE u… |
| TPV.frm | 40625 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| CargaArticulo_Video.frm | 188 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 7309 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 7384 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 7535 | SELECT | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo_Original.frm | 7535 | DELETE | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo_Original.frm | 7580 | UPDATE | conn.Execute "UPDATE articulo_foto SET articulo_foto.foto_pr… |
| CargaArticulo_Original.frm | 7744 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 7798 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| CargaArticulo_Original.frm | 8901 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " " |
| CargaArticulo_Original.frm | 10594 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 10701 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo_Original.frm | 12603 | SELECT | "FROM articulo_foto " & _ |
| Articulo.frm | 16809 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| FacturaB.frm | 13221 | SELECT | 'Sql = "select url_externo AS URL from articulo_foto WHERE u… |
| FacturaA.frm | 8747 | SELECT | 'Sql = "select url_externo AS URL from articulo_foto WHERE u… |
| Sup_importacion_tablas.frm | 5531 | UPDATE | conn.Execute "UPDATE articulo_foto LEFT JOIN (SELECT articul… |
| Sup_importacion_tablas.frm | 5532 | SELECT | " FROM articulo_foto " & _ |
| Sup_importacion_tablas.frm | 11913 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| Sup_importacion_tablas.frm | 12011 | SELECT | rs_articulo_foto.Open "SELECT * FROM articulo_foto WHERE id_… |
| CargaArticulo2.frm | 7200 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7275 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7426 | SELECT | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo2.frm | 7426 | DELETE | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo2.frm | 7454 | SELECT | rs_foto.Open "SELECT * FROM articulo_foto WHERE foto_princip… |
| CargaArticulo2.frm | 7618 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7695 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| CargaArticulo2.frm | 8790 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " " |
| CargaArticulo2.frm | 10461 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 10607 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 12509 | SELECT | "FROM articulo_foto " & _ |
| TPV_Seleccion_Articulo_Simple.frm | 1893 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| Pedido.frm | 6390 | SELECT | 'Sql = "select url_externo AS URL from articulo_foto WHERE u… |
| ecom_datos_articulo.frm | 3178 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " " |
| ecom_datos_articulo.frm | 3584 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| ecom_datos_articulo.frm | 3643 | SELECT | conn.Execute "DELETE FROM articulo_foto " & _ |
| ecom_datos_articulo.frm | 3643 | DELETE | conn.Execute "DELETE FROM articulo_foto " & _ |
| ecom_datos_articulo.frm | 3672 | UPDATE | conn.Execute "UPDATE articulo_foto SET articulo_foto.foto_pr… |
| ecom_datos_articulo.frm | 3725 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| ecom_datos_articulo.frm | 3827 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| AltaArticulo.frm | 7058 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| CargaArticulo.frm | 7940 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo.frm | 8015 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo.frm | 8293 | SELECT | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo.frm | 8293 | DELETE | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo.frm | 8340 | UPDATE | conn.Execute "UPDATE articulo_foto SET articulo_foto.foto_pr… |
| CargaArticulo.frm | 8642 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo.frm | 8651 | SELECT | "FROM articulo_foto WHERE idart = " & IDArt & " " |
| CargaArticulo.frm | 8733 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| CargaArticulo.frm | 10100 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " " |
| CargaArticulo.frm | 12206 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| CargaArticulo.frm | 12368 | INSERT | ''            conn.Execute "INSERT INTO articulo_foto SET ur… |
| CargaArticulo.frm | 12378 | SELECT | ''                                    "FROM articulo_foto WH… |
| CargaArticulo.frm | 12438 | SELECT | rs_articulo_foto.Open "SELECT * FROM articulo_foto WHERE ISN… |
| CargaArticulo.frm | 12539 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo.frm | 14622 | SELECT | "FROM articulo_foto " & _ |
| CargaArticulo.frm | 15918 | SELECT | rs_articulo_foto.Open "SELECT * FROM articulo_foto WHERE ISN… |
| VisualizarFichaArt.frm | 2074 | SELECT | "FROM articulo_foto WHERE idart = " & IDArt & " " |
| VisualizarFichaArt.frm | 2128 | SELECT | "FROM articulo_foto WHERE idart = " & lblCodSist & " " |
| VisualizarFichaArt.frm | 3184 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| VisualizarFichaArt.frm | 3427 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| VisualizarFichaArt.frm | 3469 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| Consulta_Precio_Articulo_Usr.frm | 1568 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " ", con… |
| Consulta_Precio_Articulo_Usr.frm | 1884 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| Crm_CargaFoto.frm | 572 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE idart = " & IDArt… |
| Crm_CargaFoto.frm | 595 | SELECT | "From articulo_foto " & _ |
| Crm_CargaFoto.frm | 639 | INSERT | conn.Execute "INSERT INTO articulo_foto(idart,url_interno,ur… |
| Crm_CargaFoto.frm | 659 | INSERT | conn.Execute "INSERT INTO articulo_foto(idart,url_interno,ur… |
| ArticuloProv.frm | 7223 | SELECT | rs.Open "SELECT * FROM articulo_foto WHERE ISNULL(url_extern… |
| CargaArticulo2.frm | 7200 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7275 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7426 | SELECT | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo2.frm | 7426 | DELETE | conn.Execute "DELETE FROM articulo_foto " & _ |
| CargaArticulo2.frm | 7454 | SELECT | rs_foto.Open "SELECT * FROM articulo_foto WHERE foto_princip… |
| CargaArticulo2.frm | 7618 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 7695 | SELECT | rs_f.Open "SELECT * FROM articulo_foto WHERE id_articulo_fot… |
| CargaArticulo2.frm | 8790 | SELECT | "FROM articulo_foto WHERE idart = " & id_articulo & " " |
| CargaArticulo2.frm | 10461 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| CargaArticulo2.frm | 10607 | INSERT | conn.Execute "INSERT INTO articulo_foto SET url_externo ='" … |
| … | … | … | *(3 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)