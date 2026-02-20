# Tabla `chequetercero`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ID | DOUBLE | No | ✓ |  |  |
| NroCheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| CodCliente | INT | Sí |  |  |  |
| CodProveedor | INT | Sí |  |  |  |
| Librador | VARCHAR | Sí |  |  |  |
| FechaEmision | DATE | Sí |  |  |  |
| FechaCobro | DATE | Sí |  |  |  |
| FechaVto | DATE | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| NroCompREC | VARCHAR | Sí |  |  |  |
| NroCompOP | VARCHAR | Sí |  |  |  |
| CUITLibrador | VARCHAR | Sí |  |  |  |
| Entregado | VARCHAR | Sí |  |  |  |
| Rechazado | CHAR | Sí |  |  |  |
| Encartera | CHAR | Sí |  |  |  |
| Depositado | CHAR | Sí |  |  |  |
| en_nd_cliente | CHAR | Sí |  |  |  |
| en_nd_proveedor | CHAR | Sí |  |  |  |
| CodBancoDep | INT | Sí |  |  |  |
| NroCuentaDep | INT | Sí |  |  |  |
| CodigoMovimientoREC | DECIMAL | Sí |  |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| id_boletadeposito | DOUBLE | Sí |  |  |  |
| reemplazado | VARCHAR | Sí |  |  |  |
| cobrado_efectivo | VARCHAR | Sí |  |  |  |
| id_caja | BIGINT | Sí |  |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1591 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| CargaBDeposito.frm | 1997 | SELECT | rs_consulta.Open "select chequetercero.*, banco.Nombre as Ba… |
| CargaBDeposito.frm | 2072 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| Visualiza_ReciboCobro.frm | 6907 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero where ID … |
| Visualiza_ReciboCobro.frm | 12611 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| Info_Estadistica.frm | 3844 | SELECT | '                                     "Set reporte_flujofond… |
| Info_Estadistica.frm | 4087 | SELECT | "Set reporte_flujofondos_temp.imp_depcheque = (SELECT sum(ch… |
| NotaCredCon.frm | 3083 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| FacturaB_COPIA.frm | 11139 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| FacturaB_COPIA.frm | 11164 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| ChequeTercero.frm | 1995 | SELECT | rs_cheque.Open "SELECT * FROM chequetercero WHERE ID = " & D… |
| ChequeTercero.frm | 2026 | SELECT | rs_cheque.Open "SELECT * FROM chequetercero WHERE ID = " & D… |
| ChequeTercero.frm | 2259 | SELECT | rs_cheque.Open "SELECT * FROM chequetercero WHERE ID = " & D… |
| ChequeTercero.frm | 2370 | SELECT | sql_busqueda = " FROM chequetercero " & _ |
| ChequeTercero.frm | 2409 | SELECT | sql_busqueda = "FROM chequetercero " & _ |
| ChequeTercero.frm | 2448 | SELECT | sql_busqueda = "FROM chequetercero " & _ |
| ChequeTercero.frm | 2487 | SELECT | sql_busqueda = " FROM ChequeTercero,Banco,Proveedor,cliente … |
| ChequeTercero.frm | 2526 | SELECT | sql_busqueda = " FROM chequetercero,banco,cliente " & _ |
| TPV.frm | 7413 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| TPV.frm | 9928 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero where ID … |
| TPV.frm | 26177 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| TPV.frm | 26202 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| TPV.frm | 33610 | SELECT | '                            rs_limitescli.Open "SELECT SUM(… |
| TPV.frm | 33635 | SELECT | '                            rs_limitescli.Open "SELECT SUM(… |
| CuentaCliente.frm | 3051 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| CuentaCliente.frm | 3338 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| CargaMovCaja.frm | 2203 | UPDATE | conn.Execute "UPDATE chequetercero SET entregado = 'No', rec… |
| CargaMovCaja.frm | 3300 | SELECT | rs_consulta.Open "SELECT chequetercero.*,`banco`.`Nombre` as… |
| Visualiza_Pedido.frm | 9517 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Visualiza_Pedido.frm | 9543 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| OrdenPago.frm | 7536 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| trz_trazabilidad.frm | 6890 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| Info_Banco.frm | 1933 | SELECT | "From chequetercero " & _ |
| Info_Banco.frm | 2934 | SELECT | "Set reporte_flujofondos_temp.imp_depcheque = (SELECT sum(ch… |
| Visualiza_FB_Copia.frm | 6563 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Visualiza_FB_Copia.frm | 6588 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| FacturaB.frm | 16947 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| FacturaB.frm | 16972 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| FacturaA.frm | 13026 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| FacturaA.frm | 13051 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| CambioFechaCheq.frm | 592 | UPDATE | conn.Execute "Update chequetercero " & _ |
| PNotaDebCopia.frm | 2008 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| PNotaDebCopia.frm | 3512 | JOIN | "LEFT JOIN chequetercero ON (chequetercero.ID = caja.id_cheq… |
| NotaCred_Importe.frm | 2679 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| Visualiza_FA.frm | 6399 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Visualiza_FA.frm | 6424 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Visualiza_FB.frm | 7098 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Visualiza_FB.frm | 7123 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Pedido.frm | 3979 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Pedido.frm | 4005 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Pedido.frm | 10613 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Pedido.frm | 10639 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| ConsultaComprobante.frm | 9786 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| ConsultaComprobante.frm | 10927 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| ConsultaComprobante.frm | 11351 | SELECT | rs_validacion.Open "SELECT * FROM chequetercero WHERE anulad… |
| ConsultaComprobante.frm | 11360 | SELECT | rs_validacion.Open "SELECT * FROM chequetercero WHERE anulad… |
| ConsultaComprobante.frm | 11588 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| ConsultaComprobante.frm | 12365 | SELECT | rs_validacion.Open "SELECT * FROM ChequeTercero WHERE Anulad… |
| ConsultaComprobante.frm | 12725 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| ConsultaComprobante.frm | 20584 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| NotaDeb.frm | 2857 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| NotaDeb.frm | 7816 | JOIN | "LEFT JOIN chequetercero ON (chequetercero.ID = caja.id_cheq… |
| NotaDeb.frm | 14304 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE Cod… |
| CargaClearing.frm | 766 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID=… |
| trz_trazabilidadComp.frm | 4853 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE che… |
| Carga_Cliente.frm | 6628 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| Carga_Cliente.frm | 6648 | SELECT | rs_limitescli.Open "SELECT SUM(ChequeTercero.Importe) as Imp… |
| PNotaDeb.frm | 2102 | SELECT | rs_chequetercero.Open "SELECT * FROM chequetercero WHERE ID … |
| PNotaDeb.frm | 3718 | JOIN | "LEFT JOIN chequetercero ON (chequetercero.ID = caja.id_cheq… |
| ListaCheque3.frm | 809 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 821 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 832 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 843 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 854 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 870 | SELECT | ''    DataChequeTercero.RecordSource = "select chequetercero… |
| ListaCheque3.frm | 873 | SELECT | '    DataChequeTercero.RecordSource = "SELECT chequetercero.… |
| ListaCheque3.frm | 892 | SELECT | '    DataChequeTercero.RecordSource = "select chequetercero.… |
| ListaCheque3.frm | 900 | SELECT | '    DataChequeTercero.RecordSource = "SELECT chequetercero.… |
| ListaCheque3.frm | 944 | SELECT | '                "From chequetercero " & _ |
| ListaCheque3.frm | 1131 | SELECT | DataChequeTercero.RecordSource = "SELECT chequetercero.*, ba… |
| … | … | … | *(37 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)