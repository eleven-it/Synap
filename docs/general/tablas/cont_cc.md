# Tabla `cont_cc`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cc | DOUBLE | No | ✓ |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| descRenglon_cc | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| cont_cc | cont_pc | Cont_CentroCosto.frm | 679 | DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont_pc.descrip_pc, S… |
| cont_cc | cont_pc | Cont_ListaCtaCont.frm | 1253 | 'rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_c… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 2209 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 3210 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 3313 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 2718 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 3756 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 3859 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaCentroCosto.frm | 640 | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont… |
| cont_cc | cont_pc | Cont_CargaCentroCosto.frm | 714 | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cont_CentroCosto.frm | 569 | SELECT | DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, c… |
| Cont_CentroCosto.frm | 588 | SELECT | DataCC.RecordSource = "SELECT * from cont_cc where id_pc = "… |
| Cont_CentroCosto.frm | 599 | SELECT | DataCC.RecordSource = "SELECT * from cont_cc " & _ |
| Cont_CentroCosto.frm | 679 | SELECT | DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, c… |
| Cont_CentroCosto.frm | 811 | SELECT | DataCC.RecordSource = "SELECT * from cont_cc where id_pc = "… |
| Cont_ListaCtaCont.frm | 1253 | SELECT | 'rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (co… |
| Cont_ListaCtaCont.frm | 1813 | SELECT | '    rs_cc.Open "SELECT * FROM cont_cc where id_pc = " & Dat… |
| Cont_ListaCtaCont.frm | 1831 | SELECT | '    rs_cc.Open "SELECT * FROM cont_cc where id_pc = " & Dat… |
| Visualiza_Cont_CargaAsientoM.frm | 2209 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Visualiza_Cont_CargaAsientoM.frm | 3141 | SELECT | rs_Nomcosto.Open "SELECT * from cont_cc where id_cc = " & rs… |
| Visualiza_Cont_CargaAsientoM.frm | 3210 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Visualiza_Cont_CargaAsientoM.frm | 3313 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Cont_CargaAsientoM.frm | 2718 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Cont_CargaAsientoM.frm | 3687 | SELECT | rs_Nomcosto.Open "SELECT * from cont_cc where id_cc = " & rs… |
| Cont_CargaAsientoM.frm | 3756 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Cont_CargaAsientoM.frm | 3859 | SELECT | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (con… |
| Cont_CargaCentroCosto.frm | 584 | SELECT | rs_CantCC.Open "SELECT * FROM cont_cc WHERE id_pc = " & idpc… |
| Cont_CargaCentroCosto.frm | 597 | SELECT | rs_newcc.Open "SELECT * from cont_cc where id_cc = 0", conn,… |
| Cont_CargaCentroCosto.frm | 640 | SELECT | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT… |
| Cont_CargaCentroCosto.frm | 651 | SELECT | conn.Execute "DELETE FROM cont_cc WHERE id_pc = " & idpc & "… |
| Cont_CargaCentroCosto.frm | 651 | DELETE | conn.Execute "DELETE FROM cont_cc WHERE id_pc = " & idpc & "… |
| Cont_CargaCentroCosto.frm | 654 | SELECT | rs_CantCC.Open "SELECT * FROM cont_cc WHERE id_pc = " & idpc… |
| Cont_CargaCentroCosto.frm | 671 | SELECT | rs_newcc.Open "SELECT * from cont_cc where id_cc = 0", conn,… |
| Cont_CargaCentroCosto.frm | 714 | SELECT | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT… |
| Cont_CargaCentroCosto.frm | 1010 | SELECT | rs_VisualizarCC.Open "SELECT * from cont_cc where id_pc = " … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)