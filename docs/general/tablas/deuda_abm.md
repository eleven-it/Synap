# Tabla `deuda_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_deuda_abm | INT | No | ✓ |  |  |
| nombre_deuda | VARCHAR | Sí |  |  |  |
| alcance | VARCHAR | Sí |  |  |  |
| tipo_datos_adicional | VARCHAR | Sí |  |  |  |
| id_pc | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 10317 | SELECT | data_deuda.RecordSource = "SELECT * FROM deuda_abm WHERE anu… |
| OrdenPago.frm | 10353 | SELECT | data_mp.RecordSource = "SELECT * FROM deuda_abm WHERE anulad… |
| OrdenPago.frm | 11223 | SELECT | rs_consulta_mp.Open "SELECT * FROM deuda_abm " & _ |
| OrdenPago.frm | 13088 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| OrdenPago.frm | 14275 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| ABMDeuda.frm | 446 | SELECT | DataDeuda.RecordSource = "SELECT * FROM deuda_abm" |
| ABMDeuda.frm | 564 | SELECT | consulta = "SELECT * FROM deuda_abm " & _ |
| Visualiza_OrdenPagoC.frm | 7361 | SELECT | data_deuda.RecordSource = "SELECT * FROM deuda_abm WHERE anu… |
| Visualiza_OrdenPagoC.frm | 7397 | SELECT | data_mp.RecordSource = "SELECT * FROM deuda_abm WHERE anulad… |
| Visualiza_OrdenPagoC.frm | 7927 | SELECT | rs_consulta_mp.Open "SELECT * FROM deuda_abm " & _ |
| Visualiza_OrdenPagoC.frm | 9308 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| Visualiza_OrdenPagoC.frm | 10222 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| CargaDeuda.frm | 376 | SELECT | rs_existedeuda.Open "SELECT * FROM deuda_abm WHERE Nombre_de… |
| CargaDeuda.frm | 391 | SELECT | rs_deuda.Open "SELECT * FROM deuda_abm WHERE ID_deuda_abm = … |
| CargaDeuda.frm | 407 | SELECT | ABMDeuda.DataDeuda.RecordSource = "SELECT * FROM deuda_abm O… |
| CargaDeuda.frm | 418 | SELECT | rs_deuda.Open "SELECT * FROM deuda_abm WHERE ID_deuda_abm = … |
| CargaDeuda.frm | 434 | SELECT | ABMDeuda.DataDeuda.RecordSource = "SELECT * FROM deuda_abm O… |
| CargaDeudaBancaria.frm | 1182 | SELECT | DataDeuda.RecordSource = "select * from deuda_abm where alca… |
| CargaDeudaBancaria.frm | 1666 | SELECT | rs_deuda.Open "SELECT * from deuda_abm where id_deuda_abm = … |
| Visualiza_OrdenPago.frm | 7653 | SELECT | data_deuda.RecordSource = "SELECT * FROM deuda_abm WHERE anu… |
| Visualiza_OrdenPago.frm | 7689 | SELECT | data_mp.RecordSource = "SELECT * FROM deuda_abm WHERE anulad… |
| Visualiza_OrdenPago.frm | 8317 | SELECT | rs_consulta_mp.Open "SELECT * FROM deuda_abm " & _ |
| Visualiza_OrdenPago.frm | 9710 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| Visualiza_OrdenPago.frm | 10624 | SELECT | rs_vect.Open "SELECT * from deuda_abm where id_deuda_abm = "… |
| Lista_Deuda.frm | 811 | SELECT | data_deuda_combo.RecordSource = "SELECT * FROM deuda_abm WHE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)