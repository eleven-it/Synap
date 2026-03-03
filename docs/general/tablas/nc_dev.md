# Tabla `nc_dev`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_nc_dev | BIGINT | No | ✓ |  |  |
| codigo_movimiento_nc | DOUBLE | Sí |  |  |  |
| codigo_movimiento_dev | DOUBLE | Sí |  |  |  |
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
| NotaCred_SinCompO.frm | 4614 | SELECT | rs_e.Open "SELECT id_nc_dev FROM nc_dev " & _ |
| NotaCred_SinCompO.frm | 4623 | SELECT | rs_dev.Open "SELECT * FROM nc_dev " & _ |
| PNotaDebCopia.frm | 4810 | UPDATE | '            conn.Execute "UPDATE nc_dev " & _ |
| PNotaDebCopia.frm | 4815 | JOIN | '                         "INNER JOIN nc_dev ON (nc_dev.codi… |
| ConsultaComprobante.frm | 7245 | UPDATE | conn.Execute "UPDATE nc_dev " & _ |
| ConsultaComprobante.frm | 7250 | JOIN | "INNER JOIN nc_dev ON (nc_dev.codigo_movimiento_dev = comp_p… |
| ConsultaComprobante.frm | 8695 | UPDATE | '            conn.Execute "UPDATE nc_dev " & _ |
| ConsultaComprobante.frm | 8700 | JOIN | '                         "INNER JOIN nc_dev ON (nc_dev.codi… |
| NotaDeb.frm | 2715 | UPDATE | conn.Execute "UPDATE nc_dev " & _ |
| NotaDeb.frm | 2720 | JOIN | "INNER JOIN nc_dev ON (nc_dev.codigo_movimiento_dev = comp_p… |
| PNotaDeb.frm | 5036 | UPDATE | '            conn.Execute "UPDATE nc_dev " & _ |
| PNotaDeb.frm | 5041 | JOIN | '                         "INNER JOIN nc_dev ON (nc_dev.codi… |
| NotaDebCopia.frm | 2652 | UPDATE | conn.Execute "UPDATE nc_dev " & _ |
| NotaDebCopia.frm | 2657 | JOIN | "INNER JOIN nc_dev ON (nc_dev.codigo_movimiento_dev = comp_p… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)