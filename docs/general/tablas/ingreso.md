# Tabla `ingreso`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ingreso | DOUBLE | No | ✓ |  |  |
| id_ingreso_abm | DOUBLE | Sí |  |  |  |
| fecha_ingreso | DATE | Sí |  |  |  |
| nombre_ingreso | VARCHAR | Sí |  |  |  |
| codigo_movimiento_rec | DOUBLE | Sí |  |  |  |
| codigo_movimiento_op | DOUBLE | Sí |  |  |  |
| fecha_emision_ingreso | DATE | Sí |  |  |  |
| fecha_vencimiento_ingreso | DATE | Sí |  |  |  |
| nro_ingreso | VARCHAR | Sí |  |  |  |
| importe_ingreso | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| detalle_ingreso | VARCHAR | Sí |  |  |  |
| estado_ingreso | VARCHAR | Sí |  |  |  |
| entregado_ingreso | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7213 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = 1"… |
| Visualiza_ReciboCobro.frm | 7326 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = " … |
| Info_Estadistica.frm | 4135 | SELECT | "(SELECT SUM(ingreso.saldo) FROM ingreso WHERE ingreso.anula… |
| CuentaCliente.frm | 2522 | SELECT | '            rs_mc.Open "SELECT * FROM ingreso WHERE codigo_… |
| OrdenPago.frm | 8141 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = " … |
| trz_trazabilidad.frm | 7644 | SELECT | rs_mc.Open "SELECT * FROM ingreso WHERE id_ingreso = " & rs_… |
| trz_trazabilidad.frm | 7653 | SELECT | rs_mc.Open "SELECT * FROM ingreso WHERE id_ingreso = " & rs_… |
| Lista_Ingresos.frm | 751 | SELECT | data_ingreso.RecordSource = "SELECT * FROM ingreso WHERE " &… |
| Lista_Ingresos.frm | 765 | SELECT | data_ingreso.RecordSource = "SELECT * FROM ingreso WHERE " &… |
| ConsultaComprobante.frm | 11329 | SELECT | rs_validacion.Open "SELECT * FROM ingreso WHERE NOT ISNULL(c… |
| ConsultaComprobante.frm | 12134 | SELECT | rs_ingreso_act.Open "SELECT * FROM ingreso WHERE id_ingreso … |
| ConsultaComprobante.frm | 13238 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE codigo_movimien… |
| trz_trazabilidadComp.frm | 5134 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE codigo_movimien… |
| ReciboCobro.frm | 7711 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = 1"… |
| ReciboCobro.frm | 7825 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = " … |
| CuentaProveedor.frm | 1565 | SELECT | '            rs_ingreso.Open "SELECT * FROM ingreso WHERE co… |
| Visualiza_ReciboCobroC.frm | 6979 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = 1"… |
| Visualiza_ReciboCobroC.frm | 7092 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE id_ingreso = " … |
| Visualiza.bas | 6592 | SELECT | rs_mc.Open "SELECT * FROM ingreso WHERE id_ingreso = " & rs_… |
| Visualiza.bas | 6601 | SELECT | rs_mc.Open "SELECT * FROM ingreso WHERE id_ingreso = " & rs_… |
| Visualiza.bas | 7887 | SELECT | rs_ingreso.Open "SELECT * FROM ingreso WHERE codigo_movimien… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)