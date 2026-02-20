# Tabla `impuesto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_impuesto | INT | No | ✓ |  |  |
| nombre_impuesto | VARCHAR | Sí |  |  |  |
| comp_iva | VARCHAR | Sí |  |  |  |
| id_pc | INT | Sí |  |  |  |
| alcance_impuesto | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc_deuda | INT | Sí |  |  |  |

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
| Info_Impositivo.frm | 2411 | SELECT | data_impuesto.RecordSource = "SELECT * FROM impuesto ORDER B… |
| OrdenPago.frm | 10308 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| OrdenPago.frm | 13079 | SELECT | rs_vect.Open "SELECT * from impuesto where id_impuesto = " &… |
| Imp_Carga.frm | 947 | SELECT | rs_pagado.Open "SELECT * from impuesto where id_impuesto= " … |
| Imp_Carga.frm | 972 | SELECT | rs_Apagar.Open "SELECT * from impuesto where id_impuesto= " … |
| CargaRetCli.frm | 906 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| Exportacion.frm | 967 | JOIN | '        "LEFT JOIN impuesto ON (impuesto.id_impuesto = tipo… |
| CargaGastoBancario.frm | 1098 | SELECT | '    rs_consulta_iva.Open "select * from impuesto where id_i… |
| CargaGastoBancario.frm | 1383 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| CargaGastoBancario.frm | 1468 | SELECT | rs_ImpIva.Open "SELECT comp_iva from impuesto where id_impue… |
| CargaGastoBancario.frm | 1685 | SELECT | rs_imp.Open "SELECT * from impuesto where id_impuesto = " & … |
| CargaImpuesto.frm | 450 | SELECT | rs_imp.Open "SELECT * FROM impuesto WHERE ID_impuesto = 0", … |
| CargaImpuesto.frm | 467 | SELECT | ABMImpuestos.DataImp.RecordSource = "SELECT * FROM impuesto … |
| CargaImpuesto.frm | 478 | SELECT | rs_imp.Open "SELECT * FROM impuesto WHERE ID_impuesto = " & … |
| CargaImpuesto.frm | 495 | SELECT | ABMImpuestos.DataImp.RecordSource = "SELECT * FROM impuesto … |
| ABMImpuestos.frm | 490 | SELECT | DataImp.RecordSource = "SELECT * FROM impuesto ORDER BY id_i… |
| ABMImpuestos.frm | 610 | SELECT | consulta = "SELECT * FROM impuesto" & _ |
| Visualiza_OrdenPagoC.frm | 7352 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| Visualiza_OrdenPagoC.frm | 9300 | SELECT | rs_vect.Open "SELECT * from impuesto where id_impuesto = " &… |
| imp_Gestion.frm | 964 | SELECT | DataImpuesto.RecordSource = "SELECT * from impuesto WHERE " … |
| imp_Gestion.frm | 972 | SELECT | DataImpuesto.RecordSource = "SELECT * from impuesto WHERE " … |
| CargaDeudaBancaria.frm | 1202 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| CargaDeudaBancaria.frm | 1272 | SELECT | rs_ImpIva.Open "SELECT comp_iva from impuesto where id_impue… |
| CargaDeudaBancaria.frm | 1585 | SELECT | rs_imp.Open "SELECT * from impuesto where id_impuesto = " & … |
| Visualiza_OrdenPago.frm | 7644 | SELECT | DataImpuestos.RecordSource = "SELECT * FROM impuesto WHERE i… |
| Visualiza_OrdenPago.frm | 9702 | SELECT | rs_vect.Open "SELECT * from impuesto where id_impuesto = " &… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)