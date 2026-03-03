# Tabla `cond_venta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Codigo | INT | No | ✓ |  |  |
| Descripcion | VARCHAR | Sí |  |  |  |
| Dias | INT | Sí |  |  |  |
| tipo_cv | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| descuento | DECIMAL | Sí |  |  |  |
| interes | DECIMAL | Sí |  |  |  |
| tipo_cond_elect | VARCHAR | Sí |  |  |  |
| tipo_pago_elect | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 11229 | SELECT | Visualiza_FA.DataCV.RecordSource = "select * from Cond_Venta… |
| Visualiza_ReciboCobro.frm | 11601 | SELECT | Visualiza_FB.DataCV.RecordSource = "select * from Cond_Venta… |
| Visualiza_ReciboCobro.frm | 12502 | SELECT | Visualiza_TPV.DataCV.RecordSource = "select * from Cond_Vent… |
| FacturaB_COPIA.frm | 3494 | SELECT | rs_cv_consulta.Open "SELECT * FROM cond_venta WHERE Codigo =… |
| FacturaB_COPIA.frm | 4208 | SELECT | rs_cv.Open "select * from cond_venta where Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 4232 | SELECT | rs_cv.Open "select * from cond_venta where Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 8151 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 8386 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 8474 | SELECT | DataCV.RecordSource = "SELECT * FROM cond_venta ORDER BY Cod… |
| FacturaB_COPIA.frm | 8486 | SELECT | '    DataCV.RecordSource = "select * from Cond_Venta WHERE C… |
| FacturaB_COPIA.frm | 8538 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 8695 | SELECT | DataCV.RecordSource = "SELECT * FROM cond_venta WHERE Codigo… |
| FacturaB_COPIA.frm | 8703 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| FacturaB_COPIA.frm | 15704 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| FacturaB_COPIA.frm | 18559 | SELECT | rs_consulta_cv.Open "SELECT cond_venta.codigo,cond_venta.tip… |
| Visualiza_TPV.frm | 6039 | SELECT | DataCV.RecordSource = "SELECT * FROM cond_venta WHERE Codigo… |
| TPV.frm | 6329 | SELECT | rs_cond_venta.Open "SELECT * FROM cond_venta WHERE Codigo = … |
| TPV.frm | 9066 | SELECT | rs_cond_venta.Open "SELECT * FROM cond_venta WHERE Codigo = … |
| TPV.frm | 9380 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| TPV.frm | 10035 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| TPV.frm | 12683 | SELECT | DataCV.RecordSource = "SELECT * FROM cond_venta WHERE anulad… |
| TPV.frm | 24403 | SELECT | '    rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_v… |
| TPV.frm | 24445 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| TPV.frm | 24478 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| TPV.frm | 24512 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| TPV.frm | 38386 | SELECT | rs_consulta_cv.Open "SELECT cond_venta.codigo,cond_venta.tip… |
| TPV.frm | 38779 | SELECT | '    rs_consulta_cv.Open "SELECT cond_venta.codigo,cond_vent… |
| CuentaCliente.frm | 2970 | SELECT | Visualiza_TPV.DataCV.RecordSource = "select * from cond_vent… |
| Logi_Gestion2.frm | 7204 | SELECT | FacturaA.DataCV.RecordSource = "select * from Cond_Venta ord… |
| Logi_Gestion2.frm | 7212 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion2.frm | 7746 | SELECT | '                rs_cond_venta.Open "SELECT * FROM cond_vent… |
| Logi_Gestion2.frm | 7957 | SELECT | FacturaB.DataCV.RecordSource = "select * from Cond_Venta ord… |
| Logi_Gestion2.frm | 7965 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion2.frm | 8302 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion2.frm | 8342 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion2.frm | 8464 | SELECT | FacturaA.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Logi_Gestion2.frm | 8501 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion2.frm | 8786 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Logi_Gestion2.frm | 8798 | SELECT | '    DataCV.RecordSource = "select * from Cond_Venta WHERE C… |
| Logi_Gestion2.frm | 8852 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion2.frm | 8997 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta WHE… |
| Logi_Gestion2.frm | 9005 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion2.frm | 10141 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Facturacion_Ciclica.frm | 2897 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Facturacion_Ciclica.frm | 2935 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Facturacion_Ciclica.frm | 3065 | SELECT | FacturaA.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Facturacion_Ciclica.frm | 3102 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Facturacion_Ciclica.frm | 3430 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Facturacion_Ciclica.frm | 3442 | SELECT | '    DataCV.RecordSource = "select * from Cond_Venta WHERE C… |
| Facturacion_Ciclica.frm | 3496 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Facturacion_Ciclica.frm | 3687 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta WHE… |
| Facturacion_Ciclica.frm | 3695 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Facturacion_Ciclica.frm | 3817 | SELECT | '        rs_consulta.Open "SELECT * FROM cond_venta WHERE co… |
| Visualiza_Pedido.frm | 6054 | SELECT | '    rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " &… |
| Visualiza_Pedido.frm | 6063 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & CV.B… |
| Visualiza_Pedido.frm | 6320 | SELECT | DataCV.RecordSource = "select * from Cond_Venta order by Cod… |
| Visualiza_Pedido.frm | 6332 | SELECT | '    DataCV.RecordSource = "select * from Cond_Venta WHERE C… |
| Visualiza_Pedido.frm | 6361 | SELECT | 'DataCV.RecordSource = "select * from Cond_Venta order by Co… |
| Visualiza_Pedido.frm | 12415 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion.frm | 8723 | SELECT | FacturaA.DataCV.RecordSource = "select * from Cond_Venta ord… |
| Logi_Gestion.frm | 8731 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion.frm | 9265 | SELECT | '                rs_cond_venta.Open "SELECT * FROM cond_vent… |
| Logi_Gestion.frm | 9472 | SELECT | FacturaB.DataCV.RecordSource = "select * from Cond_Venta ord… |
| Logi_Gestion.frm | 9480 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion.frm | 9846 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion.frm | 9886 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| Logi_Gestion.frm | 10011 | SELECT | FacturaA.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Logi_Gestion.frm | 10048 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion.frm | 10366 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta ORD… |
| Logi_Gestion.frm | 10378 | SELECT | '    DataCV.RecordSource = "select * from Cond_Venta WHERE C… |
| Logi_Gestion.frm | 10432 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion.frm | 10613 | SELECT | FacturaB.DataCV.RecordSource = "SELECT * FROM cond_venta WHE… |
| Logi_Gestion.frm | 10621 | SELECT | rs_cv.Open "SELECT * FROM cond_venta WHERE Codigo = " & Fact… |
| Logi_Gestion.frm | 11805 | SELECT | rs_consulta.Open "SELECT * FROM cond_venta WHERE cond_venta.… |
| OrdenPago.frm | 15426 | SELECT | Visualiza_PFactura.DataCV.RecordSource = "select * from cond… |
| trz_trazabilidad.frm | 4004 | SELECT | Visualiza_FA.DataCV.RecordSource = "select * from Cond_Venta… |
| trz_trazabilidad.frm | 4445 | SELECT | Visualiza_FB.DataCV.RecordSource = "select * from Cond_Venta… |
| trz_trazabilidad.frm | 5449 | SELECT | Visualiza_Presupuesto.DataCV.RecordSource = "select * from C… |
| trz_trazabilidad.frm | 5738 | SELECT | Visualiza_Pedido.DataCV.RecordSource = "select * from Cond_V… |
| trz_trazabilidad.frm | 6809 | SELECT | Visualiza_TPV.DataCV.RecordSource = "select * from Cond_Vent… |
| … | … | … | *(257 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)