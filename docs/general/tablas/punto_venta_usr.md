# Tabla `punto_venta_usr`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_punto_venta_usr | INT | No | ✓ |  |  |
| id_pv | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| AsigUsrPv.frm | 653 | SELECT | rs_exist.Open "SELECT * FROM punto_venta_usr WHERE id_pv = "… |
| AsigUsrPv.frm | 712 | SELECT | conn.Execute "DELETE FROM punto_venta_usr WHERE id_punto_ven… |
| AsigUsrPv.frm | 712 | DELETE | conn.Execute "DELETE FROM punto_venta_usr WHERE id_punto_ven… |
| AsigUsrPv.frm | 759 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| AsigUsrPv.frm | 887 | SELECT | conn.Execute "DELETE FROM punto_venta_usr WHERE id_usuario =… |
| AsigUsrPv.frm | 887 | DELETE | conn.Execute "DELETE FROM punto_venta_usr WHERE id_usuario =… |
| AsigUsrPv.frm | 898 | INSERT | conn.Execute "INSERT INTO punto_venta_usr (id_pv, id_usuario… |
| CargaUsuario.frm | 1702 | INSERT | conn.Execute "INSERT INTO punto_venta_usr (id_pv,id_usuario)… |
| CargaUsuario.frm | 1748 | SELECT | '                rs_exist.Open "SELECT * FROM punto_venta_us… |
| CargaUsuario.frm | 1752 | UPDATE | '                    conn.Execute "UPDATE punto_venta_usr SE… |
| NotaCredCon.frm | 5840 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| FacturaB_COPIA.frm | 8572 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCredDesc.frm | 1389 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCred_COPIA.frm | 6894 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| TPV.frm | 12772 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Impositivo.frm | 2327 | JOIN | '                            "LEFT JOIN  punto_venta_usr ON … |
| Info_Impositivo.frm | 2371 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Impositivo.frm | 2659 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Proceso_Fiscal.frm | 1691 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion2.frm | 5468 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion2.frm | 8529 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion2.frm | 8880 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion2.frm | 9239 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| CargaMovCaja.frm | 1399 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Facturacion_Ciclica.frm | 3135 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Facturacion_Ciclica.frm | 3529 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion.frm | 6725 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion.frm | 10076 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion.frm | 10460 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Logi_Gestion.frm | 10894 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| OrdenPago.frm | 10395 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| OrdenPago.frm | 10420 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Venta_respaldo_bruno.frm | 10075 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Venta_respaldo_bruno.frm | 12171 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Venta.frm | 10163 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Venta.frm | 12666 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| FacturaB.frm | 13732 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCred_SinCompO.frm | 8522 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| FacturaA.frm | 9255 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCred_Importe.frm | 5391 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Conta_Info.frm | 1686 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Seleccion_PV.frm | 248 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCredCopia.frm | 7505 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Remito.frm | 8313 | JOIN | '                            "LEFT JOIN  punto_venta_usr ON … |
| Remito.frm | 8550 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 4198 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 4474 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 4708 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 6654 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 7554 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 8181 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 8706 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Pedido_Avanzado.frm | 9530 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| ConsultaComprobante.frm | 4173 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| ConsultaComprobante.frm | 4187 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Caja.frm | 1964 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaDeb.frm | 6115 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| ABM_Filtros.frm | 566 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| CargaUsuario_Copia.frm | 504 | INSERT | '                 conn.Execute "INSERT INTO punto_venta_usr … |
| CargaUsuario_Copia.frm | 506 | INSERT | conn.Execute "INSERT INTO punto_venta_usr (id_pv,id_usuario)… |
| CargaUsuario_Copia.frm | 507 | SELECT | " SELECT id_pv, '" & id_usr & "' FROM punto_venta_usr WHERE … |
| Info_RepRapidos.frm | 957 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Info_Cobranza.frm | 5689 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaCred.frm | 7811 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| NotaDebCopia.frm | 5951 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 2800 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 2958 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 6095 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 6686 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 7635 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 8985 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Lista_Comp_Fact.frm | 9600 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| ReciboCobro.frm | 9732 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| CM_Filtros.frm | 541 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| InicSaldos.frm | 2343 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| InicSaldos.frm | 2383 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| InicSaldos.frm | 2408 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| Visualiza_NotaCredCon.frm | 5330 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| TPV_2.frm | 12147 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| adm_felectronicas.frm | 1354 | JOIN | "LEFT JOIN  punto_venta_usr ON (punto_venta_usr.id_pv =punto… |
| … | … | … | *(1 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)