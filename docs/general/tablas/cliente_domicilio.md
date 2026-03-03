# Tabla `cliente_domicilio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cliente_domicilio | DOUBLE | No | ✓ |  |  |
| Calle | VARCHAR | Sí |  |  |  |
| NroCalle | VARCHAR | Sí |  |  |  |
| Dpto | VARCHAR | Sí |  |  |  |
| IDDistrito | INT | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| diasContacto | VARCHAR | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| geo_latitud | VARCHAR | Sí |  |  |  |
| geo_longitud | VARCHAR | Sí |  |  |  |
| distancia_sucursal | DECIMAL | Sí |  |  |  |
| hora_desde | TIME | Sí |  |  |  |
| hora_hasta | TIME | Sí |  |  |  |
| periodicidad_visita_vendedor | VARCHAR | Sí |  |  |  |
| visita_vendedor_valor | VARCHAR | Sí |  |  |  |
| codpostal_ecom | VARCHAR | Sí |  |  |  |
| domicilio_ecom | VARCHAR | Sí |  |  |  |
| cod_provincia_ecom | VARCHAR | Sí |  |  |  |
| provincia_ecom | VARCHAR | Sí |  |  |  |
| cod_localidad_ecom | VARCHAR | Sí |  |  |  |
| localidad_ecom | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 1552 | JOIN | var_left = "LEFT JOIN cliente_domicilio ON (cliente_domicili… |
| Cliente.frm | 1595 | JOIN | var_left = " LEFT JOIN cliente_domicilio ON (cliente_domicil… |
| Cliente.frm | 1714 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 1739 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 1760 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 1774 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 1795 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 1808 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Cliente.frm | 2993 | SELECT | "From cliente_domicilio " & _ |
| Logi_Gestion2.frm | 8019 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion2.frm | 8124 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion2.frm | 8228 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Facturacion_Ciclica.frm | 2827 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Facturacion_Ciclica.frm | 2842 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Visualiza_Pedido.frm | 10724 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion.frm | 9534 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion.frm | 9556 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion.frm | 9663 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Logi_Gestion.frm | 9770 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Visualiza_CliDom.frm | 916 | SELECT | '                "From cliente_domicilio " & _ |
| Visualiza_CliDom.frm | 931 | SELECT | "From cliente_domicilio " & _ |
| Carga_DatosAdicionales.frm | 1680 | SELECT | "From cliente_domicilio " & _ |
| Carga_DatosAdicionales.frm | 1894 | SELECT | '                          "FROM cliente_domicilio " & _ |
| Carga_DatosAdicionales.frm | 1900 | SELECT | '                          "FROM cliente_domicilio " & _ |
| Carga_DatosAdicionales.frm | 2849 | JOIN | ''                  "LEFT JOIN cliente_domicilio ON (cliente… |
| Stock_Control.frm | 2912 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ListadoFacturas.frm | 905 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ListadoFacturas.frm | 1022 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_prep.frm | 4957 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_domicilio ON (client… |
| Remito.frm | 6189 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Remito.frm | 6532 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Facturacion.frm | 3204 | JOIN | var_left = "LEFT JOIN cliente_domicilio ON (cliente_domicili… |
| Facturacion.frm | 3493 | SELECT | "From cliente_domicilio " & _ |
| Facturacion.frm | 3881 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Facturacion.frm | 3896 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Facturacion.frm | 3916 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Facturacion.frm | 3930 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Facturacion.frm | 3950 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Facturacion.frm | 3965 | JOIN | '        "LEFT JOIN cliente_domicilio ON (cliente_domicilio.… |
| Pedido_Avanzado.frm | 4248 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 4520 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 4769 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 6729 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 9610 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 9937 | JOIN | '                            LosLeft = LosLeft & " LEFT JOIN… |
| Pedido_Avanzado.frm | 9939 | JOIN | LosLeft = " LEFT JOIN cliente_domicilio ON (cliente_domicili… |
| Pedido_Avanzado.frm | 9972 | JOIN | LosLeft = LosLeft & " LEFT JOIN cliente_domicilio ON (client… |
| Pedido_Avanzado.frm | 11065 | JOIN | '                                        "LEFT JOIN cliente_… |
| Pedido_Avanzado.frm | 11536 | JOIN | '                                    "LEFT JOIN cliente_domi… |
| Pedido_Avanzado.frm | 13082 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 13202 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Pedido_Avanzado.frm | 13348 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 14592 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 15186 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 16849 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 17799 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 26903 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 31936 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 32860 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ConsultaComprobante.frm | 35153 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| CargaComprobantesPed.frm | 1716 | JOIN | var_left = "LEFT JOIN cliente_domicilio ON (cliente_domicili… |
| Logi_OrdenRuta.frm | 955 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| ecom_datos_pedido.frm | 887 | JOIN | " LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_clien… |
| Carga_Cliente.frm | 4772 | SELECT | conn.Execute "DELETE FROM cliente_domicilio WHERE id_cliente… |
| Carga_Cliente.frm | 4772 | DELETE | conn.Execute "DELETE FROM cliente_domicilio WHERE id_cliente… |
| Carga_Cliente.frm | 5591 | SELECT | '            conn.Execute "delete from cliente_domicilio whe… |
| Carga_Cliente.frm | 5591 | DELETE | '            conn.Execute "delete from cliente_domicilio whe… |
| Carga_Cliente.frm | 5595 | INSERT | conn.Execute "INSERT INTO cliente_domicilio " & _ |
| Carga_Cliente.frm | 5937 | SELECT | '            conn.Execute "delete from cliente_domicilio whe… |
| Carga_Cliente.frm | 5937 | DELETE | '            conn.Execute "delete from cliente_domicilio whe… |
| Carga_Cliente.frm | 5940 | INSERT | '            conn.Execute "INSERT INTO cliente_domicilio " &… |
| Carga_Cliente.frm | 5964 | INSERT | '                        conn.Execute "INSERT INTO cliente_d… |
| Carga_Cliente.frm | 5969 | SELECT | rs_cliente_domicilio.Open "SELECT * FROM cliente_domicilio W… |
| Carga_Cliente.frm | 5993 | INSERT | '                        conn.Execute "INSERT INTO cliente_d… |
| Carga_Cliente.frm | 6001 | SELECT | rs_cliente_domicilio.Open "SELECT * FROM cliente_domicilio W… |
| Carga_Cliente.frm | 6025 | UPDATE | '                        conn.Execute "UPDATE cliente_domici… |
| Carga_Cliente.frm | 6032 | UPDATE | '                        conn.Execute "UPDATE cliente_domici… |
| Lista_Comp_Gral.frm | 2866 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Lista_Comp_Gral.frm | 3424 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| Lista_Comp_Gral.frm | 3813 | JOIN | "LEFT JOIN cliente_domicilio ON (cliente_domicilio.id_client… |
| … | … | … | *(55 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)