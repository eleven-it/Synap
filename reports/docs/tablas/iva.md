# Tabla `iva`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ID | INT | No | ✓ |  |  |
| Alicuota | DECIMAL | Sí |  |  |  |
| nombre_iva | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| cod_afip | INT | Sí |  |  |  |

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
| Articulo_Carga_datos_adicional.frm | 2252 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo_Carga_datos_adicional.frm | 2271 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo_Carga_datos_adicional.frm | 2871 | SELECT | rs_iva.Open "SELECT  alicuota FROM iva where id = " & rs_art… |
| NotaCredCon.frm | 10054 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & ListaNombreGas… |
| NotaCredDesc.frm | 1360 | SELECT | rs_alicuota.Open "select * from IVA" |
| Visualiza_TPV.frm | 6995 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| TPV.frm | 14501 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| TPV.frm | 14789 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| TPV.frm | 14851 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| TPV.frm | 14922 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| TPV.frm | 15043 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| TPV.frm | 21083 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Visualiza_NotaCredDesc.frm | 1472 | SELECT | rs_alicuota.Open "select * from IVA" |
| CargaArticulo_Original.frm | 8700 | SELECT | rs_alicuota_iva.Open "SELECT * FROM iva WHERE id = 1 or id =… |
| CargaArticulo_Original.frm | 9532 | SELECT | rs_iva.Open "SELECT  alicuota FROM iva where id = " & rs_art… |
| CargaArticulo_Original.frm | 10118 | SELECT | rs_iva.Open "SELECT  alicuota FROM iva where id = " & rs_art… |
| ABMArticulo_seleccion.frm | 3278 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| ABMArticulo_seleccion.frm | 5897 | JOIN | "LEFT JOIN iva ON iva.id = articulo.Alicuota " & _ |
| ABMArticulo_seleccion.frm | 5909 | JOIN | "LEFT JOIN iva ON iva.id = articulo.Alicuota " & _ |
| ABMArticulo_seleccion.frm | 6021 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 3385 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 3779 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 4174 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 4573 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 4931 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 5302 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 5635 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 5955 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 8488 | JOIN | '            " LEFT JOIN iva ON (iva.id = articulo.Alicuota)… |
| Articulo.frm | 8510 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 8729 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 9155 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 9455 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 9818 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & DataArticuloTe… |
| Articulo.frm | 10188 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 10270 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 11531 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 11961 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 12002 | JOIN | '                    " LEFT JOIN iva ON (iva.id = articulo.A… |
| Articulo.frm | 12119 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 12967 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 13008 | JOIN | '                    " LEFT JOIN iva ON (iva.id = articulo.A… |
| Articulo.frm | 13125 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 13968 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 14009 | JOIN | '                    " LEFT JOIN iva ON (iva.id = articulo.A… |
| Articulo.frm | 14126 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 14971 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 15012 | JOIN | '                    " LEFT JOIN iva ON (iva.id = articulo.A… |
| Articulo.frm | 15129 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Articulo.frm | 15966 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| Articulo.frm | 16007 | JOIN | '                    " LEFT JOIN iva ON (iva.id = articulo.A… |
| Articulo.frm | 16124 | SELECT | rs_iva.Open "SELECT * FROM iva WHERE id = " & rs_articulo.Fi… |
| Lista_Confeccion_OC_Gral.frm | 1102 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| IngresoUsuario.frm | 2771 | SELECT | .Source = "SELECT  * FROM iva" |
| Visualiza_PNotaCredDesc.frm | 1561 | SELECT | rs_alicuota.Open "select * from IVA", conn, adOpenDynamic, a… |
| stock_consulta_avanzada.frm | 2069 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| stock_consulta_avanzada.frm | 3800 | JOIN | " LEFT JOIN iva ON (iva.id = articulo.Alicuota) " & _ |
| VariacionPrecio.frm | 5588 | JOIN | '                                   conn.Execute "UPDATE art… |
| VariacionPrecio.frm | 5637 | JOIN | Debug.Print "3- " & "UPDATE articulo LEFT JOIN iva ON articu… |
| VariacionPrecio.frm | 5640 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5645 | JOIN | Debug.Print "4- NETOS - " & "UPDATE articulo LEFT JOIN iva O… |
| VariacionPrecio.frm | 5652 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5661 | JOIN | Debug.Print " 4 - IVA - " & "UPDATE articulo LEFT JOIN iva O… |
| VariacionPrecio.frm | 5668 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5704 | JOIN | " LEFT JOIN iva ON articulo.Alicuota=iva.ID " & VarWhere |
| VariacionPrecio.frm | 5812 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5818 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5821 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5829 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5832 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5841 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5845 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5859 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5865 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5868 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5876 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5879 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5888 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5892 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| VariacionPrecio.frm | 5903 | JOIN | conn.Execute "UPDATE articulo LEFT JOIN iva ON articulo.Alic… |
| … | … | … | *(163 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)