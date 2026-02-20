# Tabla `descuento_rec`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodDescuento | INT | No | ✓ |  |  |
| NombreDescuento | VARCHAR | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| Descripcion | VARCHAR | No |  |  |  |
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
| Visualiza_ReciboCobro.frm | 8204 | SELECT | rs_descuento_rec.Open "select * from descuento_rec where Cod… |
| Visualiza_ReciboCobro.frm | 9297 | SELECT | DataDesc.RecordSource = "select * from Descuento_REC order b… |
| CuentaCliente.frm | 2368 | SELECT | '        Visualiza_ReciboCobro.DataDesc.RecordSource = "SELE… |
| OrdenPago.frm | 10138 | SELECT | DataDesc.RecordSource = "select * from descuento_rec order b… |
| OrdenPago.frm | 12383 | SELECT | rs_calculo_descuento.Open "SELECT * FROM descuento_rec WHERE… |
| trz_trazabilidad.frm | 7470 | SELECT | Visualiza_ReciboCobro.DataDesc.RecordSource = "SELECT * FROM… |
| CargaDescREC.frm | 244 | SELECT | rs_descRec.Open "SELECT * FROM descuento_rec WHERE CodDescue… |
| CargaDescREC.frm | 266 | SELECT | ABMDescuentoREC.DataDescRec.RecordSource = "SELECT * FROM de… |
| CargaDescREC.frm | 276 | SELECT | rs_descRec.Open "SELECT * FROM descuento_rec WHERE CodDescue… |
| ABMDescuentoREC.frm | 358 | SELECT | DataDescRec.RecordSource = "select * from descuento_rec wher… |
| trz_trazabilidadComp.frm | 4931 | SELECT | Visualiza_OrdenPago.DataDesc.RecordSource = "select * from D… |
| Visualiza_OrdenPagoC.frm | 7215 | SELECT | DataDesc.RecordSource = "select * from descuento_rec order b… |
| Visualiza_OrdenPagoC.frm | 8552 | SELECT | rs_calculo_descuento.Open "SELECT * FROM descuento_rec WHERE… |
| ReciboCobro.frm | 8654 | SELECT | rs_descuento_rec.Open "select * from descuento_rec where Cod… |
| ReciboCobro.frm | 9969 | SELECT | DataDesc.RecordSource = "select * from Descuento_REC order b… |
| CuentaProveedor.frm | 1461 | SELECT | '        Visualiza_OrdenPago.DataDesc.RecordSource = "select… |
| Visualiza_ReciboCobroC.frm | 7970 | SELECT | rs_descuento_rec.Open "select * from descuento_rec where Cod… |
| Visualiza_ReciboCobroC.frm | 8955 | SELECT | DataDesc.RecordSource = "select * from Descuento_REC order b… |
| Visualiza_OrdenPago.frm | 7507 | SELECT | DataDesc.RecordSource = "select * from descuento_rec order b… |
| Visualiza_OrdenPago.frm | 8946 | SELECT | rs_calculo_descuento.Open "SELECT * FROM descuento_rec WHERE… |
| Visualiza.bas | 6356 | SELECT | Visualiza_ReciboCobro.DataDesc.RecordSource = "SELECT * FROM… |
| Visualiza.bas | 7595 | SELECT | Visualiza_OrdenPago.DataDesc.RecordSource = "select * from D… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)