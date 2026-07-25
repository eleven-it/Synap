# Tabla `percep_cli`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_cli | DOUBLE | No | ✓ |  |  |
| id_percep_cli_tipo | INT | Sí |  |  |  |
| alicuota_percep_cli | DECIMAL | Sí |  |  |  |
| importe_percep_cli | DECIMAL | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
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
| NotaCredCon.frm | 2715 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| FacturaB_COPIA.frm | 4432 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| NotaCredDesc.frm | 2550 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| NotaCred_COPIA.frm | 3335 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| TPV.frm | 6449 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| TPV.frm | 9418 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Logi_Gestion2.frm | 7881 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE codigo_mo… |
| Visualiza_Pedido.frm | 9907 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE codigo_mo… |
| Visualiza_Pedido.frm | 10816 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza_Pedido.frm | 14288 | SELECT | '                        rs_percep_cli.Open "SELECT * FROM p… |
| Logi_Gestion.frm | 9400 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE codigo_mo… |
| percep_visualiza.frm | 315 | SELECT | "percep_cli.importe_percep_cli, percep_cli_tipo.cod_afip, " … |
| FacturaB.frm | 5466 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| FacturaB.frm | 8297 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| NotaCred_SinCompO.frm | 4177 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| FacturaA.frm | 5185 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| NotaCred_Importe.frm | 2305 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Exportacion.frm | 1174 | SELECT | rs_factura.Open " SELECT * FROM percep_cli " & _ |
| Exportacion.frm | 2448 | SELECT | rs_exp.Open "SELECT * FROM percep_cli " & _ |
| Exportacion.frm | 2623 | SELECT | "FROM percep_cli pc " & _ |
| Exportacion.frm | 2651 | SELECT | "FROM percep_cli pc " & _ |
| Exportacion.frm | 2687 | SELECT | "FROM percep_cli pc " & _ |
| Exportacion.frm | 11707 | SELECT | rs_exp.Open " SELECT * FROM percep_cli " & _ |
| Exportacion.frm | 12057 | SELECT | rs_exp.Open " SELECT percep_cli.*,cuentacliente.subtotaldesc… |
| Exportacion.frm | 12210 | SELECT | " FROM percep_cli " & _ |
| Exportacion.frm | 12421 | SELECT | " FROM percep_cli " & _ |
| NotaCredCopia.frm | 3855 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Presupuesto.frm | 4019 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Pedido.frm | 4334 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| ConsultaComprobante.frm | 6392 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 7233 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 7953 | SELECT | '            rs_percep.Open "SELECT percep_cli.codigo_movimi… |
| ConsultaComprobante.frm | 8683 | SELECT | '                rs_percep.Open "SELECT percep_cli.codigo_mo… |
| ConsultaComprobante.frm | 9223 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 9970 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 10158 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 10347 | SELECT | rs_percep.Open "SELECT percep_cli.id_percep_cli,percep_cli.c… |
| ConsultaComprobante.frm | 11129 | SELECT | rs_percep.Open "SELECT id_percep_cli,percep_cli.codigo_movim… |
| ConsultaComprobante.frm | 14526 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 15340 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 16721 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 17671 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 24057 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 24880 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 31894 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 32818 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 33763 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 34497 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ConsultaComprobante.frm | 35025 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| NotaDeb.frm | 2936 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| percep_ib_compras.frm | 801 | SELECT | '                "percep_cli.importe_percep_cli, percep_cli_… |
| NotaCred.frm | 3918 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Visualiza_Presupuesto.frm | 9556 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE codigo_mo… |
| NotaDebCopia.frm | 2846 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Visualiza_NotaCredCon.frm | 2608 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| TPV_2.frm | 5912 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| TPV_2.frm | 9200 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE id_percep… |
| Principal.frm | 9918 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Principal.frm | 10630 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| ListaFacturasNC.frm | 1821 | SELECT | rs_percep_cli.Open "SELECT * FROM percep_cli WHERE codigo_mo… |
| adm_felectronicas.frm | 2000 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 3462 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 4930 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 6339 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 7644 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 8965 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 10400 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 11323 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 12268 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| adm_felectronicas.frm | 13002 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 9052 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 9953 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 11064 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 12480 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 13994 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 15433 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 16775 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 18135 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 19203 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |
| Visualiza.bas | 20035 | SELECT | rs_percep.Open "SELECT percep_cli.*,percep_cli_tipo.nombre_p… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)