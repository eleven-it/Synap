# Tabla `nc_concepto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_nc | INT | No | ✓ |  |  |
| nombre | VARCHAR | Sí |  |  |  |
| importe | DECIMAL | Sí |  |  |  |
| id_gasto | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| CodIva_gasto | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DOUBLE | Sí |  |  |  |
| IvaxR | DOUBLE | Sí |  |  |  |
| alicuota_iva | DOUBLE | Sí |  |  |  |

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
| NotaCredCon.frm | 3118 | INSERT | conn.Execute "INSERT INTO nc_concepto (nombre, importe, id_g… |
| NotaCredCon.frm | 3192 | SELECT | "FROM nc_concepto WHERE codigoMovimiento = " & contador & " … |
| PNotaDebCopia.frm | 5347 | UPDATE | '                    conn.Execute "UPDATE nc_concepto SET an… |
| ConsultaComprobante.frm | 24590 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 30929 | UPDATE | conn.Execute "UPDATE nc_concepto SET anulado = 'Si' " & _ |
| ConsultaComprobante.frm | 33573 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |
| NotaDeb.frm | 3627 | UPDATE | conn.Execute "UPDATE nc_concepto SET anulado = 'Si' " & _ |
| PNotaDeb.frm | 5573 | UPDATE | '                    conn.Execute "UPDATE nc_concepto SET an… |
| NotaDebCopia.frm | 3537 | UPDATE | conn.Execute "UPDATE nc_concepto SET anulado = 'Si' " & _ |
| Visualiza_NotaCredCon.frm | 3006 | INSERT | conn.Execute "INSERT INTO nc_concepto (nombre, importe, id_g… |
| Principal.frm | 13177 | SELECT | "FROM nc_concepto " & _ |
| adm_felectronicas.frm | 4740 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |
| adm_felectronicas.frm | 12078 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |
| Visualiza.bas | 3589 | SELECT | "FROM nc_concepto " & _ |
| Visualiza.bas | 13805 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |
| Visualiza.bas | 19738 | SELECT | rs_stock.Open "SELECT * FROM nc_concepto WHERE CodigoMovimie… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)