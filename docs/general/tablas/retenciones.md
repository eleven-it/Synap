# Tabla `retenciones`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_retenciones | DOUBLE | No | ✓ |  |  |
| CodRetencion | INT | No |  |  |  |
| NroCertificado | DECIMAL | No |  |  |  |
| NroREC | VARCHAR | No |  |  |  |
| CodCliente | INT | No |  |  |  |
| Fecha | DATE | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| CodAgentRet | INT | Sí |  |  |  |
| Anulado | VARCHAR | No |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| tipo_retencion | VARCHAR | Sí |  |  |  |
| CodBanco | DOUBLE | Sí |  |  |  |
| id_tc_liquidacion | DOUBLE | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7470 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones where codigo_… |
| Info_Impositivo.frm | 2979 | SELECT | "From retenciones " & _ |
| CuentaCliente.frm | 2327 | SELECT | '        rs_retenciones.Open "SELECT * FROM retenciones WHER… |
| trz_trazabilidad.frm | 7429 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones WHERE codigo_… |
| Exportacion.frm | 879 | SELECT | rs_factura.Open "SELECT retenciones.*,retenciones.fecha as f… |
| Exportacion.frm | 956 | SELECT | rs_factura.Open "SELECT retenciones.*,tipo_retencion_cli.*,c… |
| CargaGastoBancario.frm | 961 | SELECT | rs_retenciones.Open "SELECT * from retenciones where id_rete… |
| ConsultaComprobante.frm | 11705 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones WHERE codigo_… |
| CargaLiquidacionTC.frm | 1740 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones where codigo_… |
| ReciboCobro.frm | 7964 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones where codigo_… |
| Visualiza_ReciboCobroC.frm | 7236 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones where codigo_… |
| CargaRetencion.frm | 566 | SELECT | DataRetencion.RecordSource = "SELECT * FROM retenciones WHER… |
| CargaRetencion.frm | 616 | SELECT | '            DataRetencion.RecordSource = "SELECT * FROM ret… |
| CargaRetencion.frm | 669 | SELECT | DataRetencion.RecordSource = "SELECT * FROM retenciones WHER… |
| LibroBanco.frm | 2526 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones where id_tc_l… |
| LibroBanco.frm | 3118 | SELECT | rs_retenciones.Open "SELECT * from retenciones where codigo_… |
| LibroBanco.frm | 3286 | SELECT | rs_retenciones.Open "SELECT * from retenciones where codigo_… |
| LibroBanco.frm | 4265 | SELECT | 'CargaLiquidacionTC.DataRetencionTemp.RecordSource = "SELECT… |
| LibroBanco.frm | 4267 | SELECT | CargaLiquidacionTC.DataRetencionTemp.RecordSource = "SELECT … |
| Visualiza.bas | 6315 | SELECT | rs_retenciones.Open "SELECT * FROM retenciones WHERE codigo_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)