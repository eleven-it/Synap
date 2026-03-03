# Tabla `distrito`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDDistrito | INT | No | ✓ |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| NombreDistrito | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| cod_postal | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | distrito | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 2997 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente_domici… |
| Info_Stock.frm | 14199 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| CargaTransporte.frm | 1056 | SELECT | DataDistrito.RecordSource = "select * from Distrito where id… |
| CargaTransporte.frm | 1063 | SELECT | DataDistrito.RecordSource = "select * from Distrito where id… |
| Info_Estadistica.frm | 3495 | JOIN | '"From `configuracion`, ((((`cuentacliente` left join `clien… |
| Info_Estadistica.frm | 6155 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Info_Estadistica.frm | 6652 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Info_Estadistica.frm | 6944 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Info_Estadistica.frm | 6985 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Logi_Gestion2.frm | 6233 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion2.frm | 6351 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion2.frm | 6466 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion2.frm | 6496 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion2.frm | 6535 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion2.frm | 6627 | SELECT | DataDistrito.RecordSource = "select * From distrito where id… |
| Facturacion_Ciclica.frm | 2830 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Facturacion_Ciclica.frm | 2845 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Facturacion_Ciclica.frm | 4346 | SELECT | DataDistrito.RecordSource = "select * From distrito where id… |
| Visualiza_Pedido.frm | 10727 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Logi_Gestion.frm | 7579 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion.frm | 7721 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion.frm | 7859 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion.frm | 7881 | JOIN | '                    "LEFT JOIN distrito ON (distrito.IDDist… |
| Logi_Gestion.frm | 7911 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion.frm | 8014 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Logi_Gestion.frm | 8127 | SELECT | DataDistrito.RecordSource = "select * From distrito where id… |
| Logi_Gestion.frm | 9537 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Logi_Gestion.frm | 9666 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Logi_Gestion.frm | 9773 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Visualiza_CliDom.frm | 896 | JOIN | "LEFT JOin distrito ON (distrito.idDistrito = cliente.idDist… |
| Visualiza_CliDom.frm | 919 | JOIN | '                "LEFT JOIN distrito ON (distrito.IDDistrito… |
| Visualiza_CliDom.frm | 934 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente_domici… |
| Carga_DatosAdicionales.frm | 1683 | JOIN | "LEFT OUTER JOIN distrito ON (distrito.IDDistrito = cliente_… |
| Stock_Control.frm | 2915 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Info_Venta_respaldo_bruno.frm | 11995 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Info_Venta.frm | 12417 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Crm_CargaCliPot.frm | 2332 | SELECT | DataDistrito.RecordSource = "SELECT * FROM distrito where id… |
| ListadoFacturas.frm | 908 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ListadoFacturas.frm | 1025 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Exportacion.frm | 2694 | JOIN | "LEFT JOIN distrito d ON d.IDDistrito = c.IDDistrito " & _ |
| Exportacion.frm | 3679 | JOIN | "LEFT JOIN distrito ON (distrito.idDistrito = cliente.idDist… |
| Exportacion.frm | 4493 | JOIN | "LEFT JOIN distrito d ON d.IDDistrito = p.IDDistrito " & _ |
| Pedido_prep.frm | 5019 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Pedido_prep.frm | 5079 | SELECT | DataDistrito.RecordSource = "select * From distrito where id… |
| CargaProveedor.frm | 4562 | SELECT | '        DataDistrito.RecordSource = "select * from Distrito… |
| CargaProveedor.frm | 4569 | SELECT | '        DataDistrito.RecordSource = "select * from Distrito… |
| CargaProveedor.frm | 4593 | SELECT | DataDistrito.RecordSource = "select * from Distrito where id… |
| CargaProveedor.frm | 4601 | SELECT | DataDistrito.RecordSource = "select * from Distrito where id… |
| CargaProveedor.frm | 4667 | SELECT | rs_cp.Open "SELECT * from distrito where IDDistrito = " & Di… |
| Sup_importacion_tablas.frm | 5881 | SELECT | DataDistrito.RecordSource = "SELECT * FROM Distrito WHERE ID… |
| Sup_importacion_tablas.frm | 5889 | SELECT | DataDistrito.RecordSource = "SELECT * FROM Distrito WHERE ID… |
| Carga_ClienteDomicilio.frm | 1882 | SELECT | dataDistritoDomicilio.RecordSource = "select * from Distrito… |
| Carga_ClienteDomicilio.frm | 1891 | SELECT | dataDistritoDomicilio.RecordSource = "select * from Distrito… |
| Carga_ClienteDomicilio.frm | 1956 | SELECT | rs_cp.Open "SELECT * from distrito where IDDistrito = " & Li… |
| Facturacion.frm | 3496 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente_domici… |
| Pedido_Avanzado.frm | 4251 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 4523 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 4772 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 6732 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 9613 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 9851 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| Pedido_Avanzado.frm | 10062 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Pedido_Avanzado.frm | 10111 | JOIN | '                    "LEFT JOIN distrito ON (distrito.IDDist… |
| Pedido_Avanzado.frm | 10137 | JOIN | "LEFT JOIN distrito ON (distrito.IDDistrito = cliente.IDDist… |
| Pedido_Avanzado.frm | 13085 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 13205 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Pedido_Avanzado.frm | 13351 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Info_Comercial.frm | 9794 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| ConsultaComprobante.frm | 14595 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 15189 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 16852 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 17802 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 26906 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 31939 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 32863 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| ConsultaComprobante.frm | 35156 | JOIN | "LEFT JOIN distrito ON (distrito.iddistrito = cliente_domici… |
| Info_Pago.frm | 2875 | SELECT | DataDistrito.RecordSource = "select * from distrito where id… |
| ABMDpto.frm | 1158 | SELECT | DataDistrito.RecordSource = "SELECT * FROM distrito WHERE " … |
| ABMDpto.frm | 1164 | SELECT | DataDistrito.RecordSource = "SELECT * FROM distrito where ID… |
| ABMDpto.frm | 1246 | SELECT | DataDistrito.RecordSource = "SELECT * FROM distrito WHERE " … |
| … | … | … | *(70 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)