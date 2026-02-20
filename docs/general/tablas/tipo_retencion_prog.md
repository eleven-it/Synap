# Tabla `tipo_retencion_prog`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodRetencion | INT | No | ✓ |  |  |
| NombreRetencion | TINYTEXT | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| ImporteImp | DECIMAL | No |  |  |  |
| CodigoRegimen | VARCHAR | No |  |  |  |
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
| OrdenPago.frm | 10184 | SELECT | rs_tipo_retencion_prog.Open "SELECT * FROM tipo_retencion_pr… |
| OrdenPago.frm | 11576 | SELECT | rs_tiporetencionprog.Open "SELECT porcentaje, importeimp fro… |
| OrdenPago.frm | 11818 | SELECT | rs_tiporetencionprog.Open "SELECT porcentaje, importeimp fro… |
| OrdenPago.frm | 11959 | SELECT | '        rs_tiporetencionprog.Open "SELECT porcentaje, impor… |
| CargaRetProvG.frm | 284 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_prog WHERE Cod… |
| CargaRetProvG.frm | 305 | SELECT | ABMRetProvG.DataRetProv.RecordSource = "SELECT * FROM tipo_r… |
| CargaRetProvG.frm | 314 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_prog WHERE Cod… |
| Exportacion.frm | 3304 | JOIN | "RIGHT JOIN tipo_retencion_prog ON (tipo_retencion_prog.codR… |
| Exportacion.frm | 3498 | JOIN | "RIGHT JOIN tipo_retencion_prog ON (tipo_retencion_prog.codR… |
| CargaProveedor.frm | 4320 | SELECT | DataTipoRetProvG.RecordSource = "select * from tipo_retencio… |
| Visualiza_OrdenPagoC.frm | 7251 | SELECT | rs_tipo_retencion_prog.Open "SELECT * FROM tipo_retencion_pr… |
| Visualiza_OrdenPago.frm | 7543 | SELECT | rs_tipo_retencion_prog.Open "SELECT * FROM tipo_retencion_pr… |
| ABMRetProvG.frm | 372 | SELECT | DataRetProv.RecordSource = "SELECT * FROM tipo_retencion_pro… |
| ABMRetProvG.frm | 484 | SELECT | consulta = "SELECT * FROM tipo_retencion_prog  " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)