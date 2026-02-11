# Tabla `cliente_contacto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cliente_contacto | DOUBLE | No | ✓ |  |  |
| nombre_cliente_contacto | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| nro_doc | VARCHAR | Sí |  |  |  |
| TelefonoContacto | VARCHAR | Sí |  |  |  |
| CelularContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| diasContacto | VARCHAR | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| whatsapp | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 1562 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Cliente.frm | 3013 | SELECT | "From cliente_contacto " & _ |
| Logi_Gestion2.frm | 8018 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion2.frm | 8123 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion2.frm | 8227 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Visualiza_Pedido.frm | 10723 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion.frm | 9533 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion.frm | 9555 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion.frm | 9662 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Logi_Gestion.frm | 9769 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Visualiza_CliDom.frm | 941 | SELECT | DataContactos.RecordSource = "SELECT * FROM cliente_contacto… |
| Correo_SeleccionE.frm | 557 | SELECT | "FROM cliente_contacto " & _ |
| Carga_DatosAdicionales.frm | 1741 | SELECT | DataContacto.RecordSource = "SELECT * From cliente_contacto … |
| Carga_DatosAdicionales.frm | 2850 | JOIN | ''                  "LEFT JOIN cliente_contacto ON (cliente_… |
| Stock_Control.frm | 2911 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Crm_CargaLlamada.frm | 2580 | JOIN | '        " LEFT JOIN cliente_contacto ON (cliente_contacto.i… |
| ListadoFacturas.frm | 904 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ListadoFacturas.frm | 1021 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Remito.frm | 6188 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Remito.frm | 6531 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Facturacion.frm | 3214 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Facturacion.frm | 3512 | SELECT | "From cliente_contacto " & _ |
| Facturacion.frm | 3882 | JOIN | '        "LEFT JOIN cliente_contacto ON (cliente_contacto.id… |
| Pedido_Avanzado.frm | 4247 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 4519 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 4768 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 6728 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 9609 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 9979 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_contacto ON (cliente… |
| Pedido_Avanzado.frm | 11064 | JOIN | '                                        "LEFT JOIN cliente_… |
| Pedido_Avanzado.frm | 11535 | JOIN | '                                    "LEFT JOIN cliente_cont… |
| Pedido_Avanzado.frm | 13081 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 13201 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Pedido_Avanzado.frm | 13347 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 14591 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 15185 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 16848 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 17798 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 26902 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 31935 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 32859 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| ConsultaComprobante.frm | 35152 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| CargaComprobantesPed.frm | 1726 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Logi_OrdenRuta.frm | 954 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Carga_Cliente.frm | 4666 | SELECT | conn.Execute "DELETE FROM cliente_contacto WHERE id_cliente_… |
| Carga_Cliente.frm | 4666 | DELETE | conn.Execute "DELETE FROM cliente_contacto WHERE id_cliente_… |
| Carga_Cliente.frm | 5605 | INSERT | conn.Execute "INSERT INTO cliente_contacto " & _ |
| Carga_Cliente.frm | 6061 | SELECT | '            conn.Execute "delete from cliente_contacto wher… |
| Carga_Cliente.frm | 6061 | DELETE | '            conn.Execute "delete from cliente_contacto wher… |
| Carga_Cliente.frm | 6064 | INSERT | '            conn.Execute "INSERT INTO cliente_contacto " & … |
| Carga_Cliente.frm | 6082 | INSERT | conn.Execute "INSERT INTO cliente_contacto " & _ |
| Carga_Cliente.frm | 6087 | UPDATE | conn.Execute "UPDATE cliente_contacto " & _ |
| Lista_Comp_Gral.frm | 2865 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 3423 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 3812 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 5397 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 5868 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 6429 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 9129 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 9588 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 10037 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 11101 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 11473 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 12405 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 12761 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Gral.frm | 13128 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 5423 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 6126 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 6717 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 7714 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 8323 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 9024 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Lista_Comp_Fact.frm | 9639 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Geolocalizacion_Comprobante.frm | 2248 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Geolocalizacion_Comprobante.frm | 2619 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_contacto ON (cliente… |
| CargaComprobantesC.frm | 4146 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Geolocalizacion_Cliente.frm | 1998 | JOIN | var_left = var_left & "LEFT JOIN cliente_contacto ON (client… |
| Geolocalizacion_Cliente.frm | 2393 | JOIN | '            LosLeft = LosLeft & " LEFT JOIN cliente_contact… |
| Principal.frm | 9825 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| Principal.frm | 10537 | JOIN | "LEFT JOIN cliente_contacto ON (cliente_contacto.id_cliente_… |
| … | … | … | *(21 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)