# Tabla `chequera`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| NroChequera | VARCHAR | Sí |  |  |  |
| CodCuenta | INT | Sí |  |  |  |
| NroInicial | DECIMAL | Sí |  |  |  |
| NroFinal | DECIMAL | Sí |  |  |  |
| NroActual | DECIMAL | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| TipoChequera | VARCHAR | Sí |  |  |  |
| CodChequera | INT | No | ✓ |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 7667 | SELECT | rs_chequera.Open "SELECT * FROM chequera WHERE CodChequera =… |
| OrdenPago.frm | 10831 | SELECT | rs_ultimocheque.Open "SELECT * FROM chequera WHERE CodCheque… |
| OrdenPago.frm | 10850 | SELECT | rs_ultimocheque.Open "SELECT * FROM chequera WHERE CodCheque… |
| ABMChequeras.frm | 819 | SELECT | DataChequera.RecordSource = "select * from Chequera where Co… |
| CargaChequera.frm | 358 | SELECT | rs_chequeraBusq.Open "SELECT * FROM chequera WHERE NroCheque… |
| CargaChequera.frm | 376 | SELECT | rs_chequera.Open "SELECT * FROM chequera WHERE CodCuenta=0",… |
| CargaChequera.frm | 395 | SELECT | ABMChequera.DataChequera.RecordSource = "SELECT * FROM chequ… |
| CargaChequera.frm | 405 | SELECT | rs_chequeraBusq.Open "SELECT * FROM chequera WHERE NroCheque… |
| CargaChequera.frm | 422 | SELECT | rs_chequera.Open "SELECT * FROM chequera WHERE CodChequera="… |
| CargaChequera.frm | 441 | SELECT | ABMChequera.DataChequera.RecordSource = "SELECT * FROM chequ… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)