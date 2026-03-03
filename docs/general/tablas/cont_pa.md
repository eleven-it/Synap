# Tabla `cont_pa`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pa | DOUBLE | No | ✓ |  |  |
| desc_pa | VARCHAR | Sí |  |  |  |
| id_concepto_asiento | DOUBLE | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| descripcion_pc | VARCHAR | Sí |  |  |  |
| debe_asiento | VARCHAR | Sí |  |  |  |
| haber_asiento | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| nro_pa | DOUBLE | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| modifica_pa | VARCHAR | Sí |  |  |  |

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
| Cont_ListaPA.frm | 442 | SELECT | DataListaPA.RecordSource = "select desc_pa, nro_pa from cont… |
| Cont_ListaPA.frm | 487 | SELECT | DataListaPA.RecordSource = "select desc_pa, nro_pa from cont… |
| Cont_ListaPA.frm | 640 | SELECT | rs_RecuperaPA.Open "SELECT * from cont_pa where nro_pa = " &… |
| Cont_ListaPA.frm | 751 | SELECT | rs_RecuperaPA.Open "SELECT * from cont_pa where nro_pa = " &… |
| Cont_PA.frm | 657 | SELECT | rs_NomPa.Open "SELECT * FROM cont_pa WHERE desc_pa = '" & tx… |
| Cont_PA.frm | 699 | SELECT | rs_newasiento.Open "SELECT * from cont_pa where id_pa = 0", … |
| Cont_PA.frm | 712 | SELECT | rs_NroPA.Open "SELECT max(nro_pa) as nropa from cont_pa", co… |
| Cont_PA.frm | 800 | SELECT | Cont_ListaPA.DataListaPA.RecordSource = "select desc_pa, nro… |
| Cont_PA.frm | 866 | SELECT | conn.Execute "DELETE FROM cont_pa WHERE nro_pa = " & NroPa &… |
| Cont_PA.frm | 866 | DELETE | conn.Execute "DELETE FROM cont_pa WHERE nro_pa = " & NroPa &… |
| Cont_PA.frm | 869 | SELECT | rs_NomPa.Open "SELECT * FROM cont_pa WHERE desc_pa = '" & tx… |
| Cont_PA.frm | 882 | SELECT | rs_newasiento.Open "SELECT * from cont_pa where id_pa = 0", … |
| Cont_PA.frm | 952 | SELECT | Cont_ListaPA.DataListaPA.RecordSource = "SELECT desc_pa, nro… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)