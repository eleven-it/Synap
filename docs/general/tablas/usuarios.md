# Tabla `usuarios`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_usuario | INT | No | ✓ |  |  |
| cod_usuario | VARCHAR | Sí |  |  |  |
| nombre_usuario | VARCHAR | Sí |  |  |  |
| apellido_usuario | VARCHAR | Sí |  |  |  |
| password_usuario | TINYBLOB | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| baja_usuario | VARCHAR | No |  |  |  |
| id_sucursal | INT | No |  |  |  |
| id_empresa | INT | No |  |  |  |
| pv | INT | Sí |  |  |  |
| pvc | INT | Sí |  |  |  |
| tipo_busq | VARCHAR | Sí |  |  |  |
| id_deposito | INT | Sí |  |  |  |
| id_caja | INT | Sí |  |  |  |
| id_caja_cheque | INT | Sí |  |  |  |
| id_caja_tarjeta | INT | Sí |  |  |  |
| id_punto_venta | INT | Sí |  |  |  |
| id_punto_ventac | INT | Sí |  |  |  |
| password_temporal | VARCHAR | Sí |  |  |  |
| ruta_reporte_local | VARCHAR | Sí |  |  |  |
| utiliza_reporte_local | VARCHAR | Sí |  |  |  |
| vendedor_web | VARCHAR | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| tipo_busqueda_defecto | INT | Sí |  |  |  |
| resol_principal | VARCHAR | Sí |  |  |  |
| permiso_supervisor_venta | VARCHAR | Sí |  |  |  |
| entrega_defecto | VARCHAR | Sí |  |  |  |
| ruta_certificado_local | VARCHAR | Sí |  |  |  |
| utiliza_certificado_local | VARCHAR | Sí |  |  |  |
| zoom_reportes | INT | Sí |  |  |  |
| carpeta_documentos | VARCHAR | Sí |  |  |  |
| id_caja_cheque_deposito | INT | Sí |  |  |  |
| fuente_nombre | VARCHAR | Sí |  |  |  |
| fuente_tamano | DOUBLE | Sí |  |  |  |
| id_caja_deposito | INT | Sí |  |  |  |
| id_caja_tarjeta_deposito | INT | Sí |  |  |  |
| habilita_usuario | VARBINARY | Sí |  |  |  |
| tipo_boton | VARCHAR | Sí |  |  |  |
| color_formulario | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| correo_usr | usuarios | Crm_CargaLlamada.frm | 2569 | '        rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FR… |
| correo_usr | usuarios | Funciones.bas | 13143 | rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FROM correo… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Caja_Control_Sucursales.frm | 821 | JOIN | "LEFT JOIN usuarios ON usuarios.id_usuario = ca.id_usuario_c… |
| Caja_Control_Sucursales.frm | 847 | JOIN | "LEFT JOIN usuarios ON usuarios.id_usuario = ca.id_usuario_c… |
| Cliente.frm | 3207 | JOIN | "INNER JOIN usuarios ON usuarios.codviajante = viajantes.cod… |
| Info_Stock.frm | 11572 | JOIN | "INNER JOIN usuarios ON usuarios.codviajante = viajantes.cod… |
| Info_Stock.frm | 11727 | SELECT | data_usuario.RecordSource = "SELECT * FROM usuarios WHERE us… |
| Erp_Carga_Parte_Diario.frm | 4282 | SELECT | " FROM usuarios" & _ |
| Erp_Carga_Parte_Diario.frm | 4417 | SELECT | " FROM usuarios" & _ |
| CargaUsuario.frm | 1616 | SELECT | .Source = "select * from usuarios where usuarios.cod_usuario… |
| CargaUsuario.frm | 1626 | INSERT | '                conn.Execute "INSERT INTO `usuarios` (`cod_… |
| CargaUsuario.frm | 1633 | SELECT | rs_usuarios.Open "SELECT * from usuarios where id_usuario = … |
| CargaUsuario.frm | 1697 | UPDATE | conn.Execute "UPDATE usuarios SET password_usuario=AES_ENCRY… |
| CargaUsuario.frm | 1714 | SELECT | '                ABMUsuarios.DataUsuario.RecordSource = "sel… |
| CargaUsuario.frm | 1734 | SELECT | rs_usuarios.Open "SELECT * from usuarios where id_usuario = … |
| CargaUsuario.frm | 1797 | UPDATE | conn.Execute "UPDATE usuarios SET password_usuario=AES_ENCRY… |
| CargaUsuario.frm | 1806 | SELECT | '                ABMUsuarios.DataUsuario.RecordSource = "sel… |
| mensaj_carga.frm | 794 | SELECT | data_usuario.RecordSource = "SELECT * FROM usuarios ORDER BY… |
| Pedido_prep_consulta.frm | 1424 | SELECT | '    DataUsuario.RecordSource = "SELECT * FROM usuarios ORDE… |
| Pedido_prep_consulta.frm | 1445 | JOIN | '                                    "LEFT JOIN usuarios ON … |
| Pedido_prep_consulta.frm | 1453 | JOIN | ''                                    "LEFT JOIN usuarios ON… |
| Pedido_prep_consulta.frm | 1686 | JOIN | '                                    "LEFT JOIN usuarios ON … |
| Pedido_prep_consulta.frm | 1702 | JOIN | '                                        "LEFT JOIN usuarios… |
| Pedido_prep_consulta.frm | 1720 | JOIN | '                                            "LEFT JOIN usua… |
| Pedido_prep_consulta.frm | 1735 | JOIN | '                                    "LEFT JOIN usuarios ON … |
| Pedido_prep_consulta.frm | 1751 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = ped_prep.id_re… |
| Pedido_prep_consulta.frm | 1766 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = ped_prep.id_re… |
| CuentaCliente.frm | 1620 | SELECT | rs_usr.Open "SELECT usuarios.id_usuario,usuarios.cod_usuario… |
| CuentaCliente.frm | 1786 | SELECT | rs_usr.Open "SELECT usuarios.id_usuario,usuarios.cod_usuario… |
| CuentaCliente.frm | 1919 | SELECT | rs_usr.Open "SELECT usuarios.id_usuario,usuarios.cod_usuario… |
| CuentaCliente.frm | 2105 | SELECT | rs_usr.Open "SELECT usuarios.id_usuario,usuarios.cod_usuario… |
| CuentaCliente.frm | 2595 | SELECT | '        rs_usr.Open "SELECT usuarios.id_usuario,usuarios.co… |
| CuentaCliente.frm | 3154 | SELECT | rs_usr.Open "SELECT usuarios.id_usuario,usuarios.cod_usuario… |
| Logi_Gestion2.frm | 5313 | SELECT | data_usuario.RecordSource = "SELECT * From usuarios ORDER BY… |
| Logi_Gestion2.frm | 5353 | SELECT | DataGenerado.RecordSource = "SELECT * From usuarios ORDER BY… |
| Logi_Gestion2.frm | 6234 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion2.frm | 6352 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cuentacliente.… |
| Logi_Gestion2.frm | 6467 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion2.frm | 6497 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cuentacliente.… |
| Logi_Gestion2.frm | 6536 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion2.frm | 8022 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Logi_Gestion2.frm | 8127 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Logi_Gestion2.frm | 8231 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| CargaMovCaja.frm | 1538 | SELECT | data_usuario.RecordSource = "SELECT * FROM usuarios WHERE ba… |
| CargaMovCaja.frm | 1541 | SELECT | data_usuario.RecordSource = "SELECT * FROM usuarios where id… |
| CargaMovCaja.frm | 3027 | SELECT | "From usuarios " & _ |
| CargaMovCaja.frm | 3056 | SELECT | "From usuarios " & _ |
| CargaMovCaja.frm | 3083 | SELECT | "From usuarios " & _ |
| CargaMovCaja.frm | 3110 | SELECT | '"select * from usuarios where usuarios.cod_usuario = " & pr… |
| Visualiza_Pedido.frm | 10692 | SELECT | rs_usuario.Open "SELECT * FROM usuarios WHERE id_usuario = "… |
| Visualiza_Pedido.frm | 10917 | SELECT | rs_usuario.Open "SELECT * FROM usuarios WHERE id_usuario = "… |
| Visualiza_Pedido.frm | 11326 | SELECT | rs_usuarios.Open "SELECT * from usuarios where id_usuario = … |
| Logi_Gestion.frm | 6545 | SELECT | data_usuario.RecordSource = "SELECT * From usuarios ORDER BY… |
| Logi_Gestion.frm | 6585 | SELECT | DataGenerado.RecordSource = "SELECT * From usuarios ORDER BY… |
| Logi_Gestion.frm | 7580 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion.frm | 7722 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cuentacliente.… |
| Logi_Gestion.frm | 7860 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion.frm | 7882 | JOIN | '                    "LEFT JOIN usuarios ON (usuarios.id_usu… |
| Logi_Gestion.frm | 7912 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cuentacliente.… |
| Logi_Gestion.frm | 8015 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.IdUsu… |
| Logi_Gestion.frm | 9538 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Logi_Gestion.frm | 9559 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Logi_Gestion.frm | 9667 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Logi_Gestion.frm | 9774 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Configuracion2.frm | 5425 | SELECT | '                                     "From usuarios " & _ |
| Configuracion.frm | 5524 | SELECT | '                                     "From usuarios " & _ |
| Carga_DatosAdicionales.frm | 1612 | SELECT | rs_usuarios.Open "SELECT * from usuarios where id_usuario = … |
| Carga_DatosAdicionales.frm | 1636 | SELECT | data_usuario.RecordSource = "SELECT * FROM usuarios WHERE ba… |
| Carga_DatosAdicionales.frm | 2848 | JOIN | ''                  "LEFT JOIN usuarios ON (usuarios.id_usua… |
| En_Carga_UsuRef.frm | 824 | SELECT | data_usuario.RecordSource = "SELECT id_usuario,cod_usuario,n… |
| trz_trazabilidad.frm | 5255 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.idUsu… |
| trz_trazabilidad.frm | 5266 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = comp_ped.idUsu… |
| Stock_Control.frm | 2916 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = cliente_datos_… |
| Info_Venta_respaldo_bruno.frm | 9979 | JOIN | "INNER JOIN usuarios ON usuarios.codviajante = viajantes.cod… |
| Info_Venta_respaldo_bruno.frm | 10157 | SELECT | data_usuario.RecordSource = "SELECT id_usuario,cod_usuario,b… |
| Rprecios_log.frm | 590 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = reglas_precio_… |
| Rprecios_log.frm | 600 | JOIN | "LEFT JOIN usuarios ON (usuarios.id_usuario = reglas_precio_… |
| Rprecios_log.frm | 651 | JOIN | '                            "LEFT JOIN usuarios ON (usuario… |
| Info_Venta.frm | 10066 | JOIN | "INNER JOIN usuarios ON usuarios.codviajante = viajantes.cod… |
| Info_Venta.frm | 10245 | SELECT | data_usuario.RecordSource = "SELECT id_usuario,cod_usuario,b… |
| Info_Venta.frm | 10287 | SELECT | "From usuarios " & _ |
| IngresoUsuario.frm | 2086 | SELECT | .Source = "SELECT  * FROM usuarios WHERE baja_usuario = 'No'… |
| … | … | … | *(321 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)