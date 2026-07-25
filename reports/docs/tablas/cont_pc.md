# Tabla `cont_pc`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pc | DOUBLE | No | ✓ |  |  |
| cod_pc | VARCHAR | Sí |  |  |  |
| descrip_pc | VARCHAR | Sí |  |  |  |
| codjer_pc | VARCHAR | Sí |  |  |  |
| tipo_cuenta_pc | VARCHAR | Sí |  |  |  |
| imp_cont_pc | VARCHAR | Sí |  |  |  |
| saldo_pc | VARCHAR | Sí |  |  |  |
| id_padre_pc | DOUBLE | Sí |  |  |  |
| nivel1_pc | VARCHAR | Sí |  |  |  |
| nivel2_pc | VARCHAR | Sí |  |  |  |
| nivel3_pc | VARCHAR | Sí |  |  |  |
| nivel4_pc | VARCHAR | Sí |  |  |  |
| nivel5_pc | VARCHAR | Sí |  |  |  |
| nivel6_pc | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| ajuste_infla_pc | VARCHAR | Sí |  |  |  |
| moneda_pc | VARCHAR | Sí |  |  |  |
| asig_cc | VARCHAR | Sí |  |  |  |
| id_indiceinfla | DOUBLE | Sí |  |  |  |
| id_nivel1 | DOUBLE | Sí |  |  |  |
| id_nivel2 | DOUBLE | Sí |  |  |  |
| id_nivel3 | DOUBLE | Sí |  |  |  |
| id_nivel4 | DOUBLE | Sí |  |  |  |
| id_nivel5 | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| cont_cc | cont_pc | Cont_CentroCosto.frm | 679 | DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont_pc.descrip_pc, S… |
| cont_cc | cont_pc | Cont_ListaCtaCont.frm | 1253 | 'rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_c… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 2209 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 3210 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Visualiza_Cont_CargaAsientoM.frm | 3313 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 2718 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 3756 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaAsientoM.frm | 3859 | rs_cc.Open "SELECT * FROM cont_cc INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc… |
| cont_cc | cont_pc | Cont_CargaCentroCosto.frm | 640 | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont… |
| cont_cc | cont_pc | Cont_CargaCentroCosto.frm | 714 | Cont_CentroCosto.DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, cont… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 2967 | SELECT | rs_cta.Open "SELECT cont_pc.*, SUBSTRING_INDEX(cont_pc.codje… |
| ABMTarjetaC.frm | 413 | SELECT | rs_cta.Open "SELECT cont_pc.*, SUBSTRING_INDEX(cont_pc.codje… |
| CargaBDeposito.frm | 2650 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| CargaBDeposito.frm | 2918 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| PNotaCred.frm | 7035 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| PNotaCred.frm | 7437 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| Visualiza_ReciboCobro.frm | 15473 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_ReciboCobro.frm | 15800 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| Visualiza_NotaCred.frm | 5632 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_NotaCred.frm | 5988 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| Cont_CentroCosto.frm | 570 | JOIN | "INNER JOIN cont_pc on (cont_pc.id_pc = cont_cc.id_pc) WHERE… |
| Cont_CentroCosto.frm | 679 | JOIN | DataListaCC.RecordSource = "SELECT DISTINCT cont_cc.id_pc, c… |
| Cont_CargaPlanCta.frm | 604 | SELECT | rs_NomCta.Open "SELECT * FROM cont_pc WHERE descrip_pc = '" … |
| Cont_CargaPlanCta.frm | 620 | SELECT | rs_PregCodjer.Open "Select * from cont_pc where codjer_pc = … |
| Cont_CargaPlanCta.frm | 649 | SELECT | rs_codmanual.Open "Select * from cont_pc where cod_pc = " & … |
| Cont_CargaPlanCta.frm | 665 | SELECT | rs_padreanul.Open "Select * from cont_pc where id_pc = " & C… |
| Cont_CargaPlanCta.frm | 683 | SELECT | rs_NuevoNodo.Open "select * from cont_pc", conn, adOpenDynam… |
| Cont_CargaPlanCta.frm | 845 | SELECT | rs_mod.Open "SELECT * FROM cont_pc WHERE id_pc = " & id_pc &… |
| Cont_CargaPlanCta.frm | 863 | SELECT | rs_NomCta.Open "SELECT * FROM cont_pc WHERE descrip_pc = '" … |
| Cont_CargaPlanCta.frm | 888 | SELECT | rs_PregCodjer.Open "Select * from cont_pc where codjer_pc = … |
| Cont_CargaPlanCta.frm | 947 | SELECT | rs_codmanual.Open "Select * from cont_pc where cod_pc = " & … |
| Cont_CargaPlanCta.frm | 983 | SELECT | rs_anul.Open "Select * from cont_pc where id_padre_pc = " & … |
| Cont_CargaPlanCta.frm | 1185 | SELECT | rs.Open "Select * from cont_pc where id_pc = " & id_pc & " "… |
| Cont_CargaPlanCta.frm | 1405 | SELECT | rs_TipoCta.Open "SELECT tipo_cuenta_pc from cont_pc where id… |
| Cont_CargaPlanCta.frm | 1565 | SELECT | rs.Open "SELECT * from cont_pc order by codjer_pc", conn, ad… |
| Cont_CargaPlanCta.frm | 1579 | SELECT | rs_nombrepadre.Open "Select descrip_pc from cont_pc where id… |
| Cont_CargaPlanCta.frm | 1940 | SELECT | rs_NuevoNod.Open "SELECT * from cont_pc where id_pc = " & id… |
| Cont_CargaPlanCta.frm | 1981 | UPDATE | conn.Execute "UPDATE cont_pc SET id_nivel2 = 0 WHERE id_pc =… |
| Cont_CargaPlanCta.frm | 2015 | UPDATE | conn.Execute "UPDATE cont_pc SET id_nivel3 = 0 WHERE id_pc =… |
| Cont_CargaPlanCta.frm | 2061 | UPDATE | conn.Execute "UPDATE cont_pc SET id_nivel4 = 0 WHERE id_pc =… |
| Cont_CargaPlanCta.frm | 2119 | UPDATE | conn.Execute "UPDATE cont_pc SET id_nivel5 = 0 WHERE id_pc =… |
| Cont_CargaPlanCta.frm | 2189 | UPDATE | conn.Execute "UPDATE cont_pc SET id_nivel6 = 0 WHERE id_pc =… |
| Visualiza_CargaMovStock.frm | 5413 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_CargaMovStock.frm | 5685 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| NotaCredCon.frm | 7377 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| NotaCredCon.frm | 7662 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| Visualiza_PNotaDeb.frm | 3892 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_PNotaDeb.frm | 4170 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| FacturaB_COPIA.frm | 12126 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| FacturaB_COPIA.frm | 12535 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| FacturaB_COPIA.frm | 16285 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| NotaCredDesc.frm | 4460 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| NotaCredDesc.frm | 4734 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| NotaCred_COPIA.frm | 8860 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| NotaCred_COPIA.frm | 9221 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| NotaCred_COPIA.frm | 11881 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_TPV.frm | 9251 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_TPV.frm | 10306 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| ChequeTercero.frm | 2957 | SELECT | rs_cta.Open "SELECT * from cont_pc where id_pc = " & rs_anul… |
| Cont_CargaPerido.frm | 510 | SELECT | rs_plancta.Open "SELECT * from cont_pc where imp_cont_pc = '… |
| TPV.frm | 19353 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| TPV.frm | 20676 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| TPV.frm | 25030 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| TPV.frm | 25728 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Cont_ProcAsientosM.frm | 1454 | JOIN | "LEFT JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) "… |
| Cont_ProcAsientosM.frm | 2089 | SELECT | rs_cta.Open "SELECT * from cont_pc where id_pc = " & rs_anul… |
| Visualiza_NotaCredDesc.frm | 2237 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_NotaCredDesc.frm | 2511 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| CuentaCliente.frm | 3661 | SELECT | rs_cta.Open "SELECT * from cont_pc where id_pc = " & rs_anul… |
| CargaMovCaja.frm | 4506 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| CargaMovCaja.frm | 4772 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| OrdenPago.frm | 14694 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| OrdenPago.frm | 14991 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| Cont_PlanCta.frm | 431 | SELECT | 'rs.Open "SELECT * from cont_pc", conn, adOpenDynamic, adLoc… |
| Cont_PlanCta.frm | 432 | SELECT | rs.Open "SELECT * from cont_pc order by codjer_pc", conn, ad… |
| Cont_PlanCta.frm | 448 | SELECT | rs_nombrepadre.Open "Select descrip_pc from cont_pc where id… |
| Cont_PlanCta.frm | 651 | SELECT | rs_NodoPorDefecto.Open "select * from cont_pc", conn, adOpen… |
| Cont_PlanCta.frm | 785 | SELECT | rs_BuscContenedora.Open "select * from cont_pc where id_pc= … |
| Cont_PlanCta.frm | 1097 | SELECT | rs_DatosCta.Open "select * from cont_pc where id_pc = " & SS… |
| Cont_PlanCta.frm | 1266 | SELECT | "FROM cont_pc " & _ |
| Cont_PlanCta.frm | 1273 | SELECT | "FROM cont_pc " & _ |
| Cont_PlanCta.frm | 1301 | SELECT | rs_elimina.Open "SELECT * from cont_pc where id_padre_pc = "… |
| Cont_PlanCta.frm | 1306 | SELECT | conn.Execute "DELETE FROM cont_pc WHERE id_pc = " & SSTree.S… |
| Cont_PlanCta.frm | 1306 | DELETE | conn.Execute "DELETE FROM cont_pc WHERE id_pc = " & SSTree.S… |
| Cont_PlanCta.frm | 1368 | SELECT | rs.Open "SELECT * from cont_pc order by codjer_pc", conn, ad… |
| Cont_PlanCta.frm | 1382 | SELECT | rs_nombrepadre.Open "Select descrip_pc from cont_pc where id… |
| Imp_Carga.frm | 1131 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_PNotaCred_Importe.frm | 3806 | SELECT | rs_InfoCta.Open "SELECT * from cont_pc where id_pc = " & Mat… |
| Visualiza_PNotaCred_Importe.frm | 4194 | JOIN | "INNER JOIN cont_pc ON (cont_pc.id_pc = cont_asiento.id_pc) … |
| ABMArticulo_seleccion.frm | 5253 | SELECT | rs_cta.Open "SELECT cont_pc.*, SUBSTRING_INDEX(cont_pc.codje… |
| … | … | … | *(237 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)