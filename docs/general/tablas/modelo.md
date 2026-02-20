# Tabla `modelo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodModelo | INT | No | ✓ |  |  |
| CodMarca | INT | Sí |  |  |  |
| NombreModelo | VARCHAR | Sí |  |  |  |
| Descripcion | MEDIUMTEXT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |

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
| Info_Stock.frm | 14217 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE CodMa… |
| Articulo_Carga_datos_adicional.frm | 2300 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| ActDescuento.frm | 1530 | SELECT | 'DataModelo.RecordSource = "select * from modelo order by No… |
| ActDescuento.frm | 1712 | SELECT | DataModelo.RecordSource = "select * from modelo where Anulad… |
| ABMArticulo_seleccion.frm | 3224 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| ABMArticulo_seleccion.frm | 3652 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| ABMArticulo_seleccion.frm | 5029 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| ABMArticulo_seleccion.frm | 5850 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Articulo.frm | 6670 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Articulo.frm | 7811 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| Articulo.frm | 8203 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Articulo.frm | 8261 | SELECT | '        DataModelo.RecordSource = "SELECT * FROM modelo WHE… |
| Articulo.frm | 8268 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Articulo.frm | 8436 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Articulo_FormulacionNom.frm | 4063 | SELECT | DataModelo.RecordSource = "SELECT CodModelo,NombreModelo FRO… |
| Articulo_FormulacionNom.frm | 4231 | SELECT | DataModelo.RecordSource = "SELECT CodModelo,NombreModelo FRO… |
| ABMPeriodos.frm | 531 | SELECT | DataPeriodo.RecordSource = "select * from Modelo where CodYe… |
| ABMModelo.frm | 656 | SELECT | DataModelo.RecordSource = "select * from Modelo where " & _ |
| ABMModelo.frm | 689 | SELECT | DataModelo.RecordSource = "select * from modelo where CodMar… |
| ABMModelo.frm | 697 | SELECT | DataModelo.RecordSource = "select * from modelo where " & _ |
| ABMModelo.frm | 1055 | SELECT | consulta = "SELECT * FROM modelo WHERE codmarca = " & CodMar… |
| CargaModelo.frm | 378 | SELECT | 'rs_modelo.Open "SELECT * FROM modelo WHERE  NombreModelo='"… |
| CargaModelo.frm | 379 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodMarca=" & ABMM… |
| CargaModelo.frm | 408 | SELECT | ABMModelo.DataModelo.RecordSource = "SELECT * FROM modelo WH… |
| CargaModelo.frm | 419 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodMarca=" & ABMM… |
| CargaModelo.frm | 430 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo=" & ABM… |
| stock_consulta_avanzada.frm | 2075 | JOIN | " LEFT JOIN modelo ON (modelo.codmodelo = articulo.codigomod… |
| stock_consulta_avanzada.frm | 2229 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE model… |
| stock_consulta_avanzada.frm | 2624 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE codma… |
| stock_consulta_avanzada.frm | 2708 | SELECT | rs_modelo.Open "SELECT modelo.CodModelo,modelo.NombreModelo … |
| stock_consulta_avanzada.frm | 2855 | SELECT | rs_modelo.Open "SELECT modelo.CodModelo,modelo.NombreModelo … |
| stock_consulta_avanzada.frm | 3910 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| VariacionPrecio.frm | 9267 | SELECT | DataModelo.RecordSource = "select * from modelo where Codmar… |
| VariacionPrecio.frm | 9312 | SELECT | DataModelo.RecordSource = "select * from modelo where Codmar… |
| Exportacion.frm | 7666 | JOIN | " LEFT JOIN modelo ON (modelo.codmodelo = articulo.codigomod… |
| Sup_importacion_tablas.frm | 5859 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE CodMar… |
| Sup_importacion_tablas.frm | 6139 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE Anulad… |
| Sup_importacion_tablas.frm | 7790 | UPDATE | sql_lince = sql_lince & "UPDATE modelo SET anulado='Si' WHER… |
| Sup_importacion_tablas.frm | 7792 | INSERT | sql_lince = sql_lince & "INSERT INTO modelo(CodModelo,CodMar… |
| Sup_importacion_tablas.frm | 8313 | SELECT | textosql = "DELETE FROM modelo WHERE CodModelo>1;ALTER TABLE… |
| Sup_importacion_tablas.frm | 8313 | DELETE | textosql = "DELETE FROM modelo WHERE CodModelo>1;ALTER TABLE… |
| Info_Comercial.frm | 8167 | SELECT | DataModelo.RecordSource = "select * from modelo" |
| Info_Comercial.frm | 9665 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE Codmar… |
| ActDatos_Articulo.frm | 3924 | JOIN | " LEFT JOIN modelo ON (modelo.codmodelo = articulo.codigomod… |
| ActDatos_Articulo.frm | 4045 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE model… |
| ActDatos_Articulo.frm | 4576 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE codma… |
| ActDatos_Articulo.frm | 4614 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE codma… |
| ActDatos_Articulo.frm | 4914 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| ActDescuento_Prov.frm | 1866 | JOIN | " LEFT JOIN modelo ON (modelo.codmodelo = articulo.codigomod… |
| ActDescuento_Prov.frm | 1981 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE model… |
| ActDescuento_Prov.frm | 2517 | SELECT | Data_Modelo.RecordSource = "SELECT * FROM modelo WHERE codma… |
| ActDescuento_Prov.frm | 2817 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| AltaArticulo.frm | 3509 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| AltaArticulo.frm | 4198 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| AltaArticulo.frm | 5545 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| AltaArticulo.frm | 5970 | SELECT | rs_modelo.Open "SELECT modelo.CodModelo,modelo.NombreModelo … |
| AltaArticulo.frm | 6581 | SELECT | '        DataModelo.RecordSource = "SELECT * FROM modelo WHE… |
| AltaArticulo.frm | 6588 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| VisualizarFichaArt.frm | 2289 | JOIN | "LEFT JOIN Modelo ON (Modelo.CodModelo = articulo.CodigoMode… |
| ml_sincronizacion.frm | 1271 | SELECT | DataModelo.RecordSource = "select * from modelo" |
| ml_sincronizacion.frm | 1825 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE Codmar… |
| ArticuloProv.frm | 4561 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| ArticuloProv.frm | 5636 | SELECT | rs_modelo.Open "SELECT * FROM modelo WHERE CodModelo = " & r… |
| ArticuloProv.frm | 5925 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| ArticuloProv.frm | 6129 | SELECT | '        DataModelo.RecordSource = "SELECT * FROM modelo WHE… |
| ArticuloProv.frm | 6563 | SELECT | '        DataModelo.RecordSource = "SELECT * FROM modelo WHE… |
| ArticuloProv.frm | 6620 | SELECT | '        DataModelo.RecordSource = "SELECT * FROM modelo WHE… |
| ArticuloProv.frm | 6627 | SELECT | DataModelo.RecordSource = "SELECT * FROM modelo WHERE " & _ |
| Principal.frm | 12599 | JOIN | '                            "LEFT JOIN modelo ON (modelo.Co… |
| Principal.frm | 12690 | SELECT | " FROM modelo " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)