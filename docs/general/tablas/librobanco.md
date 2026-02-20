# Tabla `librobanco`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodMov | DOUBLE | No | ✓ |  |  |
| CodBanco | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| TipoComp | VARCHAR | Sí |  |  |  |
| Comprobante | VARCHAR | Sí |  |  |  |
| Fecha | DATE | Sí |  |  |  |
| Debito | DECIMAL | Sí |  |  |  |
| Credito | DECIMAL | Sí |  |  |  |
| Saldo | DECIMAL | Sí |  |  |  |
| CodCuenta | INT | Sí |  |  |  |
| FechaMov | DATE | Sí |  |  |  |
| FechaControl | TIMESTAMP | No |  |  |  |
| IdUsuario | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| id_boletadeposito | DOUBLE | Sí |  |  |  |
| id_clearing | INT | Sí |  |  |  |
| id_gastobancario | INT | Sí |  |  |  |
| id_tc_liquidacion | DOUBLE | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| conciliado | VARCHAR | Sí |  |  |  |
| fecha_conciliado | DATE | Sí |  |  |  |
| id_impuesto | INT | Sí |  |  |  |
| id_retenciones | INT | Sí |  |  |  |
| CodCuentaDestino | INT | Sí |  |  |  |
| CodigoMovimiento_Anul | DECIMAL | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| id_cheq_rechaz | INT | Sí |  |  |  |
| id_deuda | DOUBLE | Sí |  |  |  |
| id_alicuota | DOUBLE | Sí |  |  |  |
| id_percepcion | DOUBLE | Sí |  |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| id_transf | BIGINT | Sí |  |  |  |

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
| CargaBDeposito.frm | 1390 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| CargaBDeposito.frm | 1615 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| Visualiza_ReciboCobro.frm | 6473 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| Visualiza_ReciboCobro.frm | 12834 | SELECT | rs_fecha_transf_banc.Open "SELECT * FROM librobanco WHERE id… |
| OrdenPago.frm | 7001 | SELECT | '            rs_libroBanco.Open "SELECT * FROM librobanco WH… |
| OrdenPago.frm | 7076 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| OrdenPago.frm | 12880 | SELECT | '            rs_fecha_transf_banc.Open "SELECT * FROM librob… |
| CargaExtraccion.frm | 688 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov=1"… |
| Exportacion.frm | 883 | JOIN | "LEFT JOIN librobanco ON (librobanco.CodigoMovimiento = rete… |
| Exportacion.frm | 959 | JOIN | "LEFT JOIN librobanco ON (librobanco.CodigoMovimiento = rete… |
| Exportacion.frm | 6434 | JOIN | "LEFT JOIN librobanco ON (librobanco.CodigoMovimiento = otro… |
| Exportacion.frm | 6806 | JOIN | "LEFT JOIN librobanco ON (librobanco.CodigoMovimiento = otro… |
| Exportacion.frm | 6874 | JOIN | "LEFT JOIN librobanco ON (librobanco.CodigoMovimiento = otro… |
| CargaGastoBancario.frm | 1014 | SELECT | rs_libroBanco.Open "select * from librobanco where CodMov = … |
| ConsultaComprobante.frm | 11843 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| ConsultaComprobante.frm | 11883 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| ConsultaComprobante.frm | 12959 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| ConsultaComprobante.frm | 12999 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| ConsultaComprobante.frm | 13036 | SELECT | '            rs_libroBanco.Open "SELECT * FROM librobanco WH… |
| ConsultaComprobante.frm | 13065 | INSERT | ''                sentencia_tabla = "INSERT INTO librobanco … |
| CargaLiquidacionTC.frm | 1644 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| CargaClearing.frm | 585 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov= 1… |
| CargaClearing.frm | 744 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| CargaTransBancaria.frm | 846 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov=1"… |
| CargaTransBancaria.frm | 879 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov=1"… |
| Visualiza_OrdenPagoC.frm | 9070 | SELECT | rs_fecha_transf_banc.Open "SELECT * FROM librobanco WHERE Co… |
| CargaDeudaBancaria.frm | 883 | SELECT | rs_libroBanco.Open "select * from librobanco where CodMov = … |
| ReciboCobro.frm | 6909 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| ReciboCobro.frm | 13648 | SELECT | '            rs_fecha_transf_banc.Open "SELECT * FROM librob… |
| CargaAjusteLB.frm | 509 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| Visualiza_ReciboCobroC.frm | 6239 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| Visualiza_ReciboCobroC.frm | 12525 | SELECT | rs_fecha_transf_banc.Open "SELECT * FROM librobanco WHERE Co… |
| Visualiza_OrdenPago.frm | 9448 | SELECT | rs_fecha_transf_banc.Open "SELECT * FROM librobanco WHERE id… |
| LibroBanco.frm | 1160 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1166 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1180 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1187 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1202 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1209 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1224 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1234 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE codmov… |
| LibroBanco.frm | 1307 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1317 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE " & _ |
| LibroBanco.frm | 1326 | SELECT | '      DataLB.RecordSource = "SELECT * FROM librobanco WHERE… |
| LibroBanco.frm | 1347 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco WHERE codmov… |
| LibroBanco.frm | 1370 | SELECT | DataLB.RecordSource = "SELECT * FROM librobanco where CodBan… |
| LibroBanco.frm | 1805 | SELECT | ConciliacionBancaria.DataCB.RecordSource = "SELECT * FROM li… |
| LibroBanco.frm | 1817 | SELECT | rs_CredDeb.Open "SELECT SUM(librobanco.Credito) as SumaCredi… |
| LibroBanco.frm | 1984 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 2002 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 2170 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 2193 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 2405 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 2418 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 2637 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 2718 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 2843 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodigoMov… |
| LibroBanco.frm | 2864 | SELECT | rs_libroBancoAlta.Open "SELECT * FROM librobanco WHERE CodMo… |
| LibroBanco.frm | 2906 | SELECT | rs_libroBancoAlta.Open "SELECT * FROM librobanco WHERE CodMo… |
| LibroBanco.frm | 3104 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3137 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 3272 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3305 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 3440 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3466 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 3620 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3637 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 3773 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3790 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 3941 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 3958 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |
| LibroBanco.frm | 4143 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE codbanco … |
| LibroBanco.frm | 4323 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE codbanco … |
| LibroBanco.frm | 4348 | SELECT | rs_Gasto.Open "SELECT * from librobanco WHERE codigomovimien… |
| LibroBanco.frm | 4360 | SELECT | rs_impuesto.Open "SELECT * from librobanco WHERE codigomovim… |
| LibroBanco.frm | 4381 | SELECT | rs_neto.Open "SELECT * from librobanco WHERE codigomovimient… |
| LibroBanco.frm | 4518 | SELECT | rs_lbanco.Open "SELECT * from librobanco where CodigoMovimie… |
| LibroBanco.frm | 4538 | SELECT | rs_libroBanco.Open "SELECT * FROM librobanco WHERE CodMov = … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)