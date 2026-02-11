# Tabla `codmov`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodigoMovimiento | DOUBLE | Sí |  |  |  |
| codigo | INT | No | ✓ |  |  |

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
| CargaBDeposito.frm | 1348 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaBDeposito.frm | 1526 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaBDeposito.frm | 1549 | SELECT | '           rs_codmov.Open "SELECT * FROM codmov WHERE codig… |
| PNotaCred.frm | 2837 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_ReciboCobro.frm | 6276 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Erp_Carga_Parte_Diario.frm | 2438 | SELECT | rs_codmov.Open "SELECT * FROM codmov WHERE codigo = 1", conn… |
| Visualiza_CargaMovStock.frm | 2908 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCredCon.frm | 1808 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| FacturaB_COPIA.frm | 3639 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCredDesc.frm | 1818 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCred_COPIA.frm | 2582 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ChequeTercero.frm | 2144 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ChequeTercero.frm | 2738 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| TPV.frm | 5757 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| TPV.frm | 8461 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Cont_ProcAsientosM.frm | 1888 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CuentaCliente.frm | 3238 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaMovCaja.frm | 1846 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_Pedido.frm | 14031 | SELECT | '            rs_codmov.Open "SELECT * FROM codmov where codi… |
| CargaArticulo_Original.frm | 12659 | SELECT | '    rs_codmov.Open "SELECT * FROM codmov where codigo = 1",… |
| OrdenPago.frm | 6837 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Imp_Carga.frm | 521 | SELECT | '            rs_codmov.Open "SELECT * FROM codmov where codi… |
| Visualiza_PNotaCred_Importe.frm | 2057 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_POrden_Compra.frm | 3449 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Caja_Control_Sucursales_Rend.frm | 853 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| POrden_CompraCopia.frm | 2933 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| PRemito.frm | 3443 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PNotaCredDev.frm | 2583 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PNotaCredDesc.frm | 1856 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PNotaCredDesc.frm | 1877 | SELECT | '                rs_CodData.Open "select * from CodMov where… |
| FacturaB.frm | 4576 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| FacturaB.frm | 7392 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaExtraccion.frm | 662 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCred_SinCompO.frm | 3287 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| FacturaA.frm | 4296 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| PNotaDebCopia.frm | 1789 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| En_GeneraOE.frm | 3173 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCred_Importe.frm | 1319 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaGastoBancario.frm | 931 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Pedido_prep.frm | 3596 | SELECT | rs_codmov.Open "SELECT * From codmov where codigo = 1", conn… |
| Visualiza_Cont_CargaAsientoM.frm | 1234 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_Cont_CargaAsientoM.frm | 1254 | SELECT | '        rs_codmov.Open "SELECT * FROM codmov where codigo =… |
| Inventario.frm | 1488 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaCredCopia.frm | 2932 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Remito.frm | 3970 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Sup_importacion_tablas.frm | 9286 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaArticulo2.frm | 12565 | SELECT | '    rs_codmov.Open "SELECT * FROM codmov where codigo = 1",… |
| Cont_CargaAsientoM.frm | 1502 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PNotaCred_ImporteCopia.frm | 1922 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Presupuesto.frm | 3726 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| PFactura.frm | 4077 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Pedido.frm | 4074 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_RemitoCopia.frm | 2869 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 5872 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 6601 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 7450 | SELECT | '            rs_codmov.Open "SELECT * FROM codmov where codi… |
| ConsultaComprobante.frm | 8064 | SELECT | '                rs_codmov.Open "SELECT * FROM codmov where … |
| ConsultaComprobante.frm | 8808 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 9338 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 9643 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 10588 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 11288 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 12323 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 18787 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 19580 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 20240 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 20437 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 21275 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| ConsultaComprobante.frm | 28612 | SELECT | '        rs_codmov.Open "SELECT * FROM codmov where codigo =… |
| ConsultaComprobante.frm | 29083 | SELECT | '        rs_codmov.Open "SELECT * FROM codmov where codigo =… |
| ConsultaComprobante.frm | 29860 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PPresupuesto.frm | 2836 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaLiquidacionTC.frm | 1540 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| NotaDeb.frm | 1891 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| PNotaCredDesc.frm | 1785 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| PPresupuesto.frm | 3268 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaClearing.frm | 541 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| CargaClearing.frm | 713 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_PFactura_Copia.frm | 3303 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| Visualiza_POrden_CompraC.frm | 2915 | SELECT | rs_codmov.Open "SELECT * FROM codmov where codigo = 1", conn… |
| … | … | … | *(67 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)