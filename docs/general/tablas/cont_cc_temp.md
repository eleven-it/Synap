# Tabla `cont_cc_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cc_temp | DOUBLE | No | ✓ |  |  |
| descRenglon_cc_temp | VARCHAR | Sí |  |  |  |
| importe_cc_temp | DECIMAL | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| anulado_temp | VARCHAR | Sí |  |  |  |
| id_pc_temp | DOUBLE | Sí |  |  |  |
| id_cc | DOUBLE | Sí |  |  |  |

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
| Cont_ListaCtaCont.frm | 1262 | SELECT | '    rs_asientotemp.Open "SELECT * from cont_cc_temp where i… |
| Cont_ListaCtaCont.frm | 1295 | SELECT | 'Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FRO… |
| Cont_ListaCtaCont.frm | 1321 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_ListaCtaCont.frm | 1321 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Visualiza_Cont_CargaAsientoM.frm | 1073 | SELECT | rs_sumcost.Open "SELECT sum(importe_cc_temp) as SumImporte f… |
| Visualiza_Cont_CargaAsientoM.frm | 1145 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Visualiza_Cont_CargaAsientoM.frm | 1522 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Visualiza_Cont_CargaAsientoM.frm | 1989 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Visualiza_Cont_CargaAsientoM.frm | 2166 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Visualiza_Cont_CargaAsientoM.frm | 2174 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 2224 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Visualiza_Cont_CargaAsientoM.frm | 2263 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 2612 | SELECT | rs_AsigCcosto.Open "SELECT * from cont_cc_temp where anulado… |
| Visualiza_Cont_CargaAsientoM.frm | 2683 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Visualiza_Cont_CargaAsientoM.frm | 2683 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Visualiza_Cont_CargaAsientoM.frm | 3083 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Visualiza_Cont_CargaAsientoM.frm | 3091 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 3116 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "select * from… |
| Visualiza_Cont_CargaAsientoM.frm | 3183 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Visualiza_Cont_CargaAsientoM.frm | 3191 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 3222 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Visualiza_Cont_CargaAsientoM.frm | 3261 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 3286 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Visualiza_Cont_CargaAsientoM.frm | 3294 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 3325 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Visualiza_Cont_CargaAsientoM.frm | 3361 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Visualiza_Cont_CargaAsientoM.frm | 3373 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "select * from… |
| Visualiza_Cont_CargaAsientoM.frm | 3381 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Visualiza_Cont_CargaAsientoM.frm | 3381 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaAsientoM.frm | 1226 | SELECT | rs_sumcost.Open "SELECT sum(importe_cc_temp) as SumImporte f… |
| Cont_CargaAsientoM.frm | 1301 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Cont_CargaAsientoM.frm | 1959 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Cont_CargaAsientoM.frm | 2494 | SELECT | rs_cctemp.Open "SELECT * from cont_cc_temp where id_usuario … |
| Cont_CargaAsientoM.frm | 2675 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Cont_CargaAsientoM.frm | 2683 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 2733 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Cont_CargaAsientoM.frm | 2772 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3127 | SELECT | rs_AsigCcosto.Open "SELECT * from cont_cc_temp where anulado… |
| Cont_CargaAsientoM.frm | 3197 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaAsientoM.frm | 3197 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaAsientoM.frm | 3629 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Cont_CargaAsientoM.frm | 3637 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3662 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "select * from… |
| Cont_CargaAsientoM.frm | 3729 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Cont_CargaAsientoM.frm | 3737 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3768 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Cont_CargaAsientoM.frm | 3807 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3832 | SELECT | rs_temp.Open "SELECT * FROM cont_cc_temp Where anulado_temp … |
| Cont_CargaAsientoM.frm | 3840 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3871 | SELECT | rs_asientotemp.Open "SELECT * from cont_cc_temp where id_cc_… |
| Cont_CargaAsientoM.frm | 3907 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "SELECT * FROM… |
| Cont_CargaAsientoM.frm | 3919 | SELECT | Cont_CargaImpCCosto.DataCostos.RecordSource = "select * from… |
| Cont_CargaAsientoM.frm | 3930 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaAsientoM.frm | 3930 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaImpCCosto.frm | 752 | JOIN | "INNER JOIN cont_cc_temp ON (cont_cc_temp.id_cc = cont_cc_as… |
| Cont_CargaCentroCosto.frm | 755 | SELECT | '    DataCC.RecordSource = "select * from cont_cc_temp where… |
| Cont_CargaCentroCosto.frm | 892 | SELECT | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaCentroCosto.frm | 892 | DELETE | conn.Execute "DELETE FROM cont_cc_temp WHERE id_usuario = " … |
| Cont_CargaCentroCosto.frm | 947 | SELECT | DataCC.RecordSource = "select * from cont_cc_temp  where " &… |
| Cont_CargaCentroCosto.frm | 963 | SELECT | DataCC.RecordSource = "select * from cont_cc_temp where " & … |
| Cont_CargaCentroCosto.frm | 1032 | SELECT | DataCC.RecordSource = "select * from cont_cc_temp where id_c… |
| Cont_CargaCentroCosto.frm | 1060 | SELECT | DataCC.RecordSource = "select * from cont_cc_temp where id_u… |
| Cont_CargaCosto.frm | 382 | SELECT | rs_Nomcc.Open "SELECT * FROM cont_cc_temp WHERE descrenglon_… |
| Cont_CargaCosto.frm | 395 | SELECT | rs_costo.Open "select * from cont_cc_temp where id_cc_temp =… |
| Cont_CargaCosto.frm | 418 | SELECT | Cont_CargaCentroCosto.DataCC.RecordSource = "SELECT * FROM c… |
| Cont_CargaCosto.frm | 430 | SELECT | rs_costo.Open "SELECT * FROM cont_cc_temp WHERE id_cc_temp =… |
| Cont_CargaCosto.frm | 437 | SELECT | rs_Nomcc.Open "SELECT * FROM cont_cc_temp WHERE descrenglon_… |
| Principal.frm | 6073 | SELECT | conn.Execute "delete from cont_cc_temp where id_usuario = " … |
| Principal.frm | 6073 | DELETE | conn.Execute "delete from cont_cc_temp where id_usuario = " … |
| Principal.frm | 6139 | SELECT | conn.Execute "delete from cont_cc_temp where id_usuario = " … |
| Principal.frm | 6139 | DELETE | conn.Execute "delete from cont_cc_temp where id_usuario = " … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)