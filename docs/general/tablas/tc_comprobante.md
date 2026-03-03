# Tabla `tc_comprobante`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tc_comprobante | DOUBLE | No | ✓ |  |  |
| nro_cupon_tc_comprobante | DECIMAL | Sí |  |  |  |
| nombre_tc_comprobante | VARCHAR | Sí |  |  |  |
| nombre_plan_tc_comprobante | VARCHAR | No |  |  |  |
| id_tc | DECIMAL | No |  |  |  |
| id_tc_plan | DECIMAL | Sí |  |  |  |
| cuotas_tc_comprobante | DECIMAL | Sí |  |  |  |
| interes_tc_comprobante | DECIMAL | Sí |  |  |  |
| descuento_tc_comprobante | DECIMAL | Sí |  |  |  |
| nro_tarjeta_tc_comprobante | VARCHAR | Sí |  |  |  |
| importe_tc_comprobante | DECIMAL | Sí |  |  |  |
| importe_cuota | DECIMAL | Sí |  |  |  |
| importe_con_interes | DECIMAL | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_tc_liquidacion | DOUBLE | Sí |  |  |  |
| nro_lote_tc | VARCHAR | Sí |  |  |  |
| id_cierre_caja | BIGINT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7032 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where i… |
| Visualiza_ReciboCobro.frm | 12648 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| Visualiza_TPV.frm | 9975 | SELECT | rs_QtarUso.Open " SELECT * from tc_comprobante where codigo_… |
| TPV.frm | 7315 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| TPV.frm | 10061 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where i… |
| TPV.frm | 11087 | SELECT | rs_cup.Open "SELECT * FROM tc_comprobante " & _ |
| TPV.frm | 20293 | SELECT | rs_QtarUso.Open " SELECT * from tc_comprobante where codigo_… |
| TPV.frm | 26046 | SELECT | '        rs_limCP.Open "SELECT nro_cupon_tc_comprobante FROM… |
| CuentaCliente.frm | 2435 | SELECT | '            rs_tarjeta.Open "SELECT * FROM tc_comprobante W… |
| CuentaCliente.frm | 3089 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| CargaMovCaja.frm | 2167 | UPDATE | conn.Execute "UPDATE tc_comprobante " & _ |
| trz_trazabilidad.frm | 6928 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| trz_trazabilidad.frm | 7547 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| ConsultaComprobante.frm | 11036 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| ConsultaComprobante.frm | 11921 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| CargaLiquidacionTC.frm | 1602 | SELECT | rs_tc_comprobante.Open "select * FROM tc_comprobante where i… |
| NotaDeb.frm | 14403 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| ListaCuponesTC.frm | 440 | SELECT | "FROM tc_comprobante " & _ |
| ListaCuponesTC.frm | 640 | SELECT | DataListaCupones.RecordSource = "select tc_comprobante.*, ca… |
| ListaCuponesTC.frm | 798 | SELECT | DataListaCupones.RecordSource = "select tc_comprobante.*, ca… |
| NotaDebCopia.frm | 14054 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| ReciboCobro.frm | 7524 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where i… |
| ReciboCobro.frm | 13406 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| ReciboCobro.frm | 13984 | SELECT | rs_cup.Open "SELECT * FROM tc_comprobante " & _ |
| ReciboCobro.frm | 16983 | SELECT | '        rs_limCP.Open "SELECT nro_cupon_tc_comprobante FROM… |
| Visualiza_ReciboCobroC.frm | 6798 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where i… |
| Visualiza_ReciboCobroC.frm | 12287 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| TPV_2.frm | 6625 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE c… |
| TPV_2.frm | 9800 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante where i… |
| TPV_2.frm | 10860 | SELECT | rs_cup.Open "SELECT * FROM tc_comprobante " & _ |
| TPV_2.frm | 18390 | SELECT | rs_QtarUso.Open " SELECT * from tc_comprobante where codigo_… |
| TPV_2.frm | 24079 | SELECT | '        rs_limCP.Open "SELECT nro_cupon_tc_comprobante FROM… |
| LibroBanco.frm | 2504 | SELECT | rs_tc_comprobante.Open "SELECT * FROM tc_comprobante WHERE i… |
| LibroBanco.frm | 4199 | SELECT | '                CargaLiquidacionTC.DataTC.RecordSource = "S… |
| LibroBanco.frm | 4204 | SELECT | '        rs_tc_comprobante.Open "select tc_comprobante.*, ca… |
| LibroBanco.frm | 4214 | SELECT | rs_tc_comprobante.Open "SELECT tc_comprobante.*, caja.*, cli… |
| LibroBanco.frm | 4220 | SELECT | '        rs_tc_comprobante.Open "SELECT * from tc_comprobant… |
| Visualiza.bas | 4146 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |
| Visualiza.bas | 6495 | SELECT | rs_tarjeta.Open "SELECT * FROM tc_comprobante WHERE codigo_m… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)