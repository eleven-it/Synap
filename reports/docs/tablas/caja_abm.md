# Tabla `caja_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_caja | INT | No | ✓ |  |  |
| tipo_caja | VARCHAR | Sí |  |  |  |
| nombre_caja | VARCHAR | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_pc_dolares | DOUBLE | Sí |  |  |  |
| limite_efectivo | DECIMAL | Sí |  |  |  |
| activa_limite_efectivo | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 1859 | SELECT | "FROM caja_abm,sucursales,caja_saldo WHERE (tipo_caja = 'Acu… |
| CargaBDeposito.frm | 1866 | SELECT | data_caja_cheque.RecordSource = "SELECT caja_abm.*,sucursale… |
| CargaBDeposito.frm | 1874 | SELECT | "FROM caja_abm,sucursales,caja_saldo WHERE (tipo_caja = 'Acu… |
| CargaBDeposito.frm | 1882 | SELECT | data_caja_cheque.RecordSource = "SELECT caja_abm.*,sucursale… |
| CargaBDeposito.frm | 2217 | SELECT | rs_caja_abm.Open "SELECT * FROM caja_abm WHERE id_caja = " &… |
| CargaBDeposito.frm | 2376 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & caj… |
| CargaBDeposito.frm | 2466 | SELECT | rs_ValDepo.Open "SELECT * from caja_abm where id_caja = " & … |
| PNotaCred.frm | 6234 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_ReciboCobro.frm | 9392 | SELECT | data_caja.RecordSource = "SELECT * FROM caja_abm WHERE tipo_… |
| Visualiza_ReciboCobro.frm | 9398 | SELECT | data_caja.RecordSource = "SELECT * FROM caja_abm WHERE (tipo… |
| Visualiza_ReciboCobro.frm | 9417 | SELECT | data_caja_cheque.RecordSource = "SELECT caja_abm.*,sucursale… |
| Visualiza_ReciboCobro.frm | 9424 | SELECT | '        data_caja_cheque.RecordSource = "SELECT caja_abm.*,… |
| Visualiza_ReciboCobro.frm | 9425 | SELECT | data_caja_cheque.RecordSource = "SELECT caja_abm.*,sucursale… |
| Visualiza_ReciboCobro.frm | 13412 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_ReciboCobro.frm | 13444 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_ReciboCobro.frm | 14415 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_ReciboCobro.frm | 14447 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_NotaCred.frm | 5470 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| CargaUsuario.frm | 2088 | SELECT | data_caja.RecordSource = "SELECT * FROM caja_abm WHERE tipo_… |
| CargaUsuario.frm | 2093 | SELECT | data_caja_cheque.RecordSource = "SELECT * FROM caja_abm WHER… |
| CargaUsuario.frm | 2098 | SELECT | data_caja_cheque_deposito.RecordSource = "SELECT * FROM caja… |
| CargaUsuario.frm | 2103 | SELECT | data_caja_tarjeta.RecordSource = "SELECT * FROM caja_abm WHE… |
| Info_Estadistica.frm | 3694 | JOIN | '                                  " LEFT JOIN caja_abm ON (… |
| Info_Estadistica.frm | 3962 | JOIN | " LEFT JOIN caja_abm ON (caja_abm.id_caja = caja_saldo.id_ca… |
| NotaCredCon.frm | 7195 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & id_… |
| FacturaB_COPIA.frm | 11324 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| NotaCredDesc.frm | 4277 | SELECT | '        rs_caja.Open "SELECT * from caja_abm where id_caja … |
| NotaCred_COPIA.frm | 8674 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & id_… |
| Visualiza_TPV.frm | 8641 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_TPV.frm | 9942 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_TPV.frm | 10146 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 18473 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 18515 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 20220 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 20260 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 20464 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| TPV.frm | 20504 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & Pri… |
| Visualiza_NotaCredDesc.frm | 2075 | SELECT | '        rs_caja.Open "SELECT * from caja_abm where id_caja … |
| CuentaCliente.frm | 2418 | SELECT | '                Visualiza_ReciboCobro.data_caja.RecordSourc… |
| CargaMovCaja.frm | 1436 | SELECT | data_caja_origen.RecordSource = "SELECT * FROM caja_abm WHER… |
| CargaMovCaja.frm | 1441 | SELECT | data_caja_origen.RecordSource = "SELECT * FROM caja_abm WHER… |
| CargaMovCaja.frm | 1449 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 1457 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 1463 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 1478 | SELECT | data_caja_origen.RecordSource = "SELECT * FROM caja_abm WHER… |
| CargaMovCaja.frm | 1483 | SELECT | data_caja_origen.RecordSource = "SELECT * FROM caja_abm WHER… |
| CargaMovCaja.frm | 1497 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 1512 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm WHER… |
| CargaMovCaja.frm | 1524 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 1551 | SELECT | rs_caja_abm.Open "SELECT * FROM caja_abm WHERE id_caja = " &… |
| CargaMovCaja.frm | 1961 | SELECT | rs_caja_abm.Open "SELECT * FROM caja_abm WHERE id_caja = " &… |
| CargaMovCaja.frm | 2935 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 2943 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 2958 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 2965 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 2977 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 2987 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3000 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3028 | JOIN | "INNER JOIN caja_abm ON " & _ |
| CargaMovCaja.frm | 3036 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3042 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3057 | JOIN | "INNER JOIN caja_abm ON " & _ |
| CargaMovCaja.frm | 3064 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3070 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3084 | JOIN | "INNER JOIN caja_abm ON " & _ |
| CargaMovCaja.frm | 3092 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3098 | SELECT | data_caja_destino.RecordSource = "SELECT * FROM caja_abm WHE… |
| CargaMovCaja.frm | 3112 | SELECT | '        data_caja_destino.RecordSource = "SELECT * FROM caj… |
| CargaMovCaja.frm | 3303 | JOIN | " LEFT JOIN caja_abm ON caja.id_caja_abm_destino = caja_abm.… |
| CargaMovCaja.frm | 3539 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 3565 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 3581 | SELECT | data_caja_origen.RecordSource = "SELECT * from caja_abm wher… |
| CargaMovCaja.frm | 3700 | SELECT | rs_caja_abm.Open "SELECT * FROM caja_abm WHERE id_caja = " &… |
| CargaMovCaja.frm | 3927 | SELECT | rs_cajaorigen.Open "SELECT * from caja_abm where id_caja = "… |
| CargaMovCaja.frm | 3931 | SELECT | rs_cajadestino.Open "SELECT * from caja_abm where id_caja = … |
| CargaMovCaja.frm | 3937 | SELECT | rs_cajadestino.Open "SELECT * from caja_abm where id_caja = … |
| CargaMovCaja.frm | 3994 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & caj… |
| CargaMovCaja.frm | 4093 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & caj… |
| CargaMovCaja.frm | 4172 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & caj… |
| CargaMovCaja.frm | 4220 | SELECT | rs_caja.Open "SELECT * from caja_abm where id_caja = " & caj… |
| … | … | … | *(216 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| api_views.py | 635 | SELECT | FROM caja_abm |
| services/query_runner.py | 1463 | JOIN | LEFT JOIN caja_abm caja_origen ON caja_origen.id_caja = c.id… |
| services/query_runner.py | 1464 | JOIN | LEFT JOIN caja_abm caja_destino ON caja_destino.id_caja = c.… |
| services/query_runner.py | 1715 | JOIN | LEFT JOIN caja_abm caja_origen ON caja_origen.id_caja = c.id… |
| services/query_runner.py | 1716 | JOIN | LEFT JOIN caja_abm caja_destino ON caja_destino.id_caja = c.… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)