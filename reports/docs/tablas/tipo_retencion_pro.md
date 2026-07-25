# Tabla `tipo_retencion_pro`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodRetencion | INT | No | ✓ |  |  |
| NombreRetencion | VARCHAR | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| ImporteImp | DECIMAL | No |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| codigo_tipo_regimen | VARCHAR | Sí |  |  |  |
| id_jurisdiccion | DOUBLE | Sí |  |  |  |
| tipo_webservice | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 10166 | SELECT | rs_tipo_retencion_pro.Open "SELECT * FROM tipo_retencion_pro… |
| OrdenPago.frm | 16686 | SELECT | rs_retencion_prov.Open "SELECT * FROM tipo_retencion_pro WHE… |
| ABMRetProv.frm | 389 | SELECT | DataRetProv.RecordSource = "SELECT * FROM tipo_retencion_pro… |
| ABMRetProv.frm | 503 | SELECT | consulta = "SELECT * FROM tipo_retencion_pro   " & _ |
| Exportacion.frm | 4320 | JOIN | "LEFT JOIN tipo_retencion_pro ON (tipo_retencion_pro.CodRete… |
| Exportacion.frm | 11827 | JOIN | "LEFT JOIN tipo_retencion_pro ON (tipo_retencion_pro.CodRete… |
| Exportacion.frm | 11949 | JOIN | "LEFT JOIN tipo_retencion_pro ON (tipo_retencion_pro.CodRete… |
| CargaProveedor.frm | 4315 | SELECT | DataTipoRetProv.RecordSource = "select * from tipo_retencion… |
| CargaRetProv.frm | 508 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_pro WHERE CodR… |
| CargaRetProv.frm | 537 | SELECT | rs_retProv.Open "SELECT * FROM tipo_retencion_pro WHERE CodR… |
| Visualiza_OrdenPagoC.frm | 7241 | SELECT | rs_tipo_retencion_pro.Open "SELECT * FROM tipo_retencion_pro… |
| Visualiza_OrdenPagoC.frm | 8226 | SELECT | 'rs_consulta_ret_ganancia.Open "SELECT * FROM tipo_retencion… |
| Visualiza_OrdenPago.frm | 7533 | SELECT | rs_tipo_retencion_pro.Open "SELECT * FROM tipo_retencion_pro… |
| Visualiza_OrdenPago.frm | 8616 | SELECT | 'rs_consulta_ret_ganancia.Open "SELECT * FROM tipo_retencion… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)