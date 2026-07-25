# Tabla `caja`

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
| cod_vendedor | INT | Sí |  |  |  |
| arqueo_cerrado | VARCHAR | Sí |  |  |  |
| fecha_hora_act_arqueo | DATETIME | Sí |  |  |  |

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
| CargaBDeposito.frm | 1425 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| CargaBDeposito.frm | 1649 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| PNotaCred.frm | 3350 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| PNotaCred.frm | 3354 | SELECT | rs_caja_cierre.Open "SELECT id_cierre_caja,id_caja_abm_desti… |
| PNotaCred.frm | 3379 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| PNotaCred.frm | 6042 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = "… |
| Visualiza_ReciboCobro.frm | 6586 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 6637 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 6944 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 7064 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 7159 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 7270 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 7407 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_ReciboCobro.frm | 12927 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = "… |
| Visualiza_NotaCred.frm | 4973 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = "… |
| NotaCredCon.frm | 2754 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| NotaCredCon.frm | 2758 | SELECT | rs_caja_cierre.Open "SELECT id_cierre_caja,id_caja_abm_desti… |
| NotaCredCon.frm | 2783 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| FacturaB_COPIA.frm | 4313 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| NotaCred_COPIA.frm | 3716 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| NotaCred_COPIA.frm | 3720 | SELECT | rs_caja_cierre.Open "SELECT id_cierre_caja,id_caja_abm_desti… |
| NotaCred_COPIA.frm | 3745 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| ChequeTercero.frm | 2162 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE id_caja = " & DataChe… |
| ChequeTercero.frm | 2178 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE codigo_movimiento =1 … |
| ChequeTercero.frm | 2214 | SELECT | rs_caja.Open "SELECT * from caja where id_chequetercero = " … |
| ChequeTercero.frm | 2232 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 6784 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE caja.codigo_movimient… |
| TPV.frm | 6792 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| TPV.frm | 6796 | SELECT | rs_caja_cierre.Open "SELECT id_cierre_caja,id_caja_abm_desti… |
| TPV.frm | 6839 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 7328 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE caja.codigo_movimient… |
| TPV.frm | 7332 | SELECT | rs_caja_anul.Open "SELECT * from caja where codigo_movimient… |
| TPV.frm | 7344 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| TPV.frm | 7348 | SELECT | '                            rs_caja_cierre.Open "SELECT id_… |
| TPV.frm | 7439 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE caja.codigo_movimient… |
| TPV.frm | 7443 | SELECT | rs_caja_anul.Open "SELECT * from caja where codigo_movimient… |
| TPV.frm | 7454 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| TPV.frm | 7459 | SELECT | '                            rs_caja_cierre.Open "SELECT id_… |
| TPV.frm | 9248 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 9966 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 10099 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 37862 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| TPV.frm | 37964 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE caja.codigo_movimient… |
| TPV.frm | 37972 | SELECT | rs_caja_factura.Open "SELECT id_cierre_caja,id_caja_abm_dest… |
| TPV.frm | 37976 | SELECT | rs_caja_cierre.Open "SELECT id_cierre_caja,id_caja_abm_desti… |
| TPV.frm | 38012 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| CuentaCliente.frm | 2413 | SELECT | '            rs_caja.Open "select * from caja where caja.cod… |
| CargaMovCaja.frm | 1967 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE codigo_movimiento =1 … |
| CargaMovCaja.frm | 2131 | SELECT | rs_consulta_caja.Open "SELECT * FROM caja WHERE isnull(id_ci… |
| CargaMovCaja.frm | 2133 | SELECT | '            rs_consulta_caja.Open "SELECT * FROM caja WHERE… |
| CargaMovCaja.frm | 2160 | UPDATE | conn.Execute "UPDATE caja SET id_cierre_caja = " & contador_… |
| CargaMovCaja.frm | 2168 | JOIN | " INNER JOIN caja on (caja.codigo_movimiento = tc_comprobant… |
| CargaMovCaja.frm | 2184 | UPDATE | conn.Execute "UPDATE caja SET id_cierre_caja = " & contador_… |
| CargaMovCaja.frm | 2190 | JOIN | " INNER JOIN caja on (caja.codigo_movimiento = otro_egreso.c… |
| CargaMovCaja.frm | 2259 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE codigo_movimiento =1 … |
| CargaMovCaja.frm | 3302 | JOIN | " LEFT JOIN caja ON caja.id_chequetercero = chequetercero.ID… |
| OrdenPago.frm | 7209 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| OrdenPago.frm | 7264 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| OrdenPago.frm | 7571 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| OrdenPago.frm | 8075 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| OrdenPago.frm | 8175 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| OrdenPago.frm | 12894 | SELECT | '            rs_caja.Open "SELECT * from caja where codigo_m… |
| OrdenPago.frm | 15437 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE codigo_movimiento = "… |
| Visualiza_PNotaCred_Importe.frm | 2228 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| trz_trazabilidad.frm | 7517 | SELECT | rs_caja.Open "select * from caja where caja.codigo_movimient… |
| Visualiza_FB_Copia.frm | 6336 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = "… |
| Caja_Control_Sucursales_Rend.frm | 904 | SELECT | rs_caja.Open "SELECT * FROM caja WHERE codigo_movimiento =1 … |
| Visualiza_PNotaCredDev.frm | 2898 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Visualiza_PNotaCredDev.frm | 4799 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = "… |
| FacturaB.frm | 5343 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| FacturaB.frm | 8174 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| Clave_Supervisor.frm | 699 | SELECT | '                        " FROM caja " & _ |
| Clave_Supervisor.frm | 793 | SELECT | " FROM caja " & _ |
| CargaExtraccion.frm | 721 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| NotaCred_SinCompO.frm | 4678 | SELECT | '        rs_caja_factura.Open "SELECT id_cierre_caja,id_caja… |
| NotaCred_SinCompO.frm | 4682 | SELECT | '                             "FROM caja " & _ |
| NotaCred_SinCompO.frm | 4687 | SELECT | '            rs_caja_cierre.Open "SELECT id_cierre_caja,id_c… |
| NotaCred_SinCompO.frm | 4712 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| FacturaA.frm | 5056 | SELECT | rs_caja.Open "SELECT * from caja where codigo_movimiento = 1… |
| PNotaDebCopia.frm | 3511 | JOIN | "LEFT JOIN caja ON (caja_abm.id_caja = caja.id_caja_abm_dest… |
| … | … | … | *(234 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 693 | SELECT | FROM caja c |
| services/query_runner.py | 709 | SELECT | FROM caja c |
| services/query_runner.py | 734 | SELECT | FROM caja c |
| services/query_runner.py | 771 | SELECT | FROM caja c |
| services/query_runner.py | 788 | SELECT | FROM caja c2 |
| services/query_runner.py | 796 | SELECT | FROM caja c |
| services/query_runner.py | 814 | SELECT | FROM caja c2 |
| services/query_runner.py | 821 | SELECT | FROM caja c |
| services/query_runner.py | 838 | SELECT | FROM caja |
| services/query_runner.py | 922 | SELECT | FROM caja c |
| services/query_runner.py | 945 | SELECT | FROM caja c |
| services/query_runner.py | 975 | SELECT | FROM caja c |
| services/query_runner.py | 997 | SELECT | FROM caja c |
| services/query_runner.py | 1150 | SELECT | FROM caja c |
| services/query_runner.py | 1167 | SELECT | FROM caja c2 |
| services/query_runner.py | 1175 | SELECT | FROM caja c |
| services/query_runner.py | 1191 | SELECT | FROM caja c2 |
| services/query_runner.py | 1198 | SELECT | FROM caja c |
| services/query_runner.py | 1460 | SELECT | FROM caja c |
| services/query_runner.py | 1714 | SELECT | FROM caja c |
| services/query_runner.py | 1766 | SELECT | FROM caja c |
| services/query_runner.py | 1780 | SELECT | FROM caja c |
| services/query_runner.py | 1836 | SELECT | FROM caja c |

[← Índice de tablas](../DB_INDICE_TABLAS.md)