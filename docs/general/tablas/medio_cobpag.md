# Tabla `medio_cobpag`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_mcp | DOUBLE | No | ✓ |  |  |
| id_mcp_abm | DOUBLE | Sí |  |  |  |
| fecha_mcp | DATE | Sí |  |  |  |
| tipo_mcp_tipo | VARCHAR | Sí |  |  |  |
| nombre_mcp | VARCHAR | Sí |  |  |  |
| codigo_movimiento_rec | DOUBLE | Sí |  |  |  |
| codigo_movimiento_op | DOUBLE | Sí |  |  |  |
| fecha_emision_mcp | DATE | Sí |  |  |  |
| fecha_vencimiento_mcp | DATE | Sí |  |  |  |
| nro_mcp | VARCHAR | Sí |  |  |  |
| importe_mcp | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| detalle_mcp | VARCHAR | Sí |  |  |  |
| estado_mcp | VARCHAR | Sí |  |  |  |
| entregado_mcp | VARCHAR | Sí |  |  |  |
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
| Visualiza_ReciboCobro.frm | 7113 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag where id_mcp = 1", co… |
| Visualiza_ReciboCobro.frm | 7331 | SELECT | rs_ingreso.Open "SELECT * FROM medio_cobpag WHERE id_mcp = "… |
| Info_Estadistica.frm | 4136 | SELECT | "(SELECT SUM(medio_cobpag.saldo) FROM medio_cobpag WHERE med… |
| CuentaCliente.frm | 2481 | SELECT | '            rs_mc.Open "SELECT * FROM medio_cobpag WHERE co… |
| OrdenPago.frm | 8041 | SELECT | rs_mct.Open "SELECT * FROM medio_cobpag WHERE id_mcp = " & d… |
| trz_trazabilidad.frm | 7593 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag WHERE codigo_movimien… |
| trz_trazabilidad.frm | 7668 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag WHERE id_mcp = " & rs… |
| ConsultaComprobante.frm | 11340 | SELECT | rs_validacion.Open "SELECT * FROM medio_cobpag WHERE NOT ISN… |
| ConsultaComprobante.frm | 12026 | SELECT | rs_medio_cobpag.Open "SELECT * FROM medio_cobpag WHERE codig… |
| ConsultaComprobante.frm | 12145 | SELECT | rs_ingreso_act.Open "SELECT * FROM medio_cobpag WHERE id_mcp… |
| ConsultaComprobante.frm | 13140 | SELECT | rs_mct.Open "SELECT * FROM medio_cobpag WHERE codigo_movimie… |
| Lista_MC.frm | 759 | SELECT | data_mc.RecordSource = "SELECT * FROM medio_cobpag WHERE " &… |
| trz_trazabilidadComp.frm | 5096 | SELECT | rs_mct.Open "SELECT * FROM medio_cobpag WHERE codigo_movimie… |
| ReciboCobro.frm | 7610 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag where id_mcp = 1", co… |
| ReciboCobro.frm | 7830 | SELECT | rs_ingreso.Open "SELECT * FROM medio_cobpag WHERE id_mcp = "… |
| CuentaProveedor.frm | 1528 | SELECT | '            rs_mct.Open "SELECT * FROM medio_cobpag WHERE c… |
| Visualiza_ReciboCobroC.frm | 6879 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag where id_mcp = 1", co… |
| Visualiza_ReciboCobroC.frm | 7097 | SELECT | rs_ingreso.Open "SELECT * FROM medio_cobpag WHERE id_mcp = "… |
| Visualiza.bas | 6541 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag WHERE codigo_movimien… |
| Visualiza.bas | 6616 | SELECT | rs_mc.Open "SELECT * FROM medio_cobpag WHERE id_mcp = " & rs… |
| Visualiza.bas | 7849 | SELECT | rs_mct.Open "SELECT * FROM medio_cobpag WHERE codigo_movimie… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)