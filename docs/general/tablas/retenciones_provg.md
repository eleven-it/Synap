# Tabla `retenciones_provg`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodRetencion | INT | No |  |  |  |
| NroCertificado | VARCHAR | No |  |  |  |
| nro_certificado_busq | DECIMAL | Sí |  |  |  |
| NroOP | VARCHAR | No |  |  |  |
| CodProveedor | INT | No |  |  |  |
| Fecha | DATE | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_retenciones_provg | DOUBLE | No | ✓ |  |  |
| retXdiferencia | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 7751 | SELECT | rs_retencion_ganancia.Open "select * from retenciones_provg … |
| OrdenPago.frm | 11611 | SELECT | "From retenciones_provg " & _ |
| OrdenPago.frm | 11857 | SELECT | "From retenciones_provg " & _ |
| OrdenPago.frm | 16021 | SELECT | rs_retgan.Open "SELECT * FROM retenciones_provg WHERE Codigo… |
| Exportacion.frm | 3301 | SELECT | rs_exp.Open "SELECT * FROM retenciones_provg " & _ |
| Exportacion.frm | 3495 | SELECT | rs_exp.Open "SELECT * FROM retenciones_provg " & _ |
| ConsultaComprobante.frm | 2907 | SELECT | DataConsulta.RecordSource = "select retenciones_provg.*, pro… |
| ConsultaComprobante.frm | 2913 | SELECT | DataConsulta.RecordSource = "select retenciones_provg.*, pro… |
| ConsultaComprobante.frm | 12832 | SELECT | rs_retenciones_provg.Open "SELECT * FROM retenciones_provg W… |
| trz_trazabilidadComp.frm | 4952 | SELECT | rs_retencion_gan.Open "SELECT retenciones_provg.*,tipo_reten… |
| CuentaProveedor.frm | 1481 | SELECT | '        rs_retencion_gan.Open "SELECT retenciones_provg.*,t… |
| Visualiza.bas | 7616 | SELECT | rs_retencion_gan.Open "SELECT retenciones_provg.*,tipo_reten… |
| Visualiza.bas | 21207 | SELECT | rs_comprobante.Open "SELECT retenciones_provg.* FROM retenci… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)