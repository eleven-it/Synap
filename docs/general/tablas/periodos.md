# Tabla `periodos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_periodo | INT | No | ✓ |  |  |
| id_year | INT | Sí |  |  |  |
| mes_periodo | VARCHAR | Sí |  |  |  |
| inicio_periodo | DATE | Sí |  |  |  |
| fin_periodo | DATE | Sí |  |  |  |
| abierto_periodo | VARCHAR | Sí |  |  |  |
| mes_numero_periodo | INT | Sí |  |  |  |
| vencimiento_fiscal_periodo | DATE | Sí |  |  |  |
| anulado_periodo | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1306 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PNotaCred.frm | 2649 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PNotaCred.frm | 2670 | SELECT | '                rs_consulta_periodo_fiscal.Open "SELECT per… |
| PNotaCred.frm | 5900 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_ReciboCobro.frm | 6157 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_ReciboCobro.frm | 10127 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_ReciboCobro.frm | 12745 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_NotaCred.frm | 4844 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_CargaMovStock.frm | 5810 | SELECT | '    rs_consulta_periodo_fiscal.Open "SELECT periodos.*,year… |
| Visualiza_CargaMovStock.frm | 5831 | SELECT | '    rs_consulta_periodo_fiscal.Open "SELECT periodos.*,year… |
| NotaCredCon.frm | 1731 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCredCon.frm | 6457 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaDeb.frm | 2835 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaDeb.frm | 2856 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| FacturaB_COPIA.frm | 3468 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| FacturaB_COPIA.frm | 10849 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCredDesc.frm | 1772 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCredDesc.frm | 3877 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_COPIA.frm | 2477 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_COPIA.frm | 7908 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_NotaCredDesc.frm | 1835 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| CargaMovCaja.frm | 1795 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| OrdenPago.frm | 6726 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| OrdenPago.frm | 12502 | SELECT | '    rs_consulta_periodo_fiscal.Open "SELECT periodos.*,year… |
| OrdenPago.frm | 12831 | SELECT | '        rs_consulta_periodo_fiscal.Open "SELECT periodos.*,… |
| Visualiza_PNotaCred_Importe.frm | 2002 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCred_Importe.frm | 2906 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCred_Importe.frm | 2927 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_POrden_Compra.frm | 6167 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_FB_Copia.frm | 6190 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| POrden_CompraCopia.frm | 5785 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PRemito.frm | 3371 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PRemito.frm | 3392 | SELECT | '        rs_consulta_periodo_fiscal.Open "SELECT periodos.*,… |
| PRemito.frm | 6361 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCredDev.frm | 2525 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCredDev.frm | 4657 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCredDev.frm | 4678 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ABMPeriodos.frm | 499 | SELECT | DataPeriodo.RecordSource = "SELECT * FROM periodos WHERE " &… |
| ABMPeriodos.frm | 537 | SELECT | DataPeriodo.RecordSource = "SELECT * FROM periodos WHERE " &… |
| ABMPeriodos.frm | 702 | UPDATE | conn.Execute "UPDATE periodos SET anulado_periodo='Si' WHERE… |
| Visualiza_PNotaCredDesc.frm | 2453 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCredDesc.frm | 2474 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| FacturaB.frm | 16657 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| CargaExtraccion.frm | 611 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_SinCompO.frm | 3192 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_SinCompO.frm | 10242 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| FacturaA.frm | 4128 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| FacturaA.frm | 12737 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_NotaDeb.frm | 3502 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PNotaDebCopia.frm | 1674 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PNotaDebCopia.frm | 1695 | SELECT | '    rs_consulta_periodo_fiscal.Open "SELECT periodos.*,year… |
| PNotaDebCopia.frm | 3189 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_Importe.frm | 1242 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCred_Importe.frm | 6007 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| CargaGastoBancario.frm | 875 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_FA.frm | 6026 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| NotaCredCopia.frm | 8756 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Remito.frm | 3888 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Remito.frm | 10131 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_NotaCred_Importe.frm | 2739 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCred_ImporteCopia.frm | 1867 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2771 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2792 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_FB.frm | 6727 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Presupuesto.frm | 8971 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PFactura.frm | 3968 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PFactura.frm | 3989 | SELECT | '        rs_consulta_periodo_fiscal.Open "SELECT periodos.*,… |
| PFactura.frm | 8319 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| PFactura.frm | 8340 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Pedido.frm | 10691 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| Visualiza_RemitoCopia.frm | 5947 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 5901 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 6622 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 7479 | SELECT | '        rs_consulta_periodo_fiscal.Open "SELECT periodos.*,… |
| ConsultaComprobante.frm | 8085 | SELECT | '            rs_consulta_periodo_fiscal.Open "SELECT periodo… |
| ConsultaComprobante.frm | 8829 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 9359 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 9664 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 10484 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| ConsultaComprobante.frm | 11310 | SELECT | rs_consulta_periodo_fiscal.Open "SELECT periodos.*,years.* F… |
| … | … | … | *(75 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)