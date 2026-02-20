# Tabla `cont_paramatriz`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_paramatriz | DOUBLE | No | ✓ |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| descrip_pc | VARCHAR | Sí |  |  |  |
| codjer_pc | VARCHAR | Sí |  |  |  |
| label_paramatriz | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 2909 | SELECT | rs_ctaDefault.Open "SELECT * from cont_paramatriz where id_p… |
| ABMTarjetaC.frm | 526 | SELECT | rs_ctaDefault.Open "SELECT * from cont_paramatriz where id_p… |
| CargaBDeposito.frm | 2292 | SELECT | 'rs_AsientoCtas.Open "SELECT * from cont_paramatriz where id… |
| CargaBDeposito.frm | 2349 | SELECT | rs_bancoMAT.Open "SELECT * from cont_paramatriz where id_par… |
| CargaBDeposito.frm | 2391 | SELECT | rs_CajaMat.Open "SELECT * from cont_paramatriz where id_para… |
| CargaBDeposito.frm | 2435 | SELECT | rs_bancoMAT.Open "SELECT * from cont_paramatriz where id_par… |
| CargaBDeposito.frm | 2477 | SELECT | rs_ValDepo.Open "SELECT * from cont_paramatriz where id_para… |
| PNotaCred.frm | 6139 | SELECT | 'rs_AsientoCtas.Open "SELECT * from cont_paramatriz where id… |
| PNotaCred.frm | 6185 | SELECT | '        rs_merc.Open "SELECT * from cont_paramatriz where i… |
| PNotaCred.frm | 6297 | SELECT | rs_dscto.Open "SELECT * from cont_paramatriz where id_parama… |
| PNotaCred.frm | 6322 | SELECT | rs_iva1.Open "SELECT id_pc from cont_paramatriz where id_par… |
| PNotaCred.frm | 6324 | SELECT | rs_iva2.Open "SELECT id_pc from cont_paramatriz where id_par… |
| PNotaCred.frm | 6326 | SELECT | rs_iva3.Open "SELECT id_pc from cont_paramatriz where id_par… |
| PNotaCred.frm | 6328 | SELECT | rs_ivaAdic.Open "SELECT id_pc from cont_paramatriz where id_… |
| PNotaCred.frm | 6463 | SELECT | rs_ImpInt.Open "SELECT * from cont_paramatriz where id_param… |
| PNotaCred.frm | 6494 | SELECT | rs_PercepIva.Open "SELECT * from cont_paramatriz where id_pa… |
| PNotaCred.frm | 6525 | SELECT | rs_PercepGan.Open "SELECT * from cont_paramatriz where id_pa… |
| PNotaCred.frm | 6590 | SELECT | '        rs_PercepIB1.Open "SELECT * from cont_paramatriz wh… |
| PNotaCred.frm | 6592 | SELECT | '        rs_PercepIB2.Open "SELECT * from cont_paramatriz wh… |
| PNotaCred.frm | 6689 | SELECT | rs_OtrosImp.Open "SELECT * from cont_paramatriz where id_par… |
| PNotaCred.frm | 6790 | SELECT | rs_vta.Open "SELECT * from cont_paramatriz where id_paramatr… |
| Visualiza_ReciboCobro.frm | 13480 | SELECT | rs_cheq.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_ReciboCobro.frm | 13527 | SELECT | rs_trans.Open "SELECT * from cont_paramatriz where id_parama… |
| Visualiza_ReciboCobro.frm | 13624 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 13789 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 13951 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 14153 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 14311 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 14483 | SELECT | rs_cheq.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_ReciboCobro.frm | 14530 | SELECT | rs_trans.Open "SELECT * from cont_paramatriz where id_parama… |
| Visualiza_ReciboCobro.frm | 14627 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 14792 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 14954 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 15120 | SELECT | rs_retMat.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_ReciboCobro.frm | 15218 | SELECT | '        rs_iva1.Open "SELECT * from cont_paramatriz where i… |
| Visualiza_ReciboCobro.frm | 15220 | SELECT | '        rs_iva2.Open "SELECT * from cont_paramatriz where i… |
| Visualiza_ReciboCobro.frm | 15317 | SELECT | '            rs_dscto.Open "SELECT * from cont_paramatriz wh… |
| Visualiza_NotaCred.frm | 5175 | SELECT | rs_vta.Open "SELECT * from cont_paramatriz where id_paramatr… |
| Visualiza_NotaCred.frm | 5276 | SELECT | rs_iva1.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_NotaCred.frm | 5278 | SELECT | rs_iva2.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_NotaCred.frm | 5377 | SELECT | rs_ImpInt.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_NotaCred.frm | 5406 | SELECT | rs_dscto.Open "SELECT * from cont_paramatriz where id_parama… |
| Visualiza_CargaMovStock.frm | 4872 | SELECT | rs_vta.Open "SELECT * from cont_paramatriz where id_paramatr… |
| Visualiza_CargaMovStock.frm | 4979 | SELECT | rs_CapitalMat.Open "SELECT * from cont_paramatriz where id_p… |
| Visualiza_CargaMovStock.frm | 5028 | SELECT | rs_faltant.Open "SELECT * from cont_paramatriz where id_para… |
| Visualiza_CargaMovStock.frm | 5140 | SELECT | rs_sobrante.Open "SELECT * from cont_paramatriz where id_par… |
| Visualiza_CargaMovStock.frm | 5194 | SELECT | rs_rotura.Open "SELECT * from cont_paramatriz where id_param… |
| NotaCredCon.frm | 6737 | SELECT | rs_ImpGastMat.Open "SELECT * from cont_paramatriz where id_p… |
| NotaCredCon.frm | 6834 | SELECT | rs_iva1.Open "SELECT * from cont_paramatriz where id_paramat… |
| NotaCredCon.frm | 6836 | SELECT | rs_iva2.Open "SELECT * from cont_paramatriz where id_paramat… |
| NotaCredCon.frm | 6934 | SELECT | '            rs_exento.Open "SELECT * from cont_paramatriz w… |
| NotaCredCon.frm | 7028 | SELECT | rs_percepMAT.Open "SELECT * from cont_paramatriz where id_pa… |
| NotaCredCon.frm | 7130 | SELECT | rs_PercepIva.Open "SELECT * from cont_paramatriz where id_pa… |
| Visualiza_PNotaDeb.frm | 3045 | SELECT | 'rs_AsientoCtas.Open "SELECT * from cont_paramatriz where id… |
| Visualiza_PNotaDeb.frm | 3094 | SELECT | rs_interes.Open " SELECT * from cont_paramatriz where id_par… |
| Visualiza_PNotaDeb.frm | 3132 | SELECT | rs_difCamb.Open " SELECT * from cont_paramatriz where id_par… |
| Visualiza_PNotaDeb.frm | 3169 | SELECT | rs_RechazoChqTerc.Open " SELECT * from cont_paramatriz where… |
| Visualiza_PNotaDeb.frm | 3205 | SELECT | rs_RechazoChqProp.Open " SELECT * from cont_paramatriz where… |
| Visualiza_PNotaDeb.frm | 3245 | SELECT | rs_GastosBanc.Open " SELECT * from cont_paramatriz where id_… |
| Visualiza_PNotaDeb.frm | 3284 | SELECT | rs_ComChqTer.Open " SELECT * from cont_paramatriz where id_p… |
| Visualiza_PNotaDeb.frm | 3319 | SELECT | rs_ComChqProp.Open " SELECT * from cont_paramatriz where id_… |
| Visualiza_PNotaDeb.frm | 3354 | SELECT | rs_exento.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_PNotaDeb.frm | 3379 | SELECT | rs_iva1.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_PNotaDeb.frm | 3381 | SELECT | rs_iva2.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_PNotaDeb.frm | 3383 | SELECT | rs_iva3.Open "SELECT * from cont_paramatriz where id_paramat… |
| Visualiza_PNotaDeb.frm | 3521 | SELECT | rs_ImpInt.Open "SELECT * from cont_paramatriz where id_param… |
| Visualiza_PNotaDeb.frm | 3552 | SELECT | rs_PercepIva.Open "SELECT * from cont_paramatriz where id_pa… |
| Visualiza_PNotaDeb.frm | 3583 | SELECT | rs_PercepGan.Open "SELECT * from cont_paramatriz where id_pa… |
| Visualiza_PNotaDeb.frm | 3611 | SELECT | rs_PercepIB1.Open "SELECT * from cont_paramatriz where id_pa… |
| Visualiza_PNotaDeb.frm | 3613 | SELECT | rs_PercepIB2.Open "SELECT * from cont_paramatriz where id_pa… |
| Visualiza_PNotaDeb.frm | 3710 | SELECT | rs_OtrosImp.Open "SELECT * from cont_paramatriz where id_par… |
| FacturaB_COPIA.frm | 11275 | SELECT | 'rs_AsientoCtas.Open "SELECT * from cont_paramatriz where id… |
| FacturaB_COPIA.frm | 11393 | SELECT | rs_dscto.Open "SELECT * from cont_paramatriz where id_parama… |
| FacturaB_COPIA.frm | 11424 | SELECT | rs_ImpInt.Open "SELECT * from cont_paramatriz where id_param… |
| FacturaB_COPIA.frm | 11450 | SELECT | rs_iva1.Open "SELECT * from cont_paramatriz where id_paramat… |
| FacturaB_COPIA.frm | 11452 | SELECT | rs_iva2.Open "SELECT * from cont_paramatriz where id_paramat… |
| FacturaB_COPIA.frm | 11550 | SELECT | '            rs_exento.Open "SELECT * from cont_paramatriz w… |
| FacturaB_COPIA.frm | 11647 | SELECT | rs_percepMAT.Open "SELECT * from cont_paramatriz where id_pa… |
| FacturaB_COPIA.frm | 11815 | SELECT | rs_vta.Open "SELECT * from cont_paramatriz where id_paramatr… |
| FacturaB_COPIA.frm | 11916 | SELECT | '        rs_vta.Open "SELECT * from cont_paramatriz where id… |
| … | … | … | *(600 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)