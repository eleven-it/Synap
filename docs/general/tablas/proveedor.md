# Tabla `proveedor`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Codigo | INT | No | ✓ |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| TipoViajante | VARCHAR | No |  |  |  |
| Nombre | VARCHAR | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| Calle | VARCHAR | Sí |  |  |  |
| NroCalle | VARCHAR | Sí |  |  |  |
| Dpto | VARCHAR | Sí |  |  |  |
| IDDistrito | INT | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| TelefonoParticular | VARCHAR | Sí |  |  |  |
| TelefonoTrabajo | VARCHAR | Sí |  |  |  |
| Celular | VARCHAR | Sí |  |  |  |
| Email | VARCHAR | Sí |  |  |  |
| Fax | VARCHAR | Sí |  |  |  |
| NombreContacto | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| Observaciones | MEDIUMTEXT | Sí |  |  |  |
| Diferencia | DECIMAL | Sí |  |  |  |
| AfavorOP | DECIMAL | Sí |  |  |  |
| AfavorNC | DECIMAL | Sí |  |  |  |
| NroCAI | VARCHAR | Sí |  |  |  |
| FechaCAI | DATE | Sí |  |  |  |
| NroIngBrutos | VARCHAR | Sí |  |  |  |
| CodCatRet | INT | Sí |  |  |  |
| CodCatRetG | INT | Sí |  |  |  |
| NroAgenteRetencion | INT | Sí |  |  |  |
| cert_IIBB | VARCHAR | Sí |  |  |  |
| desde_cert_IIBB | DATE | Sí |  |  |  |
| hasta_cert_IIBB | DATE | Sí |  |  |  |
| id_manual_prov | VARCHAR | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| descuento | DECIMAL | Sí |  |  |  |
| credito | DECIMAL | Sí |  |  |  |
| id_cc | INT | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| id_cod_afip_percep | INT | Sí |  |  |  |
| cod_ret_iva | INT | Sí |  |  |  |
| whatsapp_empresa | VARCHAR | Sí |  |  |  |
| web_empresa | VARCHAR | Sí |  |  |  |
| obliga_oc_carga_comp | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| precios_historial | proveedor | CargaArticulo_Original.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo_Original.frm | 8882 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |
| precios_historial | proveedor | CargaArticulo2.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo2.frm | 8771 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |
| precios_historial | proveedor | CargaArticulo.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo.frm | 9860 | '    DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as… |
| precios_historial | proveedor | CargaArticulo.frm | 10117 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Info_Stock.frm | 11841 | SELECT | "From Proveedor WHERE codigo <> 1 " |
| PNotaCred.frm | 2890 | SELECT | '                        .Source = "SELECT proveedor.codigo,… |
| PNotaCred.frm | 2907 | SELECT | .Source = "SELECT proveedor.codigo,proveedor.saldo FROM prov… |
| PNotaCred.frm | 2922 | SELECT | rs_proveedor.Open "SELECT proveedor.codigo,proveedor.saldo F… |
| PNotaCred.frm | 6260 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| Articulo_Carga_datos_adicional.frm | 2289 | SELECT | rs_proveedor.Open "SELECT * FROM proveedor WHERE Codigo = " … |
| Articulo_Carga_datos_adicional.frm | 2437 | JOIN | "LEFT JOIN proveedor ON (proveedor.Codigo = descuento_provee… |
| Visualiza_PNotaDeb.frm | 3735 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| AsigProvArt.frm | 1141 | JOIN | "LEFT JOIN proveedor ON (proveedor.Codigo = articulo_prov.co… |
| Rprecios_abm.frm | 2118 | SELECT | "From proveedor WHERE proveedor.Nombre <> '-Ninguno-' AND " … |
| Rprecios_abm.frm | 2844 | JOIN | "LEFT JOIN proveedor ON (proveedor.codigo = reglas_precio.id… |
| Rprecios_abm.frm | 2865 | JOIN | "LEFT JOIN proveedor ON (proveedor.codigo = reglas_precio_ma… |
| Rprecios_abm.frm | 2880 | JOIN | "LEFT JOIN proveedor ON (proveedor.codigo = reglas_precio_al… |
| ml_consulta_indices.frm | 289 | JOIN | "LEFT JOIN proveedor ON proveedor.Codigo = chequepropio.CodP… |
| AsigProvArt_Carga.frm | 1189 | SELECT | "From proveedor WHERE codigo <> 1 " |
| CorreoEnvio2.frm | 2531 | SELECT | data_entidad.RecordSource = "SELECT codigo, nombre FROM prov… |
| CorreoEnvio2.frm | 2544 | SELECT | data_entidad.RecordSource = "SELECT * FROM proveedor " & _ |
| ActDescuento.frm | 1519 | SELECT | DataProveedor.RecordSource = "SELECT proveedor.Nombre,provee… |
| CargaArticulo_Original.frm | 8882 | JOIN | DataHistop.RecordSource = "SELECT  precios_historial.*, prov… |
| CargaArticulo_Original.frm | 12481 | SELECT | rs_prov.Open "SELECT Nombre FROM proveedor WHERE codigo = " … |
| OrdenPago.frm | 7161 | SELECT | .Source = "select proveedor.codigo,proveedor.saldo from prov… |
| OrdenPago.frm | 7172 | SELECT | rs_proveedor.Open "SELECT * FROM proveedor where codigo = " … |
| OrdenPago.frm | 10121 | SELECT | .Source = "SELECT saldo,Codigo FROM proveedor WHERE " & _ |
| OrdenPago.frm | 13274 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| OrdenPago.frm | 15573 | SELECT | rs_prov.Open "SELECT * from proveedor where codigo = " & rs_… |
| Rprecios_alta_art.frm | 1360 | SELECT | "From proveedor WHERE proveedor.Nombre <> '-Ninguno-' " |
| Rprecios_alta_art.frm | 1660 | JOIN | "LEFT JOIN proveedor ON (proveedor.Codigo = reglas_precio_al… |
| Carga_Descuento_Proveedor.frm | 503 | SELECT | Data_Proveedor.RecordSource = "SELECT * FROM proveedor WHERE… |
| Visualiza_PNotaCred_Importe.frm | 2129 | SELECT | .Source = "SELECT proveedor.codigo,proveedor.saldo FROM prov… |
| Visualiza_PNotaCred_Importe.frm | 2142 | SELECT | rs_proveedor.Open "SELECT proveedor.codigo,proveedor.saldo F… |
| Visualiza_PNotaCred_Importe.frm | 3210 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| ABMArticulo_seleccion.frm | 3249 | SELECT | DataProveedor.RecordSource = "SELECT proveedor.*, contribuye… |
| ABMArticulo_seleccion.frm | 5022 | SELECT | rs_proveedor.Open "SELECT * FROM proveedor WHERE Codigo = " … |
| ABMArticulo_seleccion.frm | 5807 | SELECT | DataProveedor.RecordSource = "SELECT * FROM proveedor WHERE … |
| Articulo.frm | 7804 | SELECT | rs_proveedor.Open "SELECT * FROM proveedor WHERE Codigo = " … |
| Articulo.frm | 8165 | SELECT | DataProveedor.RecordSource = "SELECT * FROM proveedor WHERE … |
| Articulo.frm | 8461 | SELECT | DataProveedor.RecordSource = "SELECT proveedor.*, contribuye… |
| Articulo.frm | 8512 | JOIN | " LEFT JOIN proveedor ON (proveedor.codigo = articulo.codigo… |
| Visualiza_POrden_Compra.frm | 3756 | SELECT | rs_informe.Open "SELECT * FROM proveedor WHERE Codigo = " & … |
| Info_Venta_respaldo_bruno.frm | 10121 | SELECT | data_proveedor.RecordSource = "SELECT Codigo,Tipo,Nombre FRO… |
| Articulo_FormulacionNom.frm | 4095 | SELECT | "From proveedor " |
| POrden_CompraCopia.frm | 3344 | SELECT | rs_informe.Open "SELECT * FROM proveedor WHERE Codigo = " & … |
| PRemito.frm | 3576 | SELECT | rs_condcompra.Open "SELECT * FROM proveedor where Codigo = "… |
| Visualiza_PNotaCredDev.frm | 2658 | SELECT | .Source = "SELECT proveedor.codigo,proveedor.saldo FROM prov… |
| Visualiza_PNotaCredDev.frm | 2671 | SELECT | rs_proveedor.Open "SELECT proveedor.codigo,proveedor.saldo F… |
| Visualiza_PNotaCredDev.frm | 5055 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| CorreoEnvio.frm | 887 | SELECT | data_entidad.RecordSource = "SELECT codigo, nombre FROM prov… |
| CorreoEnvio.frm | 900 | SELECT | data_entidad.RecordSource = "SELECT * FROM proveedor " & _ |
| Lista_Confeccion_OC_Gral.frm | 1103 | JOIN | " LEFT JOIN proveedor ON (proveedor.Codigo = articulo.Codigo… |
| Info_Venta.frm | 10209 | SELECT | Data_Proveedor.RecordSource = "SELECT Codigo,Tipo,Nombre FRO… |
| Visualiza_PNotaCredDesc.frm | 1557 | SELECT | rs_proveedor.Open "select * from Proveedor where Codigo = " … |
| Visualiza_PNotaCredDesc.frm | 1941 | SELECT | .Source = "SELECT proveedor.codigo,proveedor.saldo FROM prov… |
| Visualiza_PNotaCredDesc.frm | 1954 | SELECT | rs_proveedor.Open "SELECT proveedor.codigo,proveedor.saldo F… |
| Visualiza_PNotaCredDesc.frm | 2706 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| Rprecios_eliminar.frm | 2019 | SELECT | "From proveedor WHERE proveedor.Nombre <> '-Ninguno-' AND " … |
| Rprecios_eliminar.frm | 3025 | JOIN | "LEFT JOIN proveedor ON (proveedor.Codigo = reglas_precio_ma… |
| Programa_Descuentos.frm | 2140 | SELECT | "From proveedor WHERE proveedor.Nombre <> '-Ninguno-' AND " … |
| Programa_Descuentos.frm | 2374 | JOIN | "LEFT JOIN proveedor ON (proveedor.codigo = sp_desc_programa… |
| Info2.frm | 489 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| Info2.frm | 844 | SELECT | '                rs_datos.Open "SELECT Email, EmailContacto … |
| Info2.frm | 1236 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| Rprecios_Masivas.frm | 1905 | SELECT | "From proveedor WHERE proveedor.Nombre <> '-Ninguno-' AND " … |
| PNotaDebCopia.frm | 1861 | SELECT | .Source = "SELECT proveedor.codigo,proveedor.saldo FROM prov… |
| PNotaDebCopia.frm | 1874 | SELECT | rs_proveedor.Open "SELECT proveedor.codigo,proveedor.saldo F… |
| PNotaDebCopia.frm | 4192 | SELECT | rs_caja.Open "SELECT * from proveedor where codigo = " & CDb… |
| PNotaDebCopia.frm | 4782 | SELECT | '    rs_saldo_proveedor.Open "SELECT proveedor.codigo,provee… |
| PNotaDebCopia.frm | 4801 | SELECT | '            rs_proveedor.Open "SELECT proveedor.codigo,prov… |
| Info3.frm | 489 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| Info3.frm | 844 | SELECT | '                rs_datos.Open "SELECT Email, EmailContacto … |
| Info3.frm | 1236 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| Info7.frm | 489 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| Info7.frm | 845 | SELECT | '                rs_datos.Open "SELECT Email, EmailContacto … |
| Info7.frm | 1237 | SELECT | rs_datos.Open "SELECT Email, EmailContacto FROM proveedor WH… |
| stock_consulta_avanzada.frm | 2070 | JOIN | " LEFT JOIN proveedor ON (proveedor.Codigo = articulo.Codigo… |
| stock_consulta_avanzada.frm | 2209 | SELECT | Data_Proveedor.RecordSource = "SELECT * FROM proveedor WHERE… |
| stock_consulta_avanzada.frm | 2691 | SELECT | rs_proveedor.Open "SELECT proveedor.Codigo,proveedor.Nombre … |
| stock_consulta_avanzada.frm | 2838 | SELECT | rs_proveedor.Open "SELECT proveedor.Codigo,proveedor.Nombre … |
| stock_consulta_avanzada.frm | 3814 | SELECT | rs_proveedor.Open "SELECT * FROM proveedor WHERE Codigo = " … |
| stock_consulta_avanzada.frm | 3899 | SELECT | '    rs_proveedor.Open "SELECT * FROM proveedor WHERE Codigo… |
| VariacionPrecio.frm | 8869 | SELECT | DataProveedor.RecordSource = "SELECT * FROM proveedor WHERE … |
| … | … | … | *(256 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 1462 | JOIN | LEFT JOIN proveedor prov ON prov.Codigo = c.codigo_prov |
| services/query_runner.py | 3283 | JOIN | LEFT JOIN proveedor prov ON prov.Codigo = cp.Codigo |

[← Índice de tablas](../DB_INDICE_TABLAS.md)