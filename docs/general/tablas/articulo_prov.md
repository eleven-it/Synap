# Tabla `articulo_prov`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_prov | DOUBLE | No | ✓ |  |  |
| codProveedor | DOUBLE | Sí |  |  |  |
| IDArt | DOUBLE | No |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| nombreArticulo_prov | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_presentacionC | DOUBLE | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_display_bulto | DOUBLE | Sí |  |  |  |
| cantidad_bulto_pallet | DOUBLE | Sí |  |  |  |
| recargo_fraccion | VARCHAR | Sí |  |  |  |
| recargo_fraccion_porcentaje | DOUBLE | Sí |  |  |  |
| cantidad_unidad_lista2 | DOUBLE | Sí |  |  |  |
| cantidad_unidad_lista3 | DOUBLE | Sí |  |  |  |
| precio_unidad | VARCHAR | Sí |  |  |  |

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
| Articulo_Carga_datos_adicional.frm | 2779 | UPDATE | '    conn.Execute "UPDATE articulo_prov " & _ |
| Articulo_Carga_datos_adicional.frm | 2978 | SELECT | rs_consulta.Open "SELECT * FROM articulo_prov WHERE IDArt = … |
| AsigProvArt.frm | 751 | UPDATE | conn.Execute "UPDATE articulo_prov a " & _ |
| AsigProvArt.frm | 768 | INSERT | conn.Execute "INSERT INTO articulo_prov (anulado, cantidad_u… |
| AsigProvArt.frm | 773 | SELECT | "NOT IN( SELECT articulo_prov.codProveedor FROM articulo_pro… |
| AsigProvArt.frm | 780 | SELECT | conn.Execute "DELETE FROM articulo_prov " & _ |
| AsigProvArt.frm | 780 | DELETE | conn.Execute "DELETE FROM articulo_prov " & _ |
| AsigProvArt.frm | 1140 | SELECT | "From articulo_prov " & _ |
| FacturaB_COPIA.frm | 7501 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| FacturaB_COPIA.frm | 7503 | SELECT | "FROM articulo_prov " & _ |
| TPV.frm | 16407 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| TPV.frm | 16409 | SELECT | "FROM articulo_prov " & _ |
| Visualiza_Pedido.frm | 5364 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Visualiza_Pedido.frm | 5366 | SELECT | "FROM articulo_prov " & _ |
| CargaArticulo_Original.frm | 7052 | SELECT | rs_presC.Open "SELECT multiplicador_comp FROM Articulo_prov … |
| CargaArticulo_Original.frm | 7957 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| CargaArticulo_Original.frm | 9924 | UPDATE | conn.Execute "UPDATE articulo_prov " & _ |
| CargaArticulo_Original.frm | 13468 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| ABMArticulo_seleccion.frm | 3340 | SELECT | rs_multiC.Open "SELECT * FROM articulo_prov WHERE IDArt = " … |
| Articulo.frm | 10755 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 10757 | SELECT | "FROM articulo_prov " & _ |
| Articulo.frm | 12609 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 12611 | SELECT | "FROM articulo_prov " & _ |
| Articulo.frm | 13616 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 13618 | SELECT | "FROM articulo_prov " & _ |
| Articulo.frm | 14618 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 14620 | SELECT | "FROM articulo_prov " & _ |
| Articulo.frm | 15617 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 15619 | SELECT | "FROM articulo_prov " & _ |
| Articulo.frm | 16572 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Articulo.frm | 16574 | SELECT | "FROM articulo_prov " & _ |
| Lista_Confeccion_OC_Gral.frm | 1099 | JOIN | " LEFT JOIN articulo_prov ON (articulo_prov.IDArt = stock_de… |
| Lista_Pedidos_OPT.frm | 2396 | SELECT | rs_multiC.Open "SELECT * FROM articulo_prov WHERE IDArt = " … |
| Lista_Pedidos_OPT.frm | 2963 | SELECT | "FROM articulo_prov WHERE IDArt = " & IDArt & " AND CodProve… |
| Lista_Pedidos_OPT.frm | 3212 | SELECT | "FROM articulo_prov WHERE IDArt = " & IDArt & " AND CodProve… |
| FacturaB.frm | 12541 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| FacturaB.frm | 12543 | SELECT | "FROM articulo_prov " & _ |
| FacturaA.frm | 7990 | SELECT | '            rs_multi.Open "SELECT multiplicador_comp,cantid… |
| FacturaA.frm | 7992 | SELECT | "FROM articulo_prov " & _ |
| CargaArticuloProv.frm | 789 | SELECT | rs_artProv.Open "SELECT * From articulo_prov WHERE CodProvee… |
| stock_consulta_avanzada.frm | 2066 | JOIN | " LEFT JOIN articulo_prov ON (articulo_prov.IDArt = stock_de… |
| ABMArticulo_seleccion_simple.frm | 1772 | SELECT | '                    rs_multiC.Open "SELECT * FROM articulo_… |
| ABMArticulo_seleccion_simple.frm | 1935 | SELECT | rs_multiC.Open "SELECT * FROM articulo_prov WHERE IDArt = " … |
| Remito.frm | 7298 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Remito.frm | 7300 | SELECT | "FROM articulo_prov " & _ |
| CargaArticulo2.frm | 6943 | SELECT | rs_presC.Open "SELECT multiplicador_comp FROM Articulo_prov … |
| CargaArticulo2.frm | 7854 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| CargaArticulo2.frm | 9802 | UPDATE | conn.Execute "UPDATE articulo_prov " & _ |
| CargaArticulo2.frm | 13374 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| TPV_Modifica_Renglon.frm | 1917 | SELECT | '            rs_multi.Open "SELECT multiplicador_comp,cantid… |
| TPV_Modifica_Renglon.frm | 1919 | SELECT | "FROM articulo_prov " & _ |
| Presupuesto.frm | 5417 | SELECT | '            rs_multi.Open "SELECT multiplicador_comp,cantid… |
| Presupuesto.frm | 5419 | SELECT | "FROM articulo_prov " & _ |
| Pedido.frm | 5917 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Pedido.frm | 5919 | SELECT | "FROM articulo_prov " & _ |
| ABMArticulo_Datos_Adicional.frm | 1160 | SELECT | rs_consulta.Open "SELECT * FROM articulo_prov WHERE IDArt = … |
| ecom_datos_articulo.frm | 4457 | SELECT | '                    rs_multiC.Open "SELECT * FROM articulo_… |
| Articulo_Promo_ABM.frm | 610 | JOIN | " LEFT JOIN articulo_prov ON (articulo_prov.IDArt = articulo… |
| AltaArticulo.frm | 3750 | SELECT | rs_multiC.Open "SELECT * FROM articulo_prov WHERE IDArt = " … |
| CargaArticulo.frm | 7676 | SELECT | rs_presC.Open "SELECT multiplicador_comp FROM Articulo_prov … |
| CargaArticulo.frm | 8893 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| CargaArticulo.frm | 10721 | SELECT | rs_articulo_prov.Open "SELECT * FROM articulo_prov WHERE IDA… |
| CargaArticulo.frm | 10773 | SELECT | '                    rs_articulo_prov.Open "SELECT * FROM ar… |
| CargaArticulo.frm | 11283 | UPDATE | conn.Execute "UPDATE articulo_prov " & _ |
| CargaArticulo.frm | 11677 | SELECT | rs_articulo_prov.Open "SELECT * FROM articulo_prov WHERE IDA… |
| CargaArticulo.frm | 11770 | SELECT | rs_articulo_prov.Open "SELECT * FROM articulo_prov WHERE IDA… |
| CargaArticulo.frm | 15487 | SELECT | rs_pres_C.Open "SELECT multiplicador_comp FROM Articulo_prov… |
| Logi_Renglon.frm | 2424 | SELECT | '            rs_multi.Open "SELECT multiplicador_comp,cantid… |
| Logi_Renglon.frm | 2426 | SELECT | "FROM articulo_prov " & _ |
| VisualizarFichaArt.frm | 2834 | SELECT | rs_multiC.Open "SELECT cantidad_uni,multiplicador_comp,id_Un… |
| Facturacion_Ciclica_Renglon.frm | 2809 | SELECT | '            rs_multi.Open "SELECT multiplicador_comp,cantid… |
| Facturacion_Ciclica_Renglon.frm | 2811 | SELECT | "FROM articulo_prov " & _ |
| Lista_Comp_Gral.frm | 8522 | SELECT | rs_multiC.Open "SELECT * FROM articulo_prov WHERE IDArt = " … |
| Visualiza_Presupuesto.frm | 5186 | SELECT | 'rs_multi.Open "SELECT multiplicador_comp,cantidad_uni FROM … |
| Visualiza_Presupuesto.frm | 5188 | SELECT | "FROM articulo_prov " & _ |
| Stock.frm | 1336 | JOIN | "LEFT JOIN articulo_prov ON (articulo_prov.codProveedor = ar… |
| Stock.frm | 1365 | JOIN | "LEFT JOIN articulo_prov ON (articulo_prov.codProveedor = ar… |
| Stock.frm | 1399 | JOIN | "LEFT JOIN articulo_prov ON (articulo_prov.codProveedor = ar… |
| Stock.frm | 1426 | JOIN | "LEFT JOIN articulo_prov ON (articulo_prov.codProveedor = ar… |
| Stock.frm | 1453 | JOIN | "LEFT JOIN articulo_prov ON (articulo_prov.codProveedor = ar… |
| … | … | … | *(41 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)