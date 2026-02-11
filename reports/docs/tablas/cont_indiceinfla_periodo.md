# Tabla `cont_indiceinfla_periodo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_indiceinfla_periodo | DOUBLE | No | ✓ |  |  |
| id_indiceinfla | DOUBLE | Sí |  |  |  |
| fecdesde_indiceinfla_periodo | DATE | Sí |  |  |  |
| fechasta_indiceinfla_periodo | DATE | Sí |  |  |  |
| importe_indiceinfla_periodo | DECIMAL | Sí |  |  |  |
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
| Cont_abmIndiceInfla.frm | 470 | SELECT | DataIndPer.RecordSource = "SELECT * FROM cont_indiceinfla_pe… |
| Cont_ProcesosC.frm | 4109 | SELECT | rs.Open "SELECT * FROM cont_indiceinfla_periodo where fechas… |
| Cont_ProcesosC.frm | 4161 | SELECT | rs.Open "SELECT * FROM cont_indiceinfla_periodo " & _ |
| Cont_CargaIndInfPer.frm | 399 | SELECT | rs_periodo.Open "select * from cont_indiceinfla_periodo wher… |
| Cont_CargaIndInfPer.frm | 413 | SELECT | rs_periodo.Open "select * from cont_indiceinfla_periodo wher… |
| Cont_CargaIndInfPer.frm | 427 | SELECT | rs_IndPer.Open "SELECT * FROM cont_indiceinfla_periodo WHERE… |
| Cont_CargaIndInfPer.frm | 452 | SELECT | Cont_abmIndiceInfla.DataIndPer.RecordSource = "SELECT * FROM… |
| Cont_CargaIndInfPer.frm | 468 | SELECT | rs_IndPer.Open "SELECT * FROM cont_indiceinfla_periodo WHERE… |
| Cont_CargaIndInfPer.frm | 475 | SELECT | rs_periodo.Open "select * from cont_indiceinfla_periodo wher… |
| Cont_CargaIndInfPer.frm | 493 | SELECT | rs_periodo.Open "select * from cont_indiceinfla_periodo wher… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)