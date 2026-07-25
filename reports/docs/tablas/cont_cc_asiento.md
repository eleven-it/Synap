# Tabla `cont_cc_asiento`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cc_asiento | DOUBLE | No | ✓ |  |  |
| id_cc | DOUBLE | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| importe_cc | DECIMAL | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |

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
| Visualiza_Cont_CargaAsientoM.frm | 1153 | SELECT | rs_ccosto.Open "SELECT * from cont_cc_asiento where codigo_m… |
| Visualiza_Cont_CargaAsientoM.frm | 1170 | SELECT | rs_NewCosto.Open "SELECT * from cont_cc_asiento where codigo… |
| Visualiza_Cont_CargaAsientoM.frm | 1518 | SELECT | rs_newcc.Open "SELECT * from cont_cc_asiento where id_cc_asi… |
| Visualiza_Cont_CargaAsientoM.frm | 1997 | SELECT | rs_ccosto.Open "SELECT * from cont_cc_asiento where codigo_m… |
| Visualiza_Cont_CargaAsientoM.frm | 2014 | SELECT | rs_NewCosto.Open "SELECT * from cont_cc_asiento where codigo… |
| Visualiza_Cont_CargaAsientoM.frm | 3075 | SELECT | rs_visualizarccosto.Open "SELECT * from cont_cc_asiento wher… |
| Cont_CargaAsientoM.frm | 1309 | SELECT | rs_ccosto.Open "SELECT * from cont_cc_asiento where codigo_m… |
| Cont_CargaAsientoM.frm | 1326 | SELECT | rs_NewCosto.Open "SELECT * from cont_cc_asiento where codigo… |
| Cont_CargaAsientoM.frm | 1955 | SELECT | rs_newcc.Open "SELECT * from cont_cc_asiento where id_cc_asi… |
| Cont_CargaAsientoM.frm | 2502 | SELECT | rs_ccosto.Open "SELECT * from cont_cc_asiento where codigo_m… |
| Cont_CargaAsientoM.frm | 2519 | SELECT | rs_NewCosto.Open "SELECT * from cont_cc_asiento where codigo… |
| Cont_CargaAsientoM.frm | 3622 | SELECT | rs_visualizarccosto.Open "SELECT * from cont_cc_asiento wher… |
| Cont_CargaImpCCosto.frm | 751 | UPDATE | conn.Execute "UPDATE cont_cc_asiento " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)