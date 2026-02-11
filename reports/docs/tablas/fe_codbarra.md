# Tabla `fe_codbarra`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_fe_codbarra | DOUBLE | No | ✓ |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| img_codbarra | LONGBLOB | Sí |  |  |  |
| texto_cod_qr | VARCHAR | Sí |  |  |  |
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
| NotaCredCon.frm | 3452 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCredCon.frm | 10343 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCredCon.frm | 11654 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaB_COPIA.frm | 5429 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| FacturaB_COPIA.frm | 18013 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCredDesc.frm | 2815 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCredDesc.frm | 8155 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCredDesc.frm | 9380 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_COPIA.frm | 4359 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCred_COPIA.frm | 13015 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| TPV.frm | 7873 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV.frm | 10580 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV.frm | 36422 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV.frm | 36488 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV.frm | 38925 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV.frm | 39544 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| AjustarSaldos.frm | 1088 | SELECT | rs_Articulo.Open "SELECT * FROM fe_codbarra WHERE id_fe_codb… |
| FacturaB.frm | 6737 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaB.frm | 9558 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaB.frm | 24788 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaB.frm | 26788 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_SinCompO.frm | 5376 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_SinCompO.frm | 15187 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_SinCompO.frm | 18019 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaA.frm | 6415 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaA.frm | 21343 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| FacturaA.frm | 22632 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_Importe.frm | 3002 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_Importe.frm | 10029 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred_Importe.frm | 11334 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCredCopia.frm | 5085 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCredCopia.frm | 14238 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCredCopia.frm | 16388 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| ConsultaComprobante.frm | 31589 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 31589 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 31607 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| ConsultaComprobante.frm | 32458 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 32458 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 32471 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| ConsultaComprobante.frm | 33362 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 33362 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 33375 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| ConsultaComprobante.frm | 34316 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 34316 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| ConsultaComprobante.frm | 34329 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaDeb.frm | 4071 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaDeb.frm | 11720 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaDeb.frm | 14611 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas_consulta.frm | 3593 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas_consulta.frm | 3607 | SELECT | '                rs_fe_codbarra.Open "SELECT * FROM fe_codba… |
| adm_felectronicas_consulta.frm | 3952 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaCred.frm | 5220 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred.frm | 14920 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaCred.frm | 17055 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| NotaDebCopia.frm | 4015 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaDebCopia.frm | 11374 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| NotaDebCopia.frm | 14269 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| Visualiza_NotaCredCon.frm | 3266 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| TPV_2.frm | 7209 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| TPV_2.frm | 10391 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| TPV_2.frm | 33857 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_fe_c… |
| TPV_2.frm | 33913 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV_2.frm | 36289 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| TPV_2.frm | 36841 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 1698 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 1698 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 1716 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 3105 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 3105 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 3118 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 4530 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 4530 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 4543 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 6158 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 6158 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 6171 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 7291 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 7291 | DELETE | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| adm_felectronicas.frm | 7304 | SELECT | rs_fe_codbarra.Open "SELECT * FROM fe_codbarra WHERE id_usua… |
| adm_felectronicas.frm | 8603 | SELECT | conn.Execute "delete from fe_codbarra where codigo_movimient… |
| … | … | … | *(32 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)