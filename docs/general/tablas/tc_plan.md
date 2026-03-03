# Tabla `tc_plan`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Id_tc_plan | DOUBLE | No | ✓ |  |  |
| nombre_tc_plan | VARCHAR | Sí |  |  |  |
| cuotas_tc_plan_desde | INT | Sí |  |  |  |
| cuotas_tc_plan_hasta | INT | Sí |  |  |  |
| idTC | INT | Sí |  |  |  |
| interes_total_tc_plan | DECIMAL | Sí |  |  |  |
| fecha_plan | DATE | Sí |  |  |  |
| vencimiento_plan | DATE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| descuento_tc_plan | DECIMAL | Sí |  |  |  |
| modo | VARCHAR | Sí |  |  |  |
| monto_cupon | DECIMAL | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 9377 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| Visualiza_ReciboCobro.frm | 13008 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| Visualiza_ReciboCobro.frm | 13120 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| Visualiza_TPV.frm | 5477 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| Visualiza_TPV.frm | 6021 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| Visualiza_TPV.frm | 6651 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| TPV.frm | 11066 | SELECT | rs_esCupon.Open "SELECT modo FROM tc_plan WHERE id_tc_plan =… |
| TPV.frm | 11756 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| TPV.frm | 12663 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE anu… |
| TPV.frm | 13989 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| TPV.frm | 26039 | SELECT | rs_cuponP.Open "SELECT * FROM tc_plan WHERE anulado = 'No' A… |
| ABMPlantc.frm | 495 | SELECT | DataPlantc.RecordSource = "SELECT * FROM tc_plan WHERE nombr… |
| ABMPlantc.frm | 540 | JOIN | DataPlantc.RecordSource = "SELECT tc_plan.*, tarjetas_credit… |
| CargaPlantc.frm | 656 | SELECT | rs_plan.Open "SELECT * FROM tc_plan WHERE Nombre_tc_plan = '… |
| CargaPlantc.frm | 672 | SELECT | rs_plan.Open "SELECT * FROM tc_plan WHERE  id_tc_plan = 0", … |
| CargaPlantc.frm | 712 | SELECT | rs_plan.Open "SELECT * FROM tc_plan WHERE id_tc_plan = " & A… |
| Pedido_Avanzado.frm | 6620 | SELECT | TPV.data_plan_tc.RecordSource = "select * from tc_plan WHERE… |
| Pedido_Avanzado.frm | 7517 | SELECT | TPV.data_plan_tc.RecordSource = "select * from tc_plan WHERE… |
| Pedido_Avanzado.frm | 9494 | SELECT | TPV.data_plan_tc.RecordSource = "select * from tc_plan WHERE… |
| Lista_Comp_Fact.frm | 7601 | SELECT | TPV.data_plan_tc.RecordSource = "select * from tc_plan WHERE… |
| ReciboCobro.frm | 10056 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| ReciboCobro.frm | 13716 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| ReciboCobro.frm | 13838 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| ReciboCobro.frm | 13963 | SELECT | rs_esCupon.Open "SELECT modo FROM tc_plan WHERE id_tc_plan =… |
| ReciboCobro.frm | 16976 | SELECT | rs_cuponP.Open "SELECT * FROM tc_plan WHERE anulado = 'No' A… |
| Visualiza_ReciboCobroC.frm | 9035 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| Visualiza_ReciboCobroC.frm | 12625 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| Visualiza_ReciboCobroC.frm | 12737 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| TPV_2.frm | 10839 | SELECT | rs_esCupon.Open "SELECT modo FROM tc_plan WHERE id_tc_plan =… |
| TPV_2.frm | 11350 | SELECT | rs_plan_tarjeta.Open "SELECT * FROM tc_plan WHERE Id_tc_plan… |
| TPV_2.frm | 12048 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE anu… |
| TPV_2.frm | 13148 | SELECT | data_plan_tc.RecordSource = "select * from tc_plan WHERE idT… |
| TPV_2.frm | 24072 | SELECT | rs_cuponP.Open "SELECT * FROM tc_plan WHERE anulado = 'No' A… |
| Visualiza.bas | 22796 | JOIN | " LEFT JOIN tc_plan ON (tc_plan.idTC = tarjetas_credito.idTC… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)