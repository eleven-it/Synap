# Tabla `contribuyentes`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDIva | INT | No | ✓ |  |  |
| IVA | VARCHAR | Sí |  |  |  |
| Abreviado | VARCHAR | Sí |  |  |  |
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
| Visualiza_ReciboCobro.frm | 12323 | SELECT | rs_contribuyente.Open "SELECT * FROM contribuyentes WHERE ID… |
| Visualiza_NotaCred.frm | 2498 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_NotaCred.frm | 2702 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_NotaCred.frm | 3019 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 3573 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 3895 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 4382 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 4645 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 4903 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 5148 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 5381 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 7806 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 9272 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 10442 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredCon.frm | 10993 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 5562 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 6071 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 6413 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 6704 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 12680 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 13499 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 14686 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB_COPIA.frm | 18109 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 2938 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 3223 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 4845 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 5096 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 5349 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 5593 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 5840 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 6082 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 7599 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 8255 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCredDesc.frm | 8792 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 4496 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 5055 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 5307 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 5679 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 5915 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 9381 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 9993 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| NotaCred_COPIA.frm | 13112 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_TPV.frm | 7776 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_TPV.frm | 7966 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_TPV.frm | 8251 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_TPV.frm | 8411 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 17332 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 17586 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 17960 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 18202 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 21603 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 22494 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 23229 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 23844 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 26357 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 27518 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 28594 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 29745 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 30887 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 32447 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 32763 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 33098 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 36622 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| TPV.frm | 36945 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| CuentaCliente.frm | 2754 | SELECT | rs_contribuyente.Open "SELECT * FROM contribuyentes WHERE ID… |
| Facturacion_Ciclica.frm | 2826 | JOIN | "LEFT JOIN contribuyentes ON (contribuyentes.idIVA = cliente… |
| Facturacion_Ciclica.frm | 2841 | JOIN | "LEFT JOIN contribuyentes ON (contribuyentes.idIVA = cliente… |
| Visualiza_Pedido.frm | 10630 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| trz_trazabilidad.frm | 6583 | SELECT | rs_contribuyente.Open "SELECT * FROM contribuyentes WHERE ID… |
| Visualiza_POrden_Compra.frm | 3783 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_FB_Copia.frm | 3332 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_FB_Copia.frm | 3532 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| Visualiza_FB_Copia.frm | 3732 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| POrden_CompraCopia.frm | 3371 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 10128 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 10496 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 10855 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 11164 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 11468 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| FacturaB.frm | 18522 | SELECT | rs_informe.Open "select * from contribuyentes where idIVA = … |
| … | … | … | *(193 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)