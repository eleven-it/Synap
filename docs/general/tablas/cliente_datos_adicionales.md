# Tabla `cliente_datos_adicionales`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_datos_adicionales | DOUBLE | No | ✓ |  |  |
| id_deposito_despacho | DOUBLE | Sí |  |  |  |
| Fentrega | VARCHAR | Sí |  |  |  |
| id_transporte | DOUBLE | Sí |  |  |  |
| id_repartidor | DOUBLE | Sí |  |  |  |
| id_cliente_domicilio | DOUBLE | Sí |  |  |  |
| id_cliente_contacto | DOUBLE | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| fechaEntrega | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| origen_pedido | VARCHAR | Sí |  |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| ped_eco | BIGINT | Sí |  |  |  |
| orden_ruta | BIGINT | Sí |  |  |  |
| transmitido | VARCHAR | No |  |  |  |
| operador_logistico | VARCHAR | Sí |  |  |  |
| nro_seguimiento | VARCHAR | Sí |  |  |  |
| id_sucursales_envios | BIGINT | Sí |  |  |  |

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
| Stock_Control_Entrada.frm | 618 | UPDATE | conn.Execute "UPDATE cliente_datos_adicionales " & _ |
| Stock_Control_Entrada.frm | 766 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Visualiza_NotaCred.frm | 6397 | SELECT | rs_da.Open "SELECT * FROM cliente_datos_adicionales WHERE co… |
| NotaCredCon.frm | 1838 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| FacturaB_COPIA.frm | 3673 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| NotaCred_COPIA.frm | 2618 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| ABM_Sucursal_Envio.frm | 532 | SELECT | rs_stock.Open "SELECT * FROM cliente_datos_adicionales WHERE… |
| TPV.frm | 8270 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| TPV.frm | 33974 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| CorreoEnvio2.frm | 2198 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion2.frm | 3299 | SELECT | '                    rs_actualiza_ruta.Open "SELECT id_datos… |
| Logi_Gestion2.frm | 3323 | UPDATE | conn.Execute "UPDATE cliente_datos_adicionales " & _ |
| Logi_Gestion2.frm | 3483 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion2.frm | 4286 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Logi_Gestion2.frm | 6198 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_datos_adicionales ON… |
| Logi_Gestion2.frm | 6353 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion2.frm | 6468 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion2.frm | 6498 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion2.frm | 6547 | JOIN | "INNER JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion2.frm | 6561 | JOIN | "INNER JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion2.frm | 7267 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Logi_Gestion2.frm | 8017 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion2.frm | 8122 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion2.frm | 8226 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion2.frm | 9437 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Visualiza_Pedido.frm | 3950 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Visualiza_Pedido.frm | 9792 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE Co… |
| Visualiza_Pedido.frm | 10722 | SELECT | "from cliente_datos_adicionales " & _ |
| Visualiza_Pedido.frm | 11067 | JOIN | '        " LEFT JOIN cliente_datos_adicionales ON (cliente_d… |
| Visualiza_Pedido.frm | 11082 | JOIN | '            " LEFT JOIN cliente_datos_adicionales ON (clien… |
| Visualiza_Pedido.frm | 11094 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Visualiza_Pedido.frm | 11111 | JOIN | '            " LEFT JOIN cliente_datos_adicionales ON (clien… |
| Visualiza_Pedido.frm | 11129 | JOIN | '            " LEFT JOIN cliente_datos_adicionales ON (clien… |
| Visualiza_Pedido.frm | 14054 | SELECT | '            rs_da.Open "SELECT * From cliente_datos_adicion… |
| Logi_Gestion.frm | 3965 | UPDATE | '            conn.Execute "UPDATE cliente_datos_adicionales … |
| Logi_Gestion.frm | 3987 | SELECT | rs_actualiza_ruta.Open "SELECT id_datos_adicionales,CodigoMo… |
| Logi_Gestion.frm | 4010 | SELECT | '                                rs_actualiza_ruta.Open "SEL… |
| Logi_Gestion.frm | 4495 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 5307 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Logi_Gestion.frm | 5899 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion.frm | 7523 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_datos_adicionales ON… |
| Logi_Gestion.frm | 7723 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 7861 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 7883 | JOIN | '                    "LEFT JOIN cliente_datos_adicionales ON… |
| Logi_Gestion.frm | 7913 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 7944 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 7966 | JOIN | "LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adici… |
| Logi_Gestion.frm | 8047 | JOIN | "INNER JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion.frm | 8061 | JOIN | "INNER JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Logi_Gestion.frm | 8786 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Logi_Gestion.frm | 9532 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion.frm | 9554 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion.frm | 9661 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion.frm | 9768 | SELECT | "From cliente_datos_adicionales " & _ |
| Logi_Gestion.frm | 11093 | SELECT | "FROM cliente_datos_adicionales WHERE CodigoMovimiento = " &… |
| Carga_DatosAdicionales.frm | 2845 | SELECT | ''                  "FROM cliente_datos_adicionales " & _ |
| Carga_DatosAdicionales.frm | 2853 | SELECT | '    rs_datosA.Open "SELECT * FROM cliente_datos_adicionales… |
| trz_trazabilidad.frm | 4969 | SELECT | '        rs_datosA.Open "SELECT cliente_datos_adicionales.* … |
| Stock_Control.frm | 1602 | UPDATE | conn.Execute "UPDATE cliente_datos_adicionales " & _ |
| Stock_Control.frm | 1805 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Stock_Control.frm | 1895 | JOIN | '        " LEFT JOIN cliente_datos_adicionales ON (cliente_d… |
| Stock_Control.frm | 1913 | JOIN | '        " LEFT JOIN cliente_datos_adicionales ON (cliente_d… |
| Stock_Control.frm | 1928 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Stock_Control.frm | 1945 | JOIN | " LEFT JOIN cliente_datos_adicionales ON (cliente_datos_adic… |
| Stock_Control.frm | 2910 | SELECT | "From cliente_datos_adicionales " & _ |
| Visualiza_FB_Copia.frm | 6355 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE Co… |
| FacturaB.frm | 25768 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| NotaCred_SinCompO.frm | 3323 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| FacturaA.frm | 4333 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| ListadoFacturas.frm | 903 | SELECT | "From cliente_datos_adicionales " & _ |
| ListadoFacturas.frm | 1020 | SELECT | "From cliente_datos_adicionales " & _ |
| NotaCred_Importe.frm | 1349 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| Pedido_prep.frm | 4982 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_datos_adicionales ON… |
| Visualiza_FA.frm | 6193 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE Co… |
| NotaCredCopia.frm | 2961 | UPDATE | ' Update cliente_datos_adicionales |
| NotaCredCopia.frm | 2971 | SELECT | '            rs_da.Open "SELECT * From cliente_datos_adicion… |
| NotaCredCopia.frm | 15593 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| Remito.frm | 4004 | SELECT | rs_da.Open "SELECT * From cliente_datos_adicionales WHERE id… |
| Remito.frm | 6187 | SELECT | "From cliente_datos_adicionales " & _ |
| Remito.frm | 6530 | SELECT | "From cliente_datos_adicionales " & _ |
| … | … | … | *(120 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)