# Tabla `cliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Codigo | INT | No | ✓ |  |  |
| TipoCliente | INT | Sí |  |  |  |
| nombre_cliente | VARCHAR | Sí |  |  |  |
| Calle | VARCHAR | Sí |  |  |  |
| NroCalle | VARCHAR | Sí |  |  |  |
| Dpto | VARCHAR | Sí |  |  |  |
| IDDistrito | INT | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| telefono | VARCHAR | Sí |  |  |  |
| Email | VARCHAR | Sí |  |  |  |
| Fax | VARCHAR | Sí |  |  |  |
| NombreContacto | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| Credito | DECIMAL | Sí |  |  |  |
| Descuento | DECIMAL | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| Observaciones | MEDIUMTEXT | Sí |  |  |  |
| ListaPrecio | VARCHAR | No |  |  |  |
| FechaAlta | TIMESTAMP | No |  |  |  |
| Estado | VARCHAR | No |  |  |  |
| NroIngBrutos | VARCHAR | Sí |  |  |  |
| NroAgenteRetencion | VARCHAR | Sí |  |  |  |
| saldo | DECIMAL | Sí |  |  |  |
| id_manual_cli | VARCHAR | Sí |  |  |  |
| id_cv | INT | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| credito_cheque | DECIMAL | Sí |  |  |  |
| credito_limite_dias | DECIMAL | Sí |  |  |  |
| credito_cheque_tercero | DECIMAL | No |  |  |  |
| cliente_ecommerce | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| aviso | MEDIUMTEXT | Sí |  |  |  |
| habilita_aviso | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| id_cobrador | INT | Sí |  |  |  |
| descuento_por_cli | DECIMAL | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| id_categoria | DOUBLE | Sí |  |  |  |
| whatsapp_empresa | VARCHAR | Sí |  |  |  |
| web_empresa | VARCHAR | Sí |  |  |  |
| habilita_sp | VARCHAR | Sí |  |  |  |
| nombre_fantasia | VARCHAR | Sí |  |  |  |
| habilita_pd | VARCHAR | Sí |  |  |  |
| id_cliente_grupo | BIGINT | Sí |  |  |  |
| fecha_ultima_compra | DATE | Sí |  |  |  |
| id_tiendanube | BIGINT | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | cliente | Info_Estadistica.frm | 3361 | '"From `configuracion`,`stock` INNER JOIN cliente ON (`cliente`.`codigo` = `stoc… |
| configuracion | cliente | Info_Estadistica.frm | 3495 | '"From `configuracion`, ((((`cuentacliente` left join `cliente` on((`cuentaclien… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 1650 | SELECT | DataTotal.RecordSource = "SELECT SQL_CALC_FOUND_ROWS Codigo … |
| Cliente.frm | 1727 | SELECT | ''        DataCliente.RecordSource = "select Cliente.*, Tipo… |
| Cliente.frm | 1826 | SELECT | '        DataTotal.RecordSource = "SELECT SQL_CALC_FOUND_ROW… |
| Cliente.frm | 2233 | SELECT | Crm_CargaLlamada.DataCli.RecordSource = "SELECT codigo, nomb… |
| Cliente.frm | 3117 | SELECT | conn.Execute "delete from cliente where Codigo = " & DataCli… |
| Cliente.frm | 3117 | DELETE | conn.Execute "delete from cliente where Codigo = " & DataCli… |
| Cliente.frm | 3242 | SELECT | 'DataConsCliente.RecordSource = "select Cliente.*, Tipo_Clie… |
| Cliente.frm | 3248 | SELECT | " FROM cliente " & _ |
| Cliente.frm | 4072 | SELECT | "From Cliente " & _ |
| Info_Stock.frm | 11825 | SELECT | Data_Cliente.RecordSource = "SELECT codigo, nombre_cliente F… |
| Stock_Control_Entrada.frm | 765 | JOIN | " LEFT JOIN cliente ON (cliente.codigo = cuentacliente.Codig… |
| Visualiza_ReciboCobro.frm | 6539 | SELECT | .Source = "select cliente.codigo,cliente.saldo from cliente … |
| Visualiza_ReciboCobro.frm | 6550 | SELECT | rs_cliente.Open "SELECT * FROM cliente where codigo = " & Co… |
| Visualiza_ReciboCobro.frm | 9225 | SELECT | .Source = "SELECT saldo,Codigo FROM cliente WHERE " & _ |
| Visualiza_ReciboCobro.frm | 9689 | JOIN | "LEFT JOIN cliente ON cliente.Codigo = erp_proyecto.id_clien… |
| Visualiza_ReciboCobro.frm | 12320 | SELECT | rs_cliente.Open "SELECT * FROM cliente WHERE Codigo = " & Da… |
| Visualiza_ReciboCobro.frm | 14047 | SELECT | rs_caja.Open "SELECT * from cliente where codigo = " & Codig… |
| Visualiza_NotaCred.frm | 2475 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| Visualiza_NotaCred.frm | 2679 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| Visualiza_NotaCred.frm | 2996 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| Visualiza_NotaCred.frm | 5437 | SELECT | rs_caja.Open "SELECT * from cliente where codigo = " & Codig… |
| Erp_Carga_Parte_Diario.frm | 2575 | JOIN | " LEFT JOIN cliente ON cliente.Codigo=py.id_cliente" & _ |
| Erp_Carga_Parte_Diario.frm | 2750 | JOIN | '                                          " LEFT JOIN clien… |
| Erp_Carga_Parte_Diario.frm | 3912 | JOIN | " LEFT JOIN `cliente`   ON cliente.Codigo = erp_proyecto.`id… |
| Info_Estadistica.frm | 3361 | JOIN | '"From `configuracion`,`stock` INNER JOIN cliente ON (`clien… |
| Info_Estadistica.frm | 3495 | JOIN | '"From `configuracion`, ((((`cuentacliente` left join `clien… |
| Info_Estadistica.frm | 4389 | SELECT | '        rs_uni.Open "SELECT count(Cliente.nombre_cliente) a… |
| Info_Estadistica.frm | 4714 | SELECT | '        rs_uni.Open "SELECT count(Cliente.nombre_cliente) a… |
| Info_Estadistica.frm | 7126 | SELECT | '        rs_uni.Open "SELECT count(Cliente.nombre_cliente) a… |
| Info_Estadistica.frm | 7146 | SELECT | 'rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant F… |
| Info_Estadistica.frm | 7148 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 7174 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 7201 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 7601 | SELECT | 'rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant F… |
| Info_Estadistica.frm | 7603 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 7629 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 7656 | SELECT | rs_uni.Open "SELECT count(Cliente.nombre_cliente) as cant Fr… |
| Info_Estadistica.frm | 8755 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8774 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8791 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8810 | JOIN | " LEFT JOIN `cliente` ON((`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8935 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8956 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8975 | JOIN | " LEFT JOIN `cliente` ON (`cliente`.`Codigo` = `stock`.`Codi… |
| Info_Estadistica.frm | 8996 | JOIN | " LEFT JOIN `cliente` ON((`cliente`.`Codigo` = `stock`.`Codi… |
| Visualiza_CargaMovStock.frm | 4188 | SELECT | data_entidad.RecordSource = "SELECT codigo, nombre_cliente F… |
| Visualiza_CargaMovStock.frm | 4350 | JOIN | "LEFT JOIN cliente ON cliente.Codigo = erp_proyecto.id_clien… |
| NotaCredCon.frm | 2597 | SELECT | .Source = "select cliente.codigo,cliente.saldo from cliente … |
| NotaCredCon.frm | 2607 | SELECT | rs_cliente.Open "SELECT cliente.codigo,cliente.saldo FROM cl… |
| NotaCredCon.frm | 2622 | SELECT | .Source = "select cliente.codigo,cliente.saldo from cliente … |
| NotaCredCon.frm | 2637 | SELECT | rs_cliente.Open "SELECT cliente.codigo,cliente.saldo FROM cl… |
| NotaCredCon.frm | 3197 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 3538 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 3841 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 4350 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 4617 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 4875 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 5120 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 5358 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 6101 | JOIN | "LEFT JOIN cliente ON cliente.Codigo = erp_proyecto.id_clien… |
| NotaCredCon.frm | 7162 | SELECT | rs_caja.Open "SELECT * from cliente where codigo = " & Codig… |
| NotaCredCon.frm | 7778 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 9234 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 10365 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| NotaCredCon.frm | 10896 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| Configuracion_Adicional2.frm | 3900 | SELECT | rs_listaPcf.Open "SELECT codigo,listaprecio from cliente whe… |
| Configuracion_Adicional2.frm | 4058 | SELECT | rs_listacf.Open "SELECT * from cliente where codigo = 1", co… |
| FacturaB_COPIA.frm | 4203 | SELECT | .Source = "select cliente.codigo,cliente.saldo from cliente … |
| FacturaB_COPIA.frm | 4223 | SELECT | rs_cliente.Open "SELECT * FROM cliente where codigo = " & CD… |
| FacturaB_COPIA.frm | 5245 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| FacturaB_COPIA.frm | 5506 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| FacturaB_COPIA.frm | 6042 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| FacturaB_COPIA.frm | 6387 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| FacturaB_COPIA.frm | 6678 | SELECT | rs_informe.Open "SELECT * FROM cliente WHERE Codigo = " & Co… |
| FacturaB_COPIA.frm | 11048 | SELECT | rs_camposL.Open "SELECT * from cliente where codigo = " & Co… |
| FacturaB_COPIA.frm | 11055 | SELECT | rs_limitescli.Open "SELECT * from cliente where codigo= " & … |
| FacturaB_COPIA.frm | 11140 | JOIN | "INNER JOIN cliente ON (cliente.Codigo = chequetercero.CodCl… |
| FacturaB_COPIA.frm | 11165 | JOIN | "INNER JOIN cliente ON (cliente.Codigo = chequetercero.CodCl… |
| FacturaB_COPIA.frm | 11354 | SELECT | rs_caja.Open "SELECT * from cliente where codigo = " & Codig… |
| FacturaB_COPIA.frm | 12410 | JOIN | "LEFT JOIN cliente ON cliente.Codigo = erp_proyecto.id_clien… |
| … | … | … | *(878 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| api_views.py | 664 | SELECT | FROM cliente |
| services/query_runner.py | 1461 | JOIN | LEFT JOIN cliente cli ON cli.Codigo = c.codigo_cliente |
| services/query_runner.py | 3031 | JOIN | INNER JOIN cliente cl ON cl.Codigo = cc.Codigo |
| services/query_runner.py | 3334 | JOIN | LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo |
| services/query_runner.py | 3387 | JOIN | LEFT JOIN cliente cli ON cli.Codigo = cp_res.Codigo |
| services/query_runner.py | 3559 | JOIN | LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo |

[← Índice de tablas](../DB_INDICE_TABLAS.md)