# Tabla `erp_proyecto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_proyecto | INT | No | ✓ |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| fecha_alta_proyecto | DATE | Sí |  |  |  |
| tipo_proyecto | VARCHAR | Sí |  |  |  |
| nombre_proyecto | VARCHAR | Sí |  |  |  |
| nro_proyecto | DOUBLE | Sí |  |  |  |
| estado_proyecto | VARCHAR | Sí |  |  |  |
| codsucursal | INT | Sí |  |  |  |
| descripcion_proyecto | TEXT | Sí |  |  |  |
| fecha_inicio_proyecto | DATE | Sí |  |  |  |
| fecha_fin_proyecto | DATE | Sí |  |  |  |
| duracion_proyecto | INT | Sí |  |  |  |
| ganancia_neta_proyecto | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| jornada_proyecto | INT | Sí |  |  |  |
| contrato_proyecto | VARCHAR | Sí |  |  |  |

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
| PNotaCred.frm | 4627 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_ReciboCobro.frm | 9104 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_ReciboCobro.frm | 9687 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| Visualiza_NotaCred.frm | 3952 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Erp_Carga_Parte_Diario.frm | 2485 | UPDATE | conn.Execute "UPDATE erp_proyecto SET estado_proyecto='En Cu… |
| Erp_Carga_Parte_Diario.frm | 2574 | SELECT | rs_informe.Open " SELECT py.contrato_proyecto, py.nombre_pro… |
| Erp_Carga_Parte_Diario.frm | 2749 | SELECT | '                          rs_informe.Open " SELECT py.contr… |
| Erp_Carga_Parte_Diario.frm | 3911 | SELECT | " FROM erp_proyecto" & _ |
| Visualiza_CargaMovStock.frm | 2766 | SELECT | '    rs_proyecto.Open "SELECT * FROM erp_proyecto where id_p… |
| Visualiza_CargaMovStock.frm | 4348 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| NotaCredCon.frm | 5869 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| NotaCredCon.frm | 6099 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| Visualiza_PNotaDeb.frm | 2184 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaB_COPIA.frm | 8677 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaB_COPIA.frm | 12408 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| NotaCredDesc.frm | 1435 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| NotaCredDesc.frm | 3805 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| NotaCred_COPIA.frm | 6920 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_NotaCredDesc.frm | 1563 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_NotaCredDesc.frm | 1775 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| CuentaCliente.frm | 1590 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| CuentaCliente.frm | 1758 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| CuentaCliente.frm | 1889 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| CuentaCliente.frm | 2077 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| CuentaCliente.frm | 2569 | SELECT | '            rs_proyecto.Open "SELECT * FROM erp_proyecto wh… |
| Logi_Gestion2.frm | 7866 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto WHERE id_proyec… |
| Logi_Gestion2.frm | 8634 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Logi_Gestion2.frm | 8979 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Logi_Gestion2.frm | 9262 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| CargaMovCaja.frm | 1661 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Facturacion_Ciclica.frm | 3283 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Facturacion_Ciclica.frm | 3669 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_Pedido.frm | 6157 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| Visualiza_Pedido.frm | 6484 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_Pedido.frm | 6953 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| Visualiza_Pedido.frm | 10803 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Logi_Gestion.frm | 9385 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto WHERE id_proyec… |
| Logi_Gestion.frm | 10216 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Logi_Gestion.frm | 10595 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Logi_Gestion.frm | 10917 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| OrdenPago.frm | 9982 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| OrdenPago.frm | 15502 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| OrdenPago.frm | 15694 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_PNotaCred_Importe.frm | 1944 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 4095 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 4534 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 4711 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 5021 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 5176 | SELECT | '            rs_proyecto.Open "SELECT * FROM erp_proyecto wh… |
| trz_trazabilidad.frm | 5535 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 5854 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 6188 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 6335 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 6458 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| trz_trazabilidad.frm | 7748 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| ABMArticulo_seleccion.frm | 5287 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.nombre_proyecto,erp_pr… |
| Visualiza_POrden_Compra.frm | 5396 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_FB_Copia.frm | 4809 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_FB_Copia.frm | 7584 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| POrden_CompraCopia.frm | 4910 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| PRemito.frm | 5555 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_PNotaCredDev.frm | 3698 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_PNotaCredDesc.frm | 1661 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaB.frm | 13802 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaB.frm | 18248 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| NotaCred_SinCompO.frm | 8548 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaA.frm | 9370 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| FacturaA.frm | 14301 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| Visualiza_NotaDeb.frm | 2960 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_NotaDeb.frm | 3091 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| PNotaDebCopia.frm | 2433 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| En_GeneraOE.frm | 2291 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| En_GeneraOE.frm | 2461 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| En_GeneraOE.frm | 4833 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| En_GeneraOE.frm | 4976 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| stock_consulta_avanzada.frm | 4204 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.nombre_proyecto,erp_pr… |
| NotaCred_Importe.frm | 5420 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| NotaCred_Importe.frm | 5645 | SELECT | rs_proyecto.Open "SELECT erp_proyecto.*,erp_zona.nombre_zona… |
| En_GestionOE.frm | 1855 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| Visualiza_FA.frm | 4477 | SELECT | rs_proyecto.Open "SELECT * FROM erp_proyecto where id_proyec… |
| … | … | … | *(193 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)