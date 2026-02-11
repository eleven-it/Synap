# Tabla `cuenta_banco`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodCuenta | INT | No | ✓ |  |  |
| CodBanco | INT | Sí |  |  |  |
| NroCuenta | VARCHAR | Sí |  |  |  |
| TipoCuenta | VARCHAR | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| moneda | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| cbu | VARCHAR | Sí |  |  |  |
| utiliza_afip_fact_credito | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1387 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaBDeposito.frm | 1612 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaBDeposito.frm | 2339 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| CargaBDeposito.frm | 2425 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| Visualiza_ReciboCobro.frm | 6477 | SELECT | '                rs_cuenta_banco.Open "SELECT * FROM cuenta_… |
| Visualiza_ReciboCobro.frm | 6518 | SELECT | '                    .Source = "select cuenta_banco.CodCuent… |
| Visualiza_ReciboCobro.frm | 9348 | SELECT | "FROM cuenta_banco,banco WHERE " & _ |
| Visualiza_ReciboCobro.frm | 9453 | JOIN | '        " INNER JOIN cuenta_banco ON (cuenta_banco.codcuent… |
| Visualiza_ReciboCobro.frm | 12814 | JOIN | " INNER JOIN cuenta_banco ON (cuenta_banco.codcuenta = trans… |
| Visualiza_ReciboCobro.frm | 13513 | SELECT | rs_CtaBanc.Open "SELECT * from cuenta_banco where codcuenta … |
| Visualiza_ReciboCobro.frm | 14516 | SELECT | rs_CtaBanc.Open "SELECT * from cuenta_banco where codcuenta … |
| Visualiza_ReciboCobro.frm | 15873 | JOIN | " INNER JOIN cuenta_banco ON (cuenta_banco.codcuenta = trans… |
| Info_Estadistica.frm | 3727 | SELECT | '                                      " FROM cuenta_banco",… |
| Info_Estadistica.frm | 3736 | SELECT | '                                          " FROM cuenta_ban… |
| Info_Estadistica.frm | 3995 | SELECT | " FROM cuenta_banco", conn, adOpenDynamic, adLockOptimistic |
| Info_Estadistica.frm | 5937 | SELECT | Data_Cta_Banc.RecordSource = "select Cuenta_Banco.CodCuenta,… |
| ml_consulta_indices.frm | 290 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| CuentaCliente.frm | 2397 | SELECT | '        Visualiza_ReciboCobro.Data_Cta_Banc.RecordSource = … |
| OrdenPago.frm | 7005 | SELECT | '            rs_cuenta_banco.Open "SELECT * FROM cuenta_banc… |
| OrdenPago.frm | 7080 | SELECT | rs_cuenta_banco.Open "SELECT * FROM cuenta_banco WHERE CodCu… |
| OrdenPago.frm | 7146 | SELECT | '                .Source = "select cuenta_banco.CodCuenta,cu… |
| OrdenPago.frm | 10220 | SELECT | '    Data_Cta_Banc.RecordSource = "select Cuenta_Banco.CodCu… |
| OrdenPago.frm | 10867 | SELECT | rs_ultimocheque.Open "SELECT * FROM cuenta_banco WHERE CodCu… |
| OrdenPago.frm | 13733 | SELECT | rs_vect.Open "SELECT * from cuenta_banco where codcuenta = "… |
| OrdenPago.frm | 13881 | SELECT | '            rs_CtaBanc.Open "SELECT * from cuenta_banco whe… |
| OrdenPago.frm | 16507 | JOIN | " INNER JOIN cuenta_banco ON (cuenta_banco.codcuenta = trans… |
| trz_trazabilidad.frm | 7499 | SELECT | '            Visualiza_ReciboCobro.Data_Cta_Banc.RecordSourc… |
| ABMChequeras.frm | 798 | SELECT | DataCuentaBanco.RecordSource = "select * from Cuenta_Banco w… |
| Info_Banco.frm | 2817 | SELECT | " FROM cuenta_banco", conn, adOpenDynamic, adLockOptimistic |
| Info_Banco.frm | 2826 | SELECT | " FROM cuenta_banco where CodCuenta = " & CtaBanc.BoundText … |
| Info_Banco.frm | 3115 | SELECT | "FROM cuenta_banco,banco WHERE " & _ |
| Info_Banco.frm | 3129 | SELECT | DetaCtaBanc.RecordSource = "select Cuenta_Banco.CodCuenta,Cu… |
| CargaExtraccion.frm | 685 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaExtraccion.frm | 1090 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| CargaGastoBancario.frm | 1012 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaGastoBancario.frm | 1854 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| CargaCtaBanc.frm | 383 | SELECT | rs_consulta.Open "SELECT * FROM cuenta_banco WHERE utiliza_a… |
| CargaCtaBanc.frm | 399 | SELECT | rs_ctaBancBusq.Open "SELECT * FROM cuenta_banco WHERE NroCue… |
| CargaCtaBanc.frm | 408 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaCtaBanc.frm | 431 | SELECT | ABMChequera.DataCuentaBanco.RecordSource = "SELECT * FROM cu… |
| CargaCtaBanc.frm | 444 | SELECT | rs_ctaBancBusq.Open "SELECT * FROM cuenta_banco WHERE NroCue… |
| CargaCtaBanc.frm | 452 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaCtaBanc.frm | 473 | SELECT | ABMChequera.DataCuentaBanco.RecordSource = "SELECT * FROM cu… |
| Carga_Transferencia_REC_OP.frm | 776 | JOIN | '    " INNER JOIN cuenta_banco ON (cuenta_banco.codcuenta = … |
| Carga_Transferencia_REC_OP.frm | 861 | SELECT | "FROM cuenta_banco,banco WHERE " & _ |
| ConsultaComprobante.frm | 11850 | SELECT | rs_cuenta_banco.Open "SELECT saldo,CodBanco,CodCuenta FROM c… |
| ConsultaComprobante.frm | 11891 | SELECT | rs_cuenta_banco.Open "SELECT saldo,CodBanco,CodCuenta FROM c… |
| ConsultaComprobante.frm | 12966 | SELECT | rs_cuenta_banco.Open "SELECT saldo,CodBanco,CodCuenta FROM c… |
| ConsultaComprobante.frm | 13007 | SELECT | rs_cuenta_banco.Open "SELECT saldo,CodBanco,CodCuenta FROM c… |
| ConsultaComprobante.frm | 13044 | SELECT | '                rs_cuenta_banco.Open "SELECT saldo,CodBanco… |
| ConsultaComprobante.frm | 16451 | SELECT | rs_transferencia_banco.Open "select cuenta_banco.CodCuenta,c… |
| ConsultaComprobante.frm | 30857 | SELECT | .Source = "select cuenta_banco.CodCuenta,cuenta_banco.CodBan… |
| ConsultaComprobante.frm | 30870 | JOIN | " INNER JOIN cuenta_banco ON (cuenta_banco.codcuenta = trans… |
| CargaLiquidacionTC.frm | 1642 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaLiquidacionTC.frm | 2455 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| ListaCheqEmitidos.frm | 911 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| ListaCheqEmitidos.frm | 923 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| ListaCheqEmitidos.frm | 941 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| ListaCheqEmitidos.frm | 954 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| ListaCheqEmitidos.frm | 967 | JOIN | "LEFT JOIN cuenta_banco ON cuenta_banco.CodCuenta = chequepr… |
| CargaClearing.frm | 582 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaClearing.frm | 742 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaClearing.frm | 1150 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| CargaClearing.frm | 1218 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| CargaTransBancaria.frm | 844 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaTransBancaria.frm | 876 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaTransBancaria.frm | 965 | SELECT | data_CtaBanc.RecordSource = "SELECT * from Cuenta_Banco WHER… |
| CargaTransBancaria.frm | 1283 | SELECT | rs_bancorigen.Open "SELECT * from cuenta_banco where codcuen… |
| CargaTransBancaria.frm | 1285 | SELECT | rs_bancodestino.Open "SELECT * from cuenta_banco where codcu… |
| trz_trazabilidadComp.frm | 4979 | SELECT | '        Visualiza_OrdenPago.Data_Cta_Banc.RecordSource = "s… |
| Visualiza_OrdenPagoC.frm | 7276 | SELECT | Data_Cta_Banc.RecordSource = "select Cuenta_Banco.CodCuenta,… |
| Visualiza_OrdenPagoC.frm | 9839 | SELECT | rs_CtaBanc.Open "SELECT * from cuenta_banco where codcuenta … |
| CargaDeudaBancaria.frm | 877 | SELECT | rs_CuentaBanco.Open "SELECT * FROM cuenta_banco WHERE CodCue… |
| CargaDeudaBancaria.frm | 1501 | SELECT | rs_banco.Open "SELECT * from cuenta_banco where codcuenta = … |
| ReciboCobro.frm | 6913 | SELECT | rs_cuenta_banco.Open "SELECT * FROM cuenta_banco WHERE CodCu… |
| ReciboCobro.frm | 10021 | SELECT | "FROM cuenta_banco,banco WHERE " & _ |
| ReciboCobro.frm | 14335 | SELECT | '                    rs_CtaBanc.Open "SELECT * from cuenta_b… |
| ReciboCobro.frm | 14397 | SELECT | rs_vect.Open "SELECT * from cuenta_banco where codcuenta = "… |
| ReciboCobro.frm | 14537 | SELECT | '            rs_CtaBanc.Open "SELECT * from cuenta_banco whe… |
| ReciboCobro.frm | 15564 | SELECT | rs_CtaBanc.Open "SELECT * from cuenta_banco where codcuenta … |
| … | … | … | *(40 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)