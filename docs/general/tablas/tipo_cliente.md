# Tabla `tipo_cliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDTipoCliente | INT | No | ✓ |  |  |
| NombreTipoCliente | VARCHAR | Sí |  |  |  |
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
| Cliente.frm | 1636 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Cliente.frm | 1713 | SELECT | '                                    "FROM Tipo_Cliente, Con… |
| Cliente.frm | 1738 | SELECT | '                                    "FROM tipo_cliente, con… |
| Cliente.frm | 1759 | SELECT | '                                    "FROM Tipo_Cliente, Con… |
| Cliente.frm | 1773 | SELECT | '                                    "FROM tipo_cliente, con… |
| Cliente.frm | 1794 | SELECT | '                                    "FROM Tipo_Cliente, Con… |
| Cliente.frm | 1807 | SELECT | '                                    "FROM tipo_cliente, con… |
| Cliente.frm | 3249 | JOIN | " LEFT JOIN Tipo_Cliente ON Cliente.TipoCliente = Tipo_Clien… |
| CargaTipoCliente.frm | 217 | SELECT | rs_tipoCliente.Open "SELECT * FROM tipo_cliente WHERE IDTipo… |
| CargaTipoCliente.frm | 235 | SELECT | ABMTipoCliente.DataTipoCliente.RecordSource = "SELECT * FROM… |
| CargaTipoCliente.frm | 246 | SELECT | rs_tipoCliente.Open "SELECT * FROM tipo_cliente WHERE IDTipo… |
| Articulo_tipo_cliente.frm | 773 | SELECT | DataTipoCli.RecordSource = "select * from tipo_cliente WHERE… |
| Info_Estadistica.frm | 5962 | SELECT | DataTipoCli.RecordSource = "SELECT * FROM tipo_cliente ORDER… |
| ABMTipoCliente.frm | 364 | SELECT | DataTipoCliente.RecordSource = "select * from Tipo_Cliente o… |
| ABMTipoCliente.frm | 476 | SELECT | consulta = "select * from Tipo_Cliente " & _ |
| Facturacion_Ciclica.frm | 2027 | SELECT | DataTipoCli.RecordSource = "SELECT * FROM tipo_cliente " & _ |
| Facturacion_Ciclica.frm | 2825 | JOIN | "LEFT JOIN tipo_cliente ON (cliente.tipoCliente = tipo_clien… |
| Facturacion_Ciclica.frm | 2840 | JOIN | "LEFT JOIN tipo_cliente ON (cliente.tipoCliente = tipo_clien… |
| Info_Venta_respaldo_bruno.frm | 10133 | SELECT | DataTipoCli.RecordSource = "SELECT * FROM tipo_cliente WHERE… |
| Info_Venta.frm | 10221 | SELECT | DataTipoCli.RecordSource = "SELECT * FROM tipo_cliente WHERE… |
| Exportacion.frm | 3682 | JOIN | "LEFT JOIN tipo_cliente ON (tipo_cliente.IdTipoCliente = cli… |
| Sup_importacion_tablas.frm | 6088 | SELECT | DataTipoCliente.RecordSource = "SELECT * FROM Tipo_Cliente W… |
| Facturacion.frm | 3237 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3542 | JOIN | " LEFT JOIN Tipo_Cliente ON Cliente.TipoCliente = Tipo_Clien… |
| Facturacion.frm | 3880 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3895 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3915 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3929 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3949 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Facturacion.frm | 3964 | SELECT | '        "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Info_Comercial.frm | 8173 | SELECT | DataTipoCli.RecordSource = "select * from tipo_cliente order… |
| CargaComprobantesPed.frm | 1746 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| adm_felectronicas_consulta.frm | 2442 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| adm_felectronicas_consulta.frm | 2615 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| adm_felectronicas_consulta.frm | 2799 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Carga_Cliente.frm | 6286 | SELECT | DataTipoCliente.RecordSource = "select * from Tipo_Cliente W… |
| Info_Cobranza.frm | 5701 | SELECT | DataTipoCliente.RecordSource = "select * from tipo_cliente W… |
| Lista_Comp_Fact.frm | 2175 | JOIN | "LEFT JOIN tipo_cliente ON (cliente.tipoCliente = tipo_clien… |
| Lista_Comp_Fact.frm | 2201 | JOIN | "LEFT JOIN tipo_cliente ON (cliente.tipoCliente = tipo_clien… |
| Lista_Comp_Fact.frm | 2445 | SELECT | DataTipoCli.RecordSource = "SELECT * FROM tipo_cliente " & _ |
| Geolocalizacion_Comprobante.frm | 2270 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| CargaComprobantesC.frm | 4167 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| Geolocalizacion_Cliente.frm | 2020 | SELECT | "FROM tipo_cliente, contribuyentes, cliente " & _ |
| TPV_Cliente_Comun.frm | 2006 | SELECT | DataTipoCliente.RecordSource = "select * from Tipo_Cliente o… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)