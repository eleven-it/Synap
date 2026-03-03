# Tabla `subrubro`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NombreSubRubro | VARCHAR | Sí |  |  |  |
| CodigoRubro | INT | Sí |  | ✓ | rubro.CodigoRubro |
| CodigoSubRubro | INT | No |  |  |  |
| CodigoSubRubroT | VARCHAR | No |  |  |  |
| IDSubRubro | INT | No | ✓ |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |
| url_foto | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_intereses | subrubro | Crm_Intereses.frm | 431 | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbreRubro,NombreSubrubro… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Info_Stock.frm | 14156 | SELECT | DataSubRubro.RecordSource = "select * from subrubro where Co… |
| Liq_Carga_Comision_avanzada.frm | 494 | SELECT | "WHEN c.tipo_comision = 'Subrubro' THEN (SELECT NombreSubRub… |
| Liq_Carga_Comision_avanzada.frm | 799 | SELECT | CargarDatos "SELECT CodigoSubRubro, NombreSubRubro FROM subr… |
| Liq_Carga_Comision_avanzada.frm | 851 | SELECT | "WHEN 'Subrubro' THEN (SELECT NombreSubRubro FROM subrubro W… |
| Articulo_Carga_datos_adicional.frm | 2254 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| Articulo_Carga_datos_adicional.frm | 2273 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| Rprecios_abm.frm | 2138 | SELECT | "From SubRubro " & _ |
| Rprecios_abm.frm | 2282 | SELECT | "From SubRubro " & _ |
| Rprecios_abm.frm | 2846 | JOIN | "LEFT JOIN subrubro ON(subrubro.IdSubRubro = reglas_precio.i… |
| Rprecios_abm.frm | 2867 | JOIN | "LEFT JOIN subrubro ON(subrubro.IdSubRubro = reglas_precio_m… |
| Rprecios_abm.frm | 2882 | JOIN | "LEFT JOIN subrubro ON(subrubro.IdSubRubro = reglas_precio_a… |
| Crm_Intereses.frm | 431 | JOIN | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbre… |
| Crm_Intereses.frm | 509 | JOIN | "LEFT JOIN subrubro ON (subrubro.codigoSubRubro = crm_intere… |
| ActDescuento.frm | 1734 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where An… |
| CargaArticulo_Original.frm | 12502 | SELECT | rs_SubR.Open "SELECT NombreSubRubro FROM SubRubro WHERE  anu… |
| Rprecios_alta_art.frm | 1378 | SELECT | "From SubRubro " |
| Rprecios_alta_art.frm | 1662 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = reglas_precio_… |
| Rprecios_alta_art.frm | 1798 | JOIN | '                    "LEFT JOIN subrubro ON (subrubro.IDSubR… |
| Rprecios_alta_art.frm | 2062 | SELECT | "From SubRubro " & _ |
| ABMArticulo_seleccion.frm | 3185 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM subrubro WHERE an… |
| ABMArticulo_seleccion.frm | 5360 | SELECT | rs_subrubro.Open "SELECT * FROM subrubro WHERE  anulado='No'… |
| ABMArticulo_seleccion.frm | 5486 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where  a… |
| Articulo.frm | 7474 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where  a… |
| Articulo.frm | 8004 | SELECT | rs_subrubro.Open "SELECT * FROM subrubro WHERE  anulado='No'… |
| Articulo.frm | 8397 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM subrubro WHERE an… |
| En_Carga_Config_Produccion.frm | 1327 | SELECT | consulta = "SELECT   IDSubRubro,  NombreSubRubro FROM subrub… |
| En_Carga_Config_Produccion.frm | 1343 | SELECT | cargo_data_abm = "SELECT id_en_config, cod_sub_rubro_contene… |
| Info_Venta_respaldo_bruno.frm | 11947 | SELECT | DataSubRubro.RecordSource = "select * from subrubro where Co… |
| Articulo_FormulacionNom.frm | 4252 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM SubRubro WHERE Co… |
| Info_Venta.frm | 12369 | SELECT | DataSubRubro.RecordSource = "select * from subrubro where Co… |
| Crm_VisualizaInt.frm | 273 | JOIN | "LEFT JOIN subrubro ON (subrubro.codigoSubRubro = crm_intere… |
| Crm_VisualizaInt.frm | 283 | JOIN | "LEFT JOIN subrubro ON (subrubro.codigoSubRubro = crm_intere… |
| Rprecios_eliminar.frm | 2039 | SELECT | "From SubRubro " & _ |
| Rprecios_eliminar.frm | 2821 | SELECT | "From SubRubro " & _ |
| Rprecios_eliminar.frm | 3027 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = reglas_precio_… |
| Programa_Descuentos.frm | 2168 | SELECT | "From SubRubro " & _ |
| Programa_Descuentos.frm | 2376 | JOIN | "LEFT JOIN subrubro ON(subrubro.IdSubRubro = sp_desc_program… |
| Programa_Descuentos.frm | 2444 | SELECT | "From SubRubro " & _ |
| Crm_AbmIntereses.frm | 412 | JOIN | "LEFT JOIN subrubro ON (subrubro.codigoSubRubro = crm_intere… |
| Crm_AbmIntereses.frm | 442 | JOIN | "LEFT JOIN subrubro ON (subrubro.codigoSubRubro = crm_intere… |
| Rprecios_Masivas.frm | 1925 | SELECT | "From SubRubro " & _ |
| Crm_CargaLlamada.frm | 4039 | JOIN | sql_lista = sql_lista & " INNER JOIN rubro ON (crm_intereses… |
| stock_consulta_avanzada.frm | 2073 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| stock_consulta_avanzada.frm | 2199 | SELECT | Data_Subrubro.RecordSource = "SELECT * FROM subrubro WHERE s… |
| stock_consulta_avanzada.frm | 2605 | SELECT | Data_Subrubro.RecordSource = "SELECT * FROM subrubro WHERE c… |
| stock_consulta_avanzada.frm | 2680 | SELECT | rs_subrubro.Open "SELECT * FROM subrubro WHERE IDSubRubro = … |
| stock_consulta_avanzada.frm | 2827 | SELECT | rs_subrubro.Open "SELECT * FROM subrubro WHERE IDSubRubro = … |
| stock_consulta_avanzada.frm | 3802 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| VariacionPrecio.frm | 9244 | SELECT | DataSubRubro.RecordSource = "select * from subrubro where  a… |
| VariacionPrecio.frm | 9289 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where  a… |
| VariacionPrecio.frm | 9492 | SELECT | DataSubRubroSolo.RecordSource = "select * from SubRubro wher… |
| Exportacion.frm | 2386 | SELECT | DataSubRubro.RecordSource = "select * from subrubro where Co… |
| Exportacion.frm | 7664 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| Exportacion.frm | 8145 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = articulo.IDSub… |
| Exportacion.frm | 8157 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = articulo.IDSub… |
| Exportacion.frm | 8418 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = articulo.IDSub… |
| Exportacion.frm | 8430 | JOIN | "LEFT JOIN subrubro ON (subrubro.IDSubRubro = articulo.IDSub… |
| Sup_importacion_tablas.frm | 5837 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM subrubro WHERE Co… |
| Sup_importacion_tablas.frm | 6013 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM subrubro WHERE co… |
| Sup_importacion_tablas.frm | 6117 | SELECT | DataSubRubro.RecordSource = "SELECT * FROM subrubro WHERE An… |
| Sup_importacion_tablas.frm | 6958 | JOIN | " LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSub… |
| Sup_importacion_tablas.frm | 6979 | JOIN | " LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSub… |
| Sup_importacion_tablas.frm | 7000 | JOIN | " LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSub… |
| Sup_importacion_tablas.frm | 7031 | JOIN | '                            " LEFT JOIN subrubro ON subrubr… |
| Sup_importacion_tablas.frm | 7052 | JOIN | '                            " LEFT JOIN subrubro ON subrubr… |
| Sup_importacion_tablas.frm | 7724 | UPDATE | sql_lince = sql_lince & "UPDATE subrubro SET Anulado='Si' WH… |
| Sup_importacion_tablas.frm | 7728 | INSERT | sql_lince = sql_lince & "INSERT INTO subrubro(IDSubRubro,Cod… |
| Sup_importacion_tablas.frm | 8022 | JOIN | "LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubR… |
| Sup_importacion_tablas.frm | 8309 | SELECT | textosql = "DELETE FROM subrubro WHERE IDSubRubro>4;ALTER TA… |
| Sup_importacion_tablas.frm | 8309 | DELETE | textosql = "DELETE FROM subrubro WHERE IDSubRubro>4;ALTER TA… |
| Sup_importacion_tablas.frm | 9930 | SELECT | rs_subrubro.Open "SELECT * FROM subrubro WHERE subrubro.IDSu… |
| Sup_importacion_tablas.frm | 10475 | SELECT | 980           rs_subrubro.Open "SELECT * FROM subrubro WHERE… |
| CargaArticulo2.frm | 12408 | SELECT | rs_SubR.Open "SELECT NombreSubRubro FROM SubRubro WHERE  anu… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 714 | JOIN | "LEFT JOIN subrubro sr ON a.CodigoSubrubro = sr.CodigoSubrub… |
| Info_Comercial.frm | 8157 | SELECT | '    DataSubrubroTodos.RecordSource = "select * from SubRubr… |
| Info_Comercial.frm | 9696 | SELECT | sql = "select * from SubRubro where CodigoRubro = " & Rubro.… |
| Info_Comercial.frm | 9713 | SELECT | sql = "select * from SubRubro where CodigoRubro = " & combo_… |
| Info_Comercial.frm | 9732 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where Co… |
| Info_Comercial.frm | 9750 | SELECT | DataSubRubro.RecordSource = "select * from SubRubro where Co… |
| ActDatos_Articulo.frm | 3922 | JOIN | " LEFT JOIN subrubro ON (subrubro.idsubrubro = articulo.idsu… |
| … | … | … | *(60 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 3558 | JOIN | LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro |

[← Índice de tablas](../DB_INDICE_TABLAS.md)