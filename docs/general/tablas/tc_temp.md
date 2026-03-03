# Tabla `tc_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tc_temp | DOUBLE | No | ✓ |  |  |
| nombre_tc_temp | VARCHAR | Sí |  |  |  |
| nombre_plan_tc_temp | VARCHAR | No |  |  |  |
| id_tc | DECIMAL | No |  |  |  |
| id_tc_plan | DECIMAL | Sí |  |  |  |
| cuotas_tc_temp | DECIMAL | Sí |  |  |  |
| interes_tc_temp | DECIMAL | Sí |  |  |  |
| descuento_tc_temp | DECIMAL | Sí |  |  |  |
| nro_tarjeta_tc_temp | VARCHAR | Sí |  |  |  |
| nro_cupon_tc_temp | DECIMAL | Sí |  |  |  |
| importe_tc_temp | DECIMAL | Sí |  |  |  |
| importe_cuota | DECIMAL | Sí |  |  |  |
| importe_con_interes | DECIMAL | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nro_lote_tc_temp | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 10746 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_ReciboCobro.frm | 10746 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_ReciboCobro.frm | 12652 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| Visualiza_ReciboCobro.frm | 12676 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| Visualiza_ReciboCobro.frm | 13235 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobro.frm | 13255 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobro.frm | 13275 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_ReciboCobro.frm | 13309 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_ReciboCobro.frm | 13309 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_ReciboCobro.frm | 13312 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobro.frm | 13324 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_TPV.frm | 5148 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_TPV.frm | 5170 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_TPV.frm | 5190 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_TPV.frm | 5394 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_TPV.frm | 5394 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_TPV.frm | 5397 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_TPV.frm | 5409 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_TPV.frm | 6156 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_TPV.frm | 6156 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_TPV.frm | 7357 | SELECT | "FROM tc_temp WHERE " & _ |
| Visualiza_TPV.frm | 7404 | SELECT | "FROM tc_temp WHERE " & _ |
| TPV.frm | 11074 | SELECT | rs_cup.Open "SELECT * FROM tc_temp WHERE id_usuario = " & Pr… |
| TPV.frm | 11142 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV.frm | 11173 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV.frm | 11194 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| TPV.frm | 11649 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| TPV.frm | 11649 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| TPV.frm | 11652 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV.frm | 11664 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| TPV.frm | 12938 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| TPV.frm | 12938 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| TPV.frm | 16632 | SELECT | "FROM tc_temp WHERE " & _ |
| TPV.frm | 16682 | SELECT | "FROM tc_temp WHERE " & _ |
| TPV.frm | 37362 | SELECT | rs_tarjeta_temp.Open "SELECT * FROM tc_temp where id_usuario… |
| CuentaCliente.frm | 2439 | SELECT | '                Visualiza_ReciboCobro.data_tarjeta_temp.Rec… |
| CuentaCliente.frm | 2465 | SELECT | '                Visualiza_ReciboCobro.data_tarjeta_temp.Rec… |
| CuentaCliente.frm | 3093 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| CuentaCliente.frm | 3118 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| trz_trazabilidad.frm | 6932 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| trz_trazabilidad.frm | 6957 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| trz_trazabilidad.frm | 7249 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| trz_trazabilidad.frm | 7249 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| trz_trazabilidad.frm | 7551 | SELECT | Visualiza_ReciboCobro.data_tarjeta_temp.RecordSource = "SELE… |
| trz_trazabilidad.frm | 7577 | SELECT | Visualiza_ReciboCobro.data_tarjeta_temp.RecordSource = "SELE… |
| ReciboCobro.frm | 11741 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| ReciboCobro.frm | 11741 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| ReciboCobro.frm | 13410 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| ReciboCobro.frm | 13434 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| ReciboCobro.frm | 13971 | SELECT | rs_cup.Open "SELECT * FROM tc_temp WHERE id_usuario = " & Pr… |
| ReciboCobro.frm | 14018 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| ReciboCobro.frm | 14042 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| ReciboCobro.frm | 14062 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| ReciboCobro.frm | 14099 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| ReciboCobro.frm | 14099 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| ReciboCobro.frm | 14102 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| ReciboCobro.frm | 14114 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_ReciboCobroC.frm | 10403 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_ReciboCobroC.frm | 10403 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| Visualiza_ReciboCobroC.frm | 12291 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| Visualiza_ReciboCobroC.frm | 12315 | SELECT | Visualiza_TPV.data_tarjeta_temp.RecordSource = "SELECT * FRO… |
| Visualiza_ReciboCobroC.frm | 12852 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobroC.frm | 12872 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobroC.frm | 12892 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| Visualiza_ReciboCobroC.frm | 12926 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_ReciboCobroC.frm | 12926 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| Visualiza_ReciboCobroC.frm | 12929 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| Visualiza_ReciboCobroC.frm | 12941 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| TPV_2.frm | 10847 | SELECT | rs_cup.Open "SELECT * FROM tc_temp WHERE id_usuario = " & Pr… |
| TPV_2.frm | 10915 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV_2.frm | 10940 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV_2.frm | 10961 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| TPV_2.frm | 11243 | SELECT | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| TPV_2.frm | 11243 | DELETE | conn.Execute "DELETE FROM tc_temp WHERE id_tc_temp = " & id_… |
| TPV_2.frm | 11246 | SELECT | data_tarjeta_temp.RecordSource = "SELECT * FROM tc_temp WHER… |
| TPV_2.frm | 11258 | SELECT | rs_total_tarjeta.Open "SELECT SUM(importe_tc_temp) as total_… |
| TPV_2.frm | 12279 | SELECT | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| TPV_2.frm | 12279 | DELETE | conn.Execute "delete from tc_temp where id_usuario = " & Pri… |
| TPV_2.frm | 14923 | SELECT | "FROM tc_temp WHERE " & _ |
| TPV_2.frm | 14973 | SELECT | "FROM tc_temp WHERE " & _ |
| … | … | … | *(11 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)