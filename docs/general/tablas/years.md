# Tabla `years`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_year | INT | No | ✓ |  |  |
| year | INT | Sí |  |  |  |
| anulado_year | VARCHAR | Sí |  |  |  |

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
| PNotaCred.frm | 2693 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| PRemito.frm | 3415 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| ABMPeriodos.frm | 534 | SELECT | DataYear.RecordSource = "SELECT * FROM years ORDER BY year D… |
| ABMPeriodos.frm | 697 | UPDATE | conn.Execute "UPDATE years SET anulado_year='Si' WHERE id_ye… |
| PNotaDebCopia.frm | 1718 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| PFactura.frm | 4012 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| PNotaCredDesc.frm | 1766 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| CargaYear.frm | 313 | SELECT | rs_year.Open "SELECT * FROM years WHERE year=" & Year.Text, … |
| CargaYear.frm | 383 | SELECT | ABMPeriodos.DataYear.RecordSource = "SELECT * FROM years ORD… |
| PNotaCred_Importe.frm | 1927 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| PNotaDeb.frm | 1811 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| PNotaCredCopia.frm | 2595 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |
| En_Carga_Pesaje.frm | 5530 | SELECT | rs_a�o.Open "SELECT * FROM Years WHERE year = " & A�oComp & … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)