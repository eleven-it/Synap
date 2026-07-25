# Tabla `conf_grilla_final_puesto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_grilla | INT | No | ✓ |  |  |
| nombre_grilla | VARCHAR | Sí |  |  |  |
| nombre_campo | VARCHAR | Sí |  |  |  |
| index_campo | INT | Sí |  |  |  |
| activa | INT | Sí |  |  |  |
| alineacion | INT | Sí |  |  |  |
| orden | INT | Sí |  |  |  |
| ancho | INT | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| id_grilla_conf | INT | Sí |  |  |  |

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
| PNotaCred.frm | 4550 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_NotaCred.frm | 3988 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_CargaMovStock.frm | 4214 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_TPV.frm | 5803 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| TPV.frm | 38859 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Facturacion_Ciclica.frm | 3217 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Facturacion_Ciclica.frm | 3612 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_Pedido.frm | 6621 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Logi_Gestion.frm | 10152 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Logi_Gestion.frm | 10537 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Logi_Gestion.frm | 10829 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| trz_trazabilidad.frm | 4046 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| trz_trazabilidad.frm | 4488 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| trz_trazabilidad.frm | 5492 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| trz_trazabilidad.frm | 5801 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| trz_trazabilidad.frm | 6143 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ABMArticulo_seleccion.frm | 4657 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Articulo.frm | 7314 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_POrden_Compra.frm | 5171 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_FB_Copia.frm | 4866 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| POrden_CompraCopia.frm | 4856 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| PRemito.frm | 5495 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PNotaCredDev.frm | 3758 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| FacturaB.frm | 16049 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| NotaCred_SinCompO.frm | 8447 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| FacturaA.frm | 9306 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto wher… |
| FacturaA.frm | 11745 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| stock_consulta_avanzada.frm | 2410 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_FA.frm | 4530 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| NotaCredCopia.frm | 7434 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ABMArticulo_seleccion_simple.frm | 2847 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Remito.frm | 12789 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| CargaPuesto.frm | 917 | INSERT | conn.Execute "INSERT INTO `conf_grilla_final_puesto` (`id_gr… |
| CargaPuesto.frm | 973 | INSERT | conn.Execute "INSERT INTO `conf_grilla_final_puesto` (`nombr… |
| CargaPuesto.frm | 982 | SELECT | " FROM `conf_grilla_final_puesto` WHERE id_puesto = " & Pues… |
| Visualiza_FB.frm | 5319 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Presupuesto.frm | 6425 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| PFactura.frm | 7345 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Pedido.frm | 7704 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ActDatos_Articulo.frm | 4404 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto … |
| Visualiza_PPresupuesto.frm | 3959 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| CargaPermiso_Sistema_Grilla.frm | 401 | SELECT | data_grilla.RecordSource = "SELECT * FROM conf_grilla_final_… |
| PPresupuesto.frm | 4971 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ActDescuento_Prov.frm | 2333 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PFactura_Copia.frm | 5138 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_POrden_CompraC.frm | 4568 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| AltaArticulo.frm | 5111 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_NotaCredCopia.frm | 3761 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| NotaCred.frm | 7740 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_Presupuesto.frm | 6381 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| PNotaCredCopia.frm | 4414 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ReciboCobro.frm | 12363 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ReciboCobro.frm | 12792 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla_final_pue… |
| CargaMovStock.frm | 3193 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PFacturaCopia2.frm | 5277 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PFactura.frm | 5401 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PPresupuestoC.frm | 3870 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_CargaMovStock_Copia.frm | 4049 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PNotaCredDevC.frm | 3887 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PRemito.frm | 4049 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| TPV_2.frm | 36226 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| ArticuloProv.frm | 4947 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Principal.frm | 8994 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Principal.frm | 9503 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| POrden_Compra.frm | 5696 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |
| Visualiza_PRemitoC.frm | 3877 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla_final_puesto where… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)