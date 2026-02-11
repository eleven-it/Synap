# Tabla `tarjetas_credito`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| idTC | INT | No | ✓ |  |  |
| Anulado | VARCHAR | No |  |  |  |
| code | VARCHAR | Sí |  |  |  |
| nombre | VARCHAR | No |  |  |  |
| id_banco | INT | Sí |  |  |  |
| tipo_tarjeta | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| entidad_pago_elect | VARCHAR | Sí |  |  |  |
| billetera_electronica | VARCHAR | Sí |  |  |  |
| activado_mp | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| tarjetas_credito | tc_plan | ABMPlantc.frm | - | SELECT tc_plan.*, tarjetas_credito.nombre FROM tarjetas_credito right join tc_pl… |
| tarjetas_credito | tc_plan | ABMPlantc.frm | 540 | DataPlantc.RecordSource = "SELECT tc_plan.*, tarjetas_credito.nombre FROM tarjet… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| ABMTarjetaC.frm | 495 | SELECT | DataTC.RecordSource = "SELECT * FROM tarjetas_credito WHERE … |
| ABMTarjetaC.frm | 565 | SELECT | DataTC.RecordSource = "select * from tarjetas_credito order … |
| Visualiza_ReciboCobro.frm | 9365 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito order… |
| Visualiza_ReciboCobro.frm | 13025 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| Visualiza_ReciboCobro.frm | 13739 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| Visualiza_ReciboCobro.frm | 14742 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| Visualiza_TPV.frm | 6009 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito order… |
| Visualiza_TPV.frm | 6668 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| Visualiza_TPV.frm | 8676 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| Visualiza_TPV.frm | 9979 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| TPV.frm | 12648 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito where… |
| TPV.frm | 14008 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| TPV.frm | 18560 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| TPV.frm | 20297 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| TPV.frm | 37369 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| ABMPlantc.frm | 540 | SELECT | DataPlantc.RecordSource = "SELECT tc_plan.*, tarjetas_credit… |
| CargaPlantc.frm | 772 | SELECT | DataTarjetas.RecordSource = "select * from tarjetas_credito … |
| Info_Banco.frm | 3620 | SELECT | data_tarjeta.RecordSource = "SELECT idtc,nombre FROM tarjeta… |
| Exportacion.frm | 885 | JOIN | "LEFT JOIN tarjetas_credito ON (tarjetas_credito.idtc = tc_l… |
| Exportacion.frm | 961 | JOIN | "LEFT JOIN tarjetas_credito ON (tarjetas_credito.idtc = tc_l… |
| Exportacion.frm | 6518 | SELECT | "FROM tarjetas_credito " & _ |
| Exportacion.frm | 6949 | SELECT | "FROM tarjetas_credito " & _ |
| Pedido_Avanzado.frm | 6609 | SELECT | TPV.data_tc.RecordSource = "select * from tarjetas_credito o… |
| Pedido_Avanzado.frm | 7506 | SELECT | TPV.data_tc.RecordSource = "select * from tarjetas_credito o… |
| Pedido_Avanzado.frm | 9483 | SELECT | TPV.data_tc.RecordSource = "select * from tarjetas_credito o… |
| CargaLiquidacionTC.frm | 2031 | SELECT | DataListaTC.RecordSource = "select * from tarjetas_credito o… |
| CargaLiquidacionTC.frm | 2722 | SELECT | 'rs_tc.Open "SELECT * from tarjetas_credito where idTC = " &… |
| CargaTarjetaC.frm | 511 | SELECT | rs_tc.Open "SELECT * FROM tarjetas_credito WHERE Nombre = '"… |
| CargaTarjetaC.frm | 527 | SELECT | rs_tc.Open "SELECT * FROM tarjetas_credito WHERE  idTC = 0",… |
| CargaTarjetaC.frm | 538 | SELECT | '        rs_cliente_consulta.Open "SELECT * FROM tarjetas_cr… |
| CargaTarjetaC.frm | 566 | SELECT | ABMTarjetaC.DataTC.RecordSource = "SELECT * FROM tarjetas_cr… |
| CargaTarjetaC.frm | 578 | SELECT | rs_tc.Open "SELECT * FROM tarjetas_credito WHERE idTC = " & … |
| CargaTarjetaC.frm | 592 | SELECT | '        rs_cliente_consulta.Open "SELECT * FROM tarjetas_cr… |
| Lista_Comp_Fact.frm | 7590 | SELECT | TPV.data_tc.RecordSource = "select * from tarjetas_credito o… |
| ReciboCobro.frm | 10044 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito where… |
| ReciboCobro.frm | 13733 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| ReciboCobro.frm | 14773 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| ReciboCobro.frm | 15790 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| Visualiza_ReciboCobroC.frm | 9023 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito order… |
| Visualiza_ReciboCobroC.frm | 12642 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| Visualiza_ReciboCobroC.frm | 13356 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| Visualiza_ReciboCobroC.frm | 14359 | SELECT | rs_vect.Open "SELECT * from tarjetas_credito where idTC = " … |
| TPV_2.frm | 12033 | SELECT | data_tc.RecordSource = "select * from tarjetas_credito where… |
| TPV_2.frm | 13167 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| TPV_2.frm | 16685 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| TPV_2.frm | 18394 | SELECT | rs_tc.Open "SELECT * from tarjetas_credito where idTC = " & … |
| TPV_2.frm | 34749 | SELECT | rs_tarjeta.Open "SELECT * FROM tarjetas_credito WHERE idtc =… |
| Visualiza.bas | 22795 | JOIN | " LEFT JOIN tarjetas_credito ON (tarjetas_credito.idTC = caj… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)