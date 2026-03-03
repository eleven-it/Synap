# Tabla `erp_zona`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_zona | INT | No | ✓ |  |  |
| id_pais | INT | Sí |  |  |  |
| codprovincia | INT | Sí |  |  |  |
| nombre_zona | VARCHAR | Sí |  |  |  |
| factura | VARCHAR | Sí |  |  |  |
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
| Cliente.frm | 1572 | JOIN | '    var_left = var_left & " LEFT JOIN erp_zona ON (erp_zona… |
| Cliente.frm | 1579 | JOIN | var_left = var_left & " LEFT JOIN erp_zona ON (erp_zona.id_z… |
| Cliente.frm | 1596 | JOIN | var_left = var_left & " LEFT JOIN erp_zona ON (erp_zona.id_z… |
| Cliente.frm | 3194 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| Logi_ABMRuta.frm | 534 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = logi_ruta_zona.id… |
| Logi_ABMRuta.frm | 764 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = logi_hoja_ruta.id… |
| Logi_ABMRuta.frm | 784 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = logi_hoja_ruta.id… |
| Stock_Control_Entrada.frm | 663 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Visualiza_ReciboCobro.frm | 9688 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Erp_Carga_Parte_Diario.frm | 3889 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| Visualiza_CargaMovStock.frm | 4349 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| NotaCredCon.frm | 6100 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| FacturaB_COPIA.frm | 12409 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| NotaCredDesc.frm | 3806 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| ABM_Sucursal_Envio.frm | 439 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = sucursales_envios… |
| Visualiza_NotaCredDesc.frm | 1776 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Logi_Gestion2.frm | 4830 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion2.frm | 4851 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion2.frm | 5342 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona From e… |
| Logi_Gestion2.frm | 5403 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion2.frm | 6175 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Logi_Gestion2.frm | 6284 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Logi_Gestion2.frm | 6409 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Facturacion_Ciclica.frm | 2001 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona From e… |
| Facturacion_Ciclica.frm | 2793 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Visualiza_Pedido.frm | 6158 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Visualiza_Pedido.frm | 6954 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Logi_Info.frm | 1323 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion.frm | 6057 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion.frm | 6082 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion.frm | 6574 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona From e… |
| Logi_Gestion.frm | 6642 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Logi_Gestion.frm | 6669 | JOIN | '                            "LEFT JOIN erp_zona as b ON (b.… |
| Logi_Gestion.frm | 7500 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Logi_Gestion.frm | 7631 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Logi_Gestion.frm | 7779 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Carga_DatosAdicionales.frm | 1543 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Carga_DatosAdicionales.frm | 1684 | JOIN | "LEFT OUTER JOIN erp_zona ON (erp_zona.id_zona = cliente_dom… |
| Erp_Carga_Zona.frm | 384 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE nombre_zona = '"… |
| Erp_Carga_Zona.frm | 400 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE  id_zona = 0", c… |
| Erp_Carga_Zona.frm | 421 | SELECT | Erp_ABM_Zonas.DataZonas.RecordSource = "SELECT * FROM erp_zo… |
| Erp_Carga_Zona.frm | 433 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE id_zona = " & Er… |
| Erp_Carga_Zona.frm | 453 | SELECT | Erp_ABM_Zonas.DataZonas.RecordSource = "SELECT * FROM erp_zo… |
| Stock_Control.frm | 1649 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Visualiza_FB_Copia.frm | 7585 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Info_Venta_respaldo_bruno.frm | 10087 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| CargaZona.frm | 384 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE nombre_zona = '"… |
| CargaZona.frm | 400 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE  id_zona = 0", c… |
| CargaZona.frm | 421 | SELECT | ABMZona.DataZonas.RecordSource = "SELECT * FROM erp_zona  OR… |
| CargaZona.frm | 433 | SELECT | rs_zonas.Open "SELECT * FROM erp_zona WHERE id_zona = " & AB… |
| CargaZona.frm | 453 | SELECT | ABMZona.DataZonas.RecordSource = "SELECT * FROM erp_zona ORD… |
| Info_Venta.frm | 10175 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| FacturaB.frm | 18249 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Crm_CargaCliPot.frm | 2164 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| En_Carga_Precio_Zona_Temporada.frm | 1252 | SELECT | consulta = "SELECT * FROM erp_zona ORDER BY nombre_zona" |
| FacturaA.frm | 14302 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Visualiza_NotaDeb.frm | 3092 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| En_GeneraOE.frm | 2462 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| NotaCred_Importe.frm | 5646 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Exportacion.frm | 3680 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = cliente.id_zona) … |
| Exportacion.frm | 3892 | SELECT | rs_zona.Open "SELECT * FROM erp_zona " & _ |
| Exportacion.frm | 4106 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = cliente.id_zona) … |
| Pedido_prep.frm | 4036 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| Pedido_prep.frm | 4108 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Pedido_prep.frm | 4952 | JOIN | '                            LosLeft = LosLeft & " LEFT JOIN… |
| Pedido_prep.frm | 4958 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Pedido_prep.frm | 5021 | JOIN | "LEFT JOIN erp_zona ON (erp_zona.id_zona = cliente.id_zona) … |
| Visualiza_FA.frm | 7429 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Logi_CargaRuta.frm | 1741 | SELECT | "From erp_zona " & _ |
| Logi_CargaRuta.frm | 1774 | SELECT | "From erp_zona " & _ |
| Logi_CargaRuta.frm | 1863 | SELECT | "From erp_zona " & _ |
| Logi_CargaRuta.frm | 1894 | SELECT | "From erp_zona " & _ |
| Logi_CargaRuta.frm | 1957 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| Remito.frm | 8104 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Carga_ClienteDomicilio.frm | 1696 | SELECT | dataZonaDomicilio.RecordSource = "SELECT id_zona,nombre_zona… |
| Visualiza_NotaCred_Importe.frm | 2381 | JOIN | "LEFT JOIN erp_zona ON erp_zona.id_zona = erp_proyecto.id_zo… |
| Pedido_Avanzado.frm | 3397 | SELECT | Data_Zonas.RecordSource = "SELECT id_zona,nombre_zona FROM e… |
| Pedido_Avanzado.frm | 3465 | JOIN | "LEFT JOIN erp_zona as b ON (b.id_zona = logi_ruta_zona.id_z… |
| Pedido_Avanzado.frm | 9917 | JOIN | LosLeft = LosLeft & " LEFT JOIN erp_zona ON (erp_zona.id_zon… |
| Pedido_Avanzado.frm | 9931 | JOIN | '                            LosLeft = LosLeft & " LEFT JOIN… |
| … | … | … | *(91 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 3033 | JOIN | LEFT JOIN erp_zona z ON z.id_zona = cl.id_zona AND (z.anulad… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)