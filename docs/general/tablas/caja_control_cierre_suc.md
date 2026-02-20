# Tabla `caja_control_cierre_suc`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_caja | BIGINT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| nro_comp_busq | VARCHAR | Sí |  |  |  |
| moneda | CHAR | Sí |  |  |  |
| ingreso | DECIMAL | Sí |  |  |  |
| egreso | DECIMAL | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| codigo_movimiento_anul | DECIMAL | Sí |  |  |  |
| codigo_cliente | INT | Sí |  |  |  |
| codigo_prov | INT | Sí |  |  |  |
| tipo_cp | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |
| cod_gasto | INT | Sí |  |  |  |
| nro_doc | VARCHAR | Sí |  |  |  |
| cod_sucursal | INT | Sí |  |  |  |
| id_caja_abm_origen | INT | Sí |  |  |  |
| id_caja_abm_destino | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_usuario_destino | INT | Sí |  |  |  |
| id_cierre_caja | DECIMAL | Sí |  |  |  |
| id_chequetercero | DECIMAL | Sí |  |  |  |
| nro_comp_cheq | VARCHAR | Sí |  |  |  |
| tipo_comp_cheq | VARCHAR | Sí |  |  |  |
| id_tc_comprobante | DOUBLE | Sí |  |  |  |
| id_boletadeposito | DOUBLE | Sí |  |  |  |
| id_tc_liquidacion | DOUBLE | Sí |  |  |  |
| id_tc | DOUBLE | Sí |  |  |  |
| id_mcp_abm | DOUBLE | Sí |  |  |  |
| id_mcp | DOUBLE | Sí |  |  |  |
| id_ingreso_abm | DOUBLE | Sí |  |  |  |
| id_ingreso | DOUBLE | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_sue_abm_empleado | DOUBLE | Sí |  |  |  |
| importe_fisico | DECIMAL | Sí |  |  |  |
| importe_diferencia | DOUBLE | Sí |  |  |  |
| estado_control | VARCHAR | Sí |  |  |  |
| id_usuario_control | INT | Sí |  |  |  |
| fecha_hora_control | DATETIME | Sí |  |  |  |
| nombre_sucursal | VARCHAR | Sí |  |  |  |
| caja_sucursal | VARCHAR | Sí |  |  |  |
| usuario_sucursal | VARCHAR | Sí |  |  |  |
| monto_cierre_sucursal | DOUBLE | Sí |  |  |  |
| id_caja_cierre_suc | INT | Sí |  |  |  |
| codigo_mov_caja_cierre_suc | BIGINT | Sí |  |  |  |
| tipo_caja_suc | VARCHAR | Sí |  |  |  |

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
| Caja_Control_Sucursales.frm | 820 | SELECT | "FROM caja_control_cierre_suc AS ca  " & _ |
| Caja_Control_Sucursales.frm | 846 | SELECT | "FROM caja_control_cierre_suc AS ca  " & _ |
| CargaMovCaja.frm | 2759 | SELECT | rs_caja.Open "SELECT * FROM caja_control_cierre_suc WHERE co… |
| Caja_Control_Sucursales_Rend.frm | 633 | SELECT | rs_caja_suc.Open "SELECT * FROM caja_control_cierre_suc WHER… |
| Caja.frm | 2816 | SELECT | rs_caja_suc.Open "SELECT codigo_mov_caja_cierre_suc,estado_c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)