# Tabla `rubro`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodigoRubro | INT | No | ✓ |  |  |
| NombreRubro | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_rubro | VARCHAR | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |
| id_categoria | BIGINT | Sí |  |  |  |
| codigo_nomenclador_arba | VARCHAR | Sí |  |  |  |
| url_foto | VARCHAR | Sí |  |  |  |
| resol_afip_5329_iva | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_intereses | rubro | Crm_Intereses.frm | 431 | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbreRubro,NombreSubrubro… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Info_Stock.frm | 11591 | SELECT | DataRubro.RecordSource = "SELECT * FROM rubro WHERE rubro.an… |
| Liq_Carga_Comision_avanzada.frm | 493 | SELECT | "WHEN c.tipo_comision = 'Rubro' THEN (SELECT NombreRubro FRO… |
| Liq_Carga_Comision_avanzada.frm | 797 | SELECT | CargarDatos "SELECT CodigoRubro, NombreRubro FROM rubro WHER… |
| Liq_Carga_Comision_avanzada.frm | 850 | SELECT | "WHEN 'Rubro' THEN (SELECT NombreRubro FROM rubro WHERE Codi… |
| Articulo_Carga_datos_adicional.frm | 2253 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Articulo_Carga_datos_adicional.frm | 2272 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Rprecios_abm.frm | 2128 | SELECT | "From rubro " & _ |
| Rprecios_abm.frm | 2845 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = reglas_precio.id_ru… |
| Rprecios_abm.frm | 2866 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = reglas_precio_masiv… |
| Rprecios_abm.frm | 2881 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = reglas_precio_alta_… |
| TPV.frm | 16944 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| TPV.frm | 16958 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Rubro.frm | 360 | SELECT | DataRubro.RecordSource = "select * from rubro order by Nombr… |
| Rubro.frm | 461 | SELECT | " FROM rubro " & _ |
| Visualiza_Pedido.frm | 8181 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Visualiza_Pedido.frm | 8200 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Crm_Intereses.frm | 431 | JOIN | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbre… |
| Crm_Intereses.frm | 508 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = crm_intereses.id_ru… |
| ActDescuento.frm | 1502 | SELECT | DataRubro.RecordSource = "select * from Rubro order by Nombr… |
| CargaArticulo_Original.frm | 12490 | SELECT | rs_rubro.Open "SELECT NombreRubro FROM rubro WHERE  anulado=… |
| Rprecios_alta_art.frm | 1369 | SELECT | "From rubro " |
| Rprecios_alta_art.frm | 1661 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = reglas_precio_alta_… |
| Rprecios_alta_art.frm | 1797 | JOIN | '                    "LEFT JOIN rubro ON (rubro.CodigoRubro … |
| ABMArticulo_seleccion.frm | 3181 | SELECT | DataRubro.RecordSource = "SELECT * FROM rubro WHERE anulado=… |
| ABMArticulo_seleccion.frm | 5354 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE  anulado='No' AND C… |
| Articulo.frm | 7997 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE  anulado='No' AND C… |
| Articulo.frm | 8393 | SELECT | DataRubro.RecordSource = "SELECT * FROM rubro WHERE anulado=… |
| En_Carga_Config_Produccion.frm | 1328 | SELECT | consulta = "SELECT r.CodigoRubro,r.NombreRubro,r.anulado,r.t… |
| Info_Venta_respaldo_bruno.frm | 9999 | SELECT | DataRubro.RecordSource = "select * from Rubro where tipo_rub… |
| Articulo_FormulacionNom.frm | 4051 | SELECT | DataRubro.RecordSource = "select * from Rubro where tipo_rub… |
| Info_Venta.frm | 10087 | SELECT | DataRubro.RecordSource = "select * from Rubro where tipo_rub… |
| Crm_VisualizaInt.frm | 272 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = crm_intereses.id_ru… |
| Crm_VisualizaInt.frm | 282 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = crm_intereses.id_ru… |
| Rprecios_eliminar.frm | 2029 | SELECT | "From rubro " & _ |
| Rprecios_eliminar.frm | 3026 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = reglas_precio_masiv… |
| Programa_Descuentos.frm | 2154 | SELECT | "From rubro " & _ |
| Programa_Descuentos.frm | 2375 | JOIN | "LEFT JOIN rubro ON (rubro.codigorubro = sp_desc_programa.id… |
| Crm_AbmIntereses.frm | 411 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = crm_intereses.id_ru… |
| Crm_AbmIntereses.frm | 441 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = crm_intereses.id_ru… |
| NotaCred_SinCompO.frm | 9690 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| NotaCred_SinCompO.frm | 9707 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| FacturaA.frm | 11145 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| FacturaA.frm | 11159 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Rprecios_Masivas.frm | 1915 | SELECT | "From rubro " & _ |
| Crm_CargaLlamada.frm | 4039 | JOIN | sql_lista = sql_lista & " INNER JOIN rubro ON (crm_intereses… |
| stock_consulta_avanzada.frm | 2071 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| stock_consulta_avanzada.frm | 2189 | SELECT | Data_Rubro.RecordSource = "SELECT * FROM rubro WHERE rubro.a… |
| stock_consulta_avanzada.frm | 2674 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE CodigoRubro = " & D… |
| stock_consulta_avanzada.frm | 2821 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE CodigoRubro = " & D… |
| stock_consulta_avanzada.frm | 3801 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| VariacionPrecio.frm | 8847 | SELECT | DataRubrop.RecordSource = "select * from Rubro WHERE  anulad… |
| VariacionPrecio.frm | 8854 | SELECT | DataRubroSolo.RecordSource = "select * from Rubro WHERE  anu… |
| VariacionPrecio.frm | 8904 | SELECT | DataRubro.RecordSource = "select * from rubro WHERE  anulado… |
| Exportacion.frm | 2247 | SELECT | DataRubro.RecordSource = "select * from Rubro where anulado=… |
| Exportacion.frm | 7662 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Exportacion.frm | 8091 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRubr… |
| Exportacion.frm | 8103 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRubr… |
| Exportacion.frm | 8364 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRubr… |
| Exportacion.frm | 8376 | JOIN | "LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRubr… |
| CargaRubro.frm | 372 | SELECT | rs_rubro_cons.Open "SELECT * FROM rubro where NombreRubro = … |
| CargaRubro.frm | 383 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE CodigoRubro = 0", c… |
| CargaRubro.frm | 412 | SELECT | rs_rubro_cons.Open "SELECT * FROM rubro where NombreRubro = … |
| CargaRubro.frm | 423 | SELECT | rs_rubro.Open "SELECT * FROM rubro WHERE CodigoRubro =" & AB… |
| Sup_importacion_tablas.frm | 6106 | SELECT | DataRubro.RecordSource = "SELECT * FROM rubro WHERE Anulado … |
| Sup_importacion_tablas.frm | 7721 | UPDATE | sql_lince = sql_lince & "UPDATE rubro SET rubro.NombreRubro=… |
| Sup_importacion_tablas.frm | 8307 | SELECT | textosql = "DELETE FROM rubro WHERE CodigoRubro>3; ALTER TAB… |
| Sup_importacion_tablas.frm | 8307 | DELETE | textosql = "DELETE FROM rubro WHERE CodigoRubro>3; ALTER TAB… |
| CargaArticulo2.frm | 12396 | SELECT | rs_rubro.Open "SELECT NombreRubro FROM rubro WHERE  anulado=… |
| Presupuesto.frm | 7888 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Presupuesto.frm | 7905 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 713 | JOIN | "LEFT JOIN rubro r ON a.CodigoRubro = r.CodigoRubro " & _ |
| Info_Comercial.frm | 8150 | SELECT | DataRubro.RecordSource = "select * from Rubro where tipo_rub… |
| Info_Comercial.frm | 9813 | SELECT | sql = "SELECT * FROM Rubro WHERE id_categoria = " & combo_ca… |
| Pedido.frm | 9198 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| Pedido.frm | 9217 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| ActDatos_Articulo.frm | 3920 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| ActDatos_Articulo.frm | 4001 | SELECT | Data_Rubro.RecordSource = "SELECT * FROM rubro WHERE rubro.a… |
| ActDatos_Articulo.frm | 4805 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| NotaDeb.frm | 6389 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| NotaDeb.frm | 6406 | JOIN | " LEFT JOIN rubro ON (rubro.CodigoRubro = articulo.CodigoRub… |
| … | … | … | *(52 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 3152 | JOIN | LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro |
| services/query_runner.py | 3557 | JOIN | LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro |

[← Índice de tablas](../DB_INDICE_TABLAS.md)