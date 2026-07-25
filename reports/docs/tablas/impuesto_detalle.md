# Tabla `impuesto_detalle`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_impuesto_detalle | DOUBLE | No | ✓ |  |  |
| id_impuesto | DOUBLE | Sí |  |  |  |
| id_periodo | DOUBLE | Sí |  |  |  |
| id_year | DOUBLE | Sí |  |  |  |
| fecdesde_impdetalle | DATE | Sí |  |  |  |
| fechasta_impdetalle | DATE | Sí |  |  |  |
| importe_impdetalle | DOUBLE | Sí |  |  |  |
| estado_impdetalle | VARCHAR | Sí |  |  |  |
| vencimiento_impdetalle | DATE | Sí |  |  |  |
| codigo_mov_op | DOUBLE | Sí |  |  |  |
| NomPer_impdetalle | VARCHAR | Sí |  |  |  |
| detalle_impdetalle | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipoPres_impdetalle | VARCHAR | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| Tipo_saldo | VARCHAR | Sí |  |  |  |
| detalle2_impdetalle | VARCHAR | Sí |  |  |  |

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
| Info_Estadistica.frm | 4155 | SELECT | "Set reporte_flujofondos_temp.imp_impuesto = (SELECT sum(imp… |
| OrdenPago.frm | 7912 | SELECT | rs_impuesto.Open "SELECT * FROM impuesto_detalle WHERE id_im… |
| Imp_Carga.frm | 490 | SELECT | rs_impdetalle.Open "SELECT * FROM impuesto_detalle WHERE id_… |
| Imp_Carga.frm | 542 | SELECT | rs_impdetalle.Open "SELECT * FROM impuesto_detalle WHERE  id… |
| Imp_Carga.frm | 593 | SELECT | imp_Gestion.DataDetalle.RecordSource = "SELECT * FROM impues… |
| Imp_Carga.frm | 610 | SELECT | rs_ModImpdetalle.Open "SELECT * FROM impuesto_detalle WHERE … |
| Imp_Carga.frm | 620 | SELECT | rs_HayAnul.Open "SELECT * from impuesto_detalle where id_imp… |
| ConsultaComprobante.frm | 13114 | SELECT | rs_impuesto_act.Open "SELECT * FROM impuesto_detalle WHERE i… |
| imp_Gestion.frm | 1044 | SELECT | DataDetalle.RecordSource = "SELECT * FROM impuesto_detalle W… |
| imp_Gestion.frm | 1053 | SELECT | DataDetalle.RecordSource = "SELECT * FROM impuesto_detalle W… |
| imp_Gestion.frm | 1077 | SELECT | '        rs_Tot.Open " SELECT SUM(impuesto_detalle.importe_i… |
| imp_Gestion.frm | 1286 | SELECT | DataDetalle.RecordSource = "SELECT * from impuesto_detalle w… |
| imp_Gestion.frm | 1293 | SELECT | DataDetalle.RecordSource = "SELECT * from impuesto_detalle w… |
| imp_Gestion.frm | 1304 | SELECT | DataDetalle.RecordSource = "SELECT * from impuesto_detalle "… |
| imp_Gestion.frm | 1352 | SELECT | rs_Tot.Open " SELECT SUM(impuesto_detalle.importe_impdetalle… |
| imp_Gestion.frm | 1373 | SELECT | rs_TotF.Open " SELECT SUM(impuesto_detalle.importe_impdetall… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)