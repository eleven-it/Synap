# Tabla `marca`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodMarca | INT | No | ✓ |  |  |
| NombreMarca | VARCHAR | Sí |  |  |  |
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
| Info_Stock.frm | 11609 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| Liq_Carga_Comision_avanzada.frm | 492 | SELECT | "WHEN c.tipo_comision = 'Marca' THEN (SELECT NombreMarca FRO… |
| Liq_Carga_Comision_avanzada.frm | 795 | SELECT | CargarDatos "SELECT CodMarca, NombreMarca FROM marca WHERE a… |
| Liq_Carga_Comision_avanzada.frm | 849 | SELECT | "WHEN 'Marca' THEN (SELECT NombreMarca FROM marca WHERE CodM… |
| Articulo_Carga_datos_adicional.frm | 2302 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| Rprecios_abm.frm | 2147 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| Rprecios_abm.frm | 2848 | JOIN | "LEFT JOIN marca ON (marca.codmarca = reglas_precio.id_marca… |
| Rprecios_abm.frm | 2869 | JOIN | "LEFT JOIN marca ON (marca.codmarca = reglas_precio_masivas.… |
| Rprecios_abm.frm | 2883 | JOIN | "LEFT JOIN marca ON(marca.codmarca = reglas_precio_alta_art.… |
| TPV.frm | 14500 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| TPV.frm | 14788 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| TPV.frm | 14850 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| TPV.frm | 14921 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ActDescuento.frm | 1524 | SELECT | DataMarca.RecordSource = "select * from marca where anulado … |
| Rprecios_alta_art.frm | 1386 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| Rprecios_alta_art.frm | 1663 | JOIN | "LEFT JOIN marca ON (marca.codmarca = reglas_precio_alta_art… |
| ABMArticulo_seleccion.frm | 3220 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE CodMarca… |
| ABMArticulo_seleccion.frm | 3277 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ABMArticulo_seleccion.frm | 5034 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| ABMArticulo_seleccion.frm | 5844 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE " & _ |
| ABMArticulo_seleccion.frm | 6020 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 7815 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_a… |
| Articulo.frm | 8243 | SELECT | '    DataMarca.RecordSource = "SELECT * FROM marca WHERE " &… |
| Articulo.frm | 8255 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE " & _ |
| Articulo.frm | 8432 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE CodMarca… |
| Articulo.frm | 8487 | JOIN | '            " LEFT JOIN marca ON (marca.codmarca = articulo… |
| Articulo.frm | 8511 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 10187 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 11960 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 12001 | JOIN | '                    " LEFT JOIN marca ON (marca.codmarca = … |
| Articulo.frm | 12966 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 13007 | JOIN | '                    " LEFT JOIN marca ON (marca.codmarca = … |
| Articulo.frm | 13967 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 14008 | JOIN | '                    " LEFT JOIN marca ON (marca.codmarca = … |
| Articulo.frm | 14970 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 15011 | JOIN | '                    " LEFT JOIN marca ON (marca.codmarca = … |
| Articulo.frm | 15965 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Articulo.frm | 16006 | JOIN | '                    " LEFT JOIN marca ON (marca.codmarca = … |
| Articulo_FormulacionNom.frm | 4058 | SELECT | DataMarca.RecordSource = "select * from marca where anulado=… |
| Info_Venta.frm | 10295 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| ABMPeriodos.frm | 529 | SELECT | DataYear.RecordSource = "select * from Marca where anulado =… |
| Rprecios_eliminar.frm | 2048 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| Programa_Descuentos.frm | 2193 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| Programa_Descuentos.frm | 2378 | JOIN | "LEFT JOIN marca ON (marca.codmarca = sp_desc_programa.id_ma… |
| ABMModelo.frm | 687 | SELECT | DataMarca.RecordSource = "select * from marca where anulado … |
| ABMModelo.frm | 693 | SELECT | DataMarca.RecordSource = "select * from marca where anulado … |
| ABMModelo.frm | 1031 | SELECT | consulta = "SELECT * FROM marca WHERE anulado = 'No' AND Nom… |
| stock_consulta_avanzada.frm | 2074 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| stock_consulta_avanzada.frm | 2219 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| stock_consulta_avanzada.frm | 2700 | SELECT | rs_marca.Open "SELECT marca.CodMarca,marca.NombreMarca FROM … |
| stock_consulta_avanzada.frm | 2847 | SELECT | rs_marca.Open "SELECT marca.CodMarca,marca.NombreMarca FROM … |
| stock_consulta_avanzada.frm | 3915 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| VariacionPrecio.frm | 8861 | SELECT | DataMarca.RecordSource = "select * from marca where anulado … |
| VariacionPrecio.frm | 8911 | SELECT | dataMarcaM.RecordSource = "select * from marca where anulado… |
| Exportacion.frm | 7665 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ABMArticulo_seleccion_simple.frm | 1597 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ABMArticulo_seleccion_simple.frm | 3226 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Sup_importacion_tablas.frm | 6128 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE Anulado … |
| Sup_importacion_tablas.frm | 7787 | UPDATE | sql_lince = sql_lince & "UPDATE marca SET marca.NombreMarca=… |
| Sup_importacion_tablas.frm | 8311 | SELECT | textosql = "DELETE FROM marca WHERE CodMarca>1;ALTER TABLE m… |
| Sup_importacion_tablas.frm | 8311 | DELETE | textosql = "DELETE FROM marca WHERE CodMarca>1;ALTER TABLE m… |
| TPV_Seleccion_Articulo_Simple.frm | 732 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| TPV_Seleccion_Articulo_Simple.frm | 1700 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 715 | JOIN | "LEFT JOIN marca m ON a.CodigoMarca = m.CodMarca " & _ |
| Info_Comercial.frm | 8162 | SELECT | DataMarca.RecordSource = "select * from marca order by Nombr… |
| ActDatos_Articulo.frm | 3923 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ActDatos_Articulo.frm | 4034 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| ActDatos_Articulo.frm | 4919 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| ecom_datos_articulo.frm | 3215 | JOIN | " LEFT JOIN marca ON (marca.CodMarca = articulo.CodigoMarca)… |
| ActDescuento_Prov.frm | 1865 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| ActDescuento_Prov.frm | 1971 | SELECT | Data_Marca.RecordSource = "SELECT * FROM marca WHERE marca.a… |
| ActDescuento_Prov.frm | 2822 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| CargaYear.frm | 396 | SELECT | rs_year.Open "SELECT * FROM marca WHERE NombreMarca='" & Yea… |
| CargaYear.frm | 406 | SELECT | rs_year.Open "SELECT * FROM marca WHERE CodMarca=" & ABMMode… |
| AltaArticulo.frm | 3505 | SELECT | DataMarca.RecordSource = "SELECT * FROM marca WHERE CodMarca… |
| AltaArticulo.frm | 3570 | JOIN | '            " LEFT JOIN marca ON (marca.codmarca = articulo… |
| AltaArticulo.frm | 3595 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| AltaArticulo.frm | 3688 | JOIN | " LEFT JOIN marca ON (marca.codmarca = articulo.codigomarca)… |
| AltaArticulo.frm | 5550 | SELECT | rs_marca.Open "SELECT * FROM marca WHERE CodMarca = " & rs_c… |
| AltaArticulo.frm | 5962 | SELECT | rs_marca.Open "SELECT marca.CodMarca,marca.NombreMarca FROM … |
| … | … | … | *(40 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)