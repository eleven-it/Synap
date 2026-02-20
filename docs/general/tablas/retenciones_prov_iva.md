# Tabla `retenciones_prov_iva`

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
| id_retenciones_prov_iva | DOUBLE | No | ✓ |  |  |
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
| OrdenPago.frm | 7805 | SELECT | rs_retencion_iva.Open "select * from retenciones_prov_IVA wh… |
| OrdenPago.frm | 16193 | SELECT | rs_ret_iva.Open "SELECT * FROM retenciones_prov_iva WHERE Co… |
| ConsultaComprobante.frm | 2926 | SELECT | DataConsulta.RecordSource = "select retenciones_prov_iva.*, … |
| ConsultaComprobante.frm | 2932 | SELECT | DataConsulta.RecordSource = "select retenciones_prov_iva.*, … |
| ConsultaComprobante.frm | 12840 | SELECT | rs_retenciones_prov_iva.Open "SELECT * FROM retenciones_prov… |
| Visualiza.bas | 7624 | SELECT | rs_retencion_iva.Open "SELECT retenciones_prov_iva.*,tipo_re… |
| Visualiza.bas | 21624 | SELECT | rs_comprobante.Open "SELECT retenciones_prov_iva.* FROM rete… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)