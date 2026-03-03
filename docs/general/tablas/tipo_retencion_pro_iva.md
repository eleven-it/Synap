# Tabla `tipo_retencion_pro_iva`

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
| base_impuesto | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 10194 | SELECT | rs_tipo_retencion_pro_iva.Open "SELECT * FROM tipo_retencion… |
| CargaRetProvIVA.frm | 304 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_pro_iva WHERE … |
| CargaRetProvIVA.frm | 326 | SELECT | ABMRetProvIVA.DataRetProv.RecordSource = "SELECT * FROM tipo… |
| CargaRetProvIVA.frm | 335 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_pro_iva WHERE … |
| CargaProveedor.frm | 4325 | SELECT | data_tipo_ret_iva.RecordSource = "select * from tipo_retenci… |
| ABMRetIVA.frm | 370 | SELECT | DataRetProv.RecordSource = "SELECT * FROM tipo_retencion_pro… |
| ABMRetIVA.frm | 485 | SELECT | consulta = "SELECT * FROM tipo_retencion_pro_iva " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)