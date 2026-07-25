# Tabla `resumen_venta_cv`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_resumen_ventas_cv | BIGINT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| comprobante | VARCHAR | Sí |  |  |  |
| importe_neto | DOUBLE | Sí |  |  |  |
| importe_iva_1 | DOUBLE | Sí |  |  |  |
| importe_iva_2 | DECIMAL | Sí |  |  |  |
| importe_percep | DECIMAL | Sí |  |  |  |
| importe_impuesto_interno | DOUBLE | Sí |  |  |  |
| importe_interes | DOUBLE | Sí |  |  |  |
| importe_exento | DOUBLE | Sí |  |  |  |
| importe_total | DECIMAL | Sí |  |  |  |
| total_efectivo | DOUBLE | Sí |  |  |  |
| total_ctacte | DOUBLE | Sí |  |  |  |
| total_tarjeta | DOUBLE | Sí |  |  |  |
| total_cheque | DOUBLE | Sí |  |  |  |
| total_transferencia | DOUBLE | Sí |  |  |  |
| total_otro_medio | DOUBLE | Sí |  |  |  |
| id_cv | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_sucursal | BIGINT | Sí |  |  |  |

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
| NotaCredCon.frm | 11475 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCredCon.frm | 11528 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| NotaCredDesc.frm | 9208 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCredDesc.frm | 9261 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| TPV.frm | 39042 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| TPV.frm | 39131 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| FacturaB.frm | 26456 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCred_SinCompO.frm | 17841 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCred_SinCompO.frm | 17894 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| FacturaA.frm | 22325 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCred_Importe.frm | 11155 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCred_Importe.frm | 11208 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| NotaCredCopia.frm | 16185 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCredCopia.frm | 16238 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| ConsultaComprobante.frm | 6493 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| NotaDeb.frm | 14426 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaDeb.frm | 14473 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| NotaCred.frm | 16869 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaCred.frm | 16922 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| NotaDebCopia.frm | 14077 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| NotaDebCopia.frm | 14124 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| TPV_2.frm | 36375 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| TPV_2.frm | 36464 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |
| Funciones.bas | 8990 | SELECT | rs_consulta.Open "SELECT * FROM resumen_venta_cv WHERE id_re… |
| Funciones.bas | 9145 | SELECT | rs_resumen_venta_cv.Open "SELECT * FROM resumen_venta_cv WHE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)