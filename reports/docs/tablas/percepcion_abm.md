# Tabla `percepcion_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percepcion_abm | DOUBLE | No | ✓ |  |  |
| nombre_percepcion_abm | VARCHAR | Sí |  |  |  |
| alicuota_percepcion_abm | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 10342 | SELECT | data_percepcion.RecordSource = "SELECT * FROM percepcion_abm… |
| OrdenPago.frm | 13095 | SELECT | '                        rs_vect.Open "SELECT * from percepc… |
| OrdenPago.frm | 13321 | SELECT | rs_vectP.Open "SELECT id_pc from percepcion_abm where id_per… |
| ABMPercepciones.frm | 370 | SELECT | Data_percepciones.RecordSource = "select * from percepcion_a… |
| ABMPercepciones.frm | 596 | SELECT | Data_percepciones.RecordSource = "SELECT * FROM percepcion_a… |
| CargaGastoBancario.frm | 1412 | SELECT | data_percepcion.RecordSource = "SELECT * FROM percepcion_abm… |
| CargaGastoBancario.frm | 1813 | SELECT | rs_percep.Open "SELECT * from percepcion_abm where id_percep… |
| Visualiza_OrdenPagoC.frm | 7386 | SELECT | data_percepcion.RecordSource = "SELECT * FROM percepcion_abm… |
| Visualiza_OrdenPagoC.frm | 9315 | SELECT | '                        rs_vect.Open "SELECT * from percepc… |
| Visualiza_OrdenPagoC.frm | 9533 | SELECT | rs_vectP.Open "SELECT id_pc from percepcion_abm where id_per… |
| CargaPercepciones.frm | 386 | SELECT | rs_percep.Open "SELECT nombre_percepcion_abm FROM percepcion… |
| CargaPercepciones.frm | 402 | SELECT | rs_percep.Open "SELECT * FROM percepcion_abm where id_percep… |
| CargaPercepciones.frm | 419 | SELECT | ABMPercepciones.Data_percepciones.RecordSource = "SELECT * F… |
| CargaPercepciones.frm | 431 | SELECT | rs_percep.Open "SELECT * FROM percepcion_abm WHERE id_percep… |
| CargaPercepciones.frm | 446 | SELECT | ABMPercepciones.Data_percepciones.RecordSource = "SELECT * F… |
| Visualiza_OrdenPago.frm | 7678 | SELECT | data_percepcion.RecordSource = "SELECT * FROM percepcion_abm… |
| Visualiza_OrdenPago.frm | 9717 | SELECT | '                        rs_vect.Open "SELECT * from percepc… |
| Visualiza_OrdenPago.frm | 9935 | SELECT | rs_vectP.Open "SELECT id_pc from percepcion_abm where id_per… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)