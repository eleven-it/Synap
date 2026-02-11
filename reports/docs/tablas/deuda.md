# Tabla `deuda`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_deuda | DOUBLE | No | ✓ |  |  |
| id_deuda_abm | INT | No |  |  |  |
| nombre_deuda | VARCHAR | Sí |  |  |  |
| tipo_deuda | VARCHAR | Sí |  |  |  |
| fecha_deuda | DATE | Sí |  |  |  |
| importe_deuda | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| estado_deuda | VARCHAR | Sí |  |  |  |
| codigo_movimiento_op | DOUBLE | Sí |  |  |  |
| codigo_movimiento_lb | DOUBLE | Sí |  |  |  |
| fecha_emision_deuda | DATE | Sí |  |  |  |
| fecha_vencimiento_deuda | DATE | Sí |  |  |  |
| nro_deuda | VARCHAR | Sí |  |  |  |
| detalle_deuda | VARCHAR | Sí |  |  |  |
| pago | VARCHAR | Sí |  |  |  |
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
| Info_Estadistica.frm | 4145 | SELECT | "Set reporte_flujofondos_temp.imp_deuda = (SELECT sum(deuda.… |
| OrdenPago.frm | 7878 | SELECT | rs_deuda.Open "SELECT * FROM deuda WHERE id_deuda = " & data… |
| OrdenPago.frm | 8000 | SELECT | rs_mp.Open "SELECT * FROM deuda where id_deuda = 1", conn, a… |
| ConsultaComprobante.frm | 13124 | SELECT | rs_deuda_act.Open "SELECT * FROM deuda WHERE id_deuda = " & … |
| ConsultaComprobante.frm | 13333 | SELECT | rs_deuda.Open "SELECT * FROM deuda WHERE codigo_movimiento_o… |
| trz_trazabilidadComp.frm | 5171 | SELECT | rs_deuda.Open "SELECT * FROM deuda WHERE codigo_movimiento_o… |
| CargaDeudaBancaria.frm | 816 | SELECT | rs_NroRef.Open "SELECT nro_deuda from deuda where nro_deuda … |
| CargaDeudaBancaria.frm | 860 | SELECT | rs_deuda.Open "SELECT * FROM deuda where id_deuda = 1 ", con… |
| CuentaProveedor.frm | 1601 | SELECT | '            rs_medpag.Open "SELECT * FROM deuda WHERE codig… |
| LibroBanco.frm | 4334 | SELECT | rs_TDeuda.Open "SELECT * from deuda where codigo_movimiento_… |
| LibroBanco.frm | 4488 | SELECT | rs_deuda.Open "SELECT * from deuda where codigo_movimiento_l… |
| Lista_Deuda.frm | 712 | SELECT | data_deuda.RecordSource = "SELECT * FROM deuda WHERE " & _ |
| Visualiza.bas | 7924 | SELECT | rs_deuda.Open "SELECT * FROM deuda WHERE codigo_movimiento_o… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)