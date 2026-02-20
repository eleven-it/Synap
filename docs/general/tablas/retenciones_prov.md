# Tabla `retenciones_prov`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_retenciones_prov | DOUBLE | No | ✓ |  |  |
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
| ImporteCompraL | VARCHAR | Sí |  |  |  |
| retXsuperar | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 7696 | SELECT | rs_retencion_ib.Open "select * from retenciones_prov where i… |
| OrdenPago.frm | 11992 | SELECT | "From retenciones_prov " & _ |
| OrdenPago.frm | 15850 | SELECT | rs_retib.Open "SELECT * FROM retenciones_prov WHERE Codigo_M… |
| Exportacion.frm | 4317 | SELECT | rs_exp.Open "SELECT * FROM retenciones_prov " & _ |
| Exportacion.frm | 4490 | SELECT | "FROM retenciones_prov rp " & _ |
| Exportacion.frm | 11824 | SELECT | rs_exp.Open "SELECT retenciones_prov.*,retenciones_prov.impo… |
| Exportacion.frm | 11946 | SELECT | rs_exp.Open "SELECT * FROM retenciones_prov " & _ |
| ConsultaComprobante.frm | 2888 | SELECT | DataConsulta.RecordSource = "select retenciones_prov.*, prov… |
| ConsultaComprobante.frm | 2894 | SELECT | DataConsulta.RecordSource = "select retenciones_prov.*, prov… |
| ConsultaComprobante.frm | 12824 | SELECT | rs_retenciones_prov.Open "SELECT * FROM retenciones_prov WHE… |
| trz_trazabilidadComp.frm | 4944 | SELECT | rs_retencion_ib.Open "SELECT retenciones_prov.*,tipo_retenci… |
| CuentaProveedor.frm | 1473 | SELECT | '        rs_retencion_ib.Open "SELECT retenciones_prov.*,tip… |
| Visualiza.bas | 7608 | SELECT | rs_retencion_ib.Open "SELECT retenciones_prov.*,tipo_retenci… |
| Visualiza.bas | 21417 | SELECT | rs_comprobante.Open "SELECT retenciones_prov.* FROM retencio… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)