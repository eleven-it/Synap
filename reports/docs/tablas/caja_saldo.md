# Tabla `caja_saldo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_caja_saldo | INT | No | ✓ |  |  |
| id_caja | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| cod_sucursal | INT | Sí |  |  |  |
| moneda | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1416 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaBDeposito.frm | 1640 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaBDeposito.frm | 2221 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| PNotaCred.frm | 3370 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 6577 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 6628 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 6933 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 7054 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 7149 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 7260 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_ReciboCobro.frm | 7397 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Info_Estadistica.frm | 3693 | SELECT | '                                  " FROM `caja_saldo`" & _ |
| Info_Estadistica.frm | 3961 | SELECT | " FROM `caja_saldo`" & _ |
| NotaCredCon.frm | 2774 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| FacturaB_COPIA.frm | 4304 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| NotaCred_COPIA.frm | 3736 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ChequeTercero.frm | 2174 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ChequeTercero.frm | 2223 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 6819 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 7365 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 7476 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 9220 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 9954 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 10087 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 37853 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| TPV.frm | 37992 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 1964 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 2219 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 2226 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 2238 | SELECT | '                    rs_saldo_caja.Open "SELECT * FROM caja_… |
| CargaMovCaja.frm | 2240 | SELECT | '                    rs_saldo_caja.Open "SELECT * FROM caja_… |
| CargaMovCaja.frm | 2247 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 2251 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 2255 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3706 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3719 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3721 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3737 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3752 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 3767 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| CargaMovCaja.frm | 4866 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| OrdenPago.frm | 7200 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| OrdenPago.frm | 7255 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| OrdenPago.frm | 7554 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| OrdenPago.frm | 8058 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| OrdenPago.frm | 8158 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_PNotaCred_Importe.frm | 2219 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Info_Banco.frm | 2783 | SELECT | " FROM `caja_saldo`" & _ |
| Caja_Control_Sucursales_Rend.frm | 901 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_PNotaCredDev.frm | 2889 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| FacturaB.frm | 5334 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| FacturaB.frm | 8165 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Clave_Supervisor.frm | 701 | JOIN | '                        " LEFT JOIN caja_saldo ON (caja_sal… |
| CargaExtraccion.frm | 712 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| NotaCred_SinCompO.frm | 4703 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| FacturaA.frm | 5045 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| PNotaDebCopia.frm | 5284 | SELECT | '                        rs_saldo_caja.Open "SELECT * FROM c… |
| NotaCred_Importe.frm | 2370 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Caja_Arqueo.frm | 2013 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| NotaCredCopia.frm | 4307 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2084 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| PFactura.frm | 4366 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| PFactura.frm | 4368 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 6293 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 6841 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 7854 | SELECT | '            rs_saldo_caja.Open "SELECT * FROM caja_saldo WH… |
| ConsultaComprobante.frm | 8304 | SELECT | '                    rs_saldo_caja.Open "SELECT * FROM caja_… |
| ConsultaComprobante.frm | 9013 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 10864 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 10990 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 11086 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 11657 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 11777 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 11980 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 12079 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 12759 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 12897 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 13192 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 13291 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| ConsultaComprobante.frm | 18983 | SELECT | rs_saldo_caja.Open "SELECT * FROM caja_saldo WHERE id_caja =… |
| … | … | … | *(62 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)