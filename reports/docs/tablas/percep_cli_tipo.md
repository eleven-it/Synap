# Tabla `percep_cli_tipo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_cli_tipo | INT | No | ✓ |  |  |
| id_percep_cli_abm | INT | Sí |  |  |  |
| nombre_percep_cli_tipo | VARCHAR | Sí |  |  |  |
| alicuota_percep_cli_tipo | DECIMAL | Sí |  |  |  |
| tipo_calculo | VARCHAR | Sí |  |  |  |
| importe_minimo | DECIMAL | Sí |  |  |  |
| cod_afip | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| codigo_tipo_regimen | VARCHAR | Sí |  |  |  |
| id_jurisdiccion | DOUBLE | Sí |  |  |  |
| resol_afip_5329_iva | VARCHAR | Sí |  |  |  |
| alicuota_percep_cli_tipo_sec | DOUBLE | Sí |  |  |  |
| tipo_webservice | VARCHAR | Sí |  |  |  |

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
| NotaCredCon.frm | 6002 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCredCon.frm | 6981 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCredCon.frm | 9839 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCredCon.frm | 11688 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| FacturaB_COPIA.frm | 9805 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| FacturaB_COPIA.frm | 11596 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCredDesc.frm | 1510 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCredDesc.frm | 4091 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCredDesc.frm | 9413 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_COPIA.frm | 7396 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_COPIA.frm | 8328 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| TPV.frm | 16828 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| TPV.frm | 16924 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| TPV.frm | 16932 | SELECT | " FROM percep_cli_tipo " & _ |
| TPV.frm | 18899 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| TPV.frm | 19872 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| TPV.frm | 40479 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Visualiza_Pedido.frm | 8059 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Visualiza_Pedido.frm | 8161 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| Visualiza_Pedido.frm | 8169 | SELECT | " FROM percep_cli_tipo " & _ |
| Visualiza_Pedido.frm | 8460 | SELECT | '            rs_percep_calculo.Open "SELECT * FROM percep_cl… |
| Visualiza_Pedido.frm | 13250 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| percep_visualiza.frm | 316 | JOIN | "LEFT JOIN percep_cli_tipo ON percep_cli_tipo.id_percep_cli_… |
| FacturaB.frm | 15333 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| FacturaB.frm | 17404 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Percep_parametrizacion.frm | 727 | SELECT | rs_tipo.Open "SELECT id_jurisdiccion FROM percep_cli_tipo WH… |
| Percep_parametrizacion.frm | 831 | JOIN | "LEFT JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = p… |
| Percep_parametrizacion.frm | 876 | JOIN | "LEFT JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = p… |
| Percep_parametrizacion.frm | 909 | JOIN | "LEFT JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = p… |
| Percep_parametrizacion.frm | 1024 | SELECT | DataTipoPercep.RecordSource = "select * from percep_cli_tipo… |
| Percep_parametrizacion.frm | 1121 | SELECT | rs_tipo.Open "SELECT id_jurisdiccion FROM percep_cli_tipo WH… |
| NotaCred_SinCompO.frm | 9549 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_SinCompO.frm | 9670 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| NotaCred_SinCompO.frm | 9678 | SELECT | " FROM percep_cli_tipo " & _ |
| NotaCred_SinCompO.frm | 10662 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCred_SinCompO.frm | 18357 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| FacturaA.frm | 11034 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| FacturaA.frm | 11125 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| FacturaA.frm | 11133 | SELECT | " FROM percep_cli_tipo " & _ |
| FacturaA.frm | 13461 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| FacturaA.frm | 23484 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_Importe.frm | 5528 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_Importe.frm | 6390 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCred_Importe.frm | 9344 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred_Importe.frm | 11366 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Exportacion.frm | 1177 | JOIN | " LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Exportacion.frm | 2451 | JOIN | "LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cli… |
| Exportacion.frm | 2625 | JOIN | "INNER JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = … |
| Exportacion.frm | 2653 | JOIN | "INNER JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = … |
| Exportacion.frm | 2689 | JOIN | "INNER JOIN percep_cli_tipo pct ON pct.id_percep_cli_tipo = … |
| Exportacion.frm | 11710 | JOIN | " LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Exportacion.frm | 12060 | JOIN | " LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Exportacion.frm | 12213 | JOIN | " LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Exportacion.frm | 12424 | JOIN | " LEFT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCredCopia.frm | 8238 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCredCopia.frm | 9176 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| Remito.frm | 14029 | SELECT | '                rs_percep_calculo.Open "SELECT * FROM perce… |
| Presupuesto.frm | 7766 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Presupuesto.frm | 7868 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| Presupuesto.frm | 7876 | SELECT | " FROM percep_cli_tipo " & _ |
| Presupuesto.frm | 10975 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Pedido.frm | 9075 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Pedido.frm | 9178 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| Pedido.frm | 9186 | SELECT | " FROM percep_cli_tipo " & _ |
| Pedido.frm | 9479 | SELECT | '            rs_percep_calculo.Open "SELECT * FROM percep_cl… |
| Pedido.frm | 12888 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaDeb.frm | 6253 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaDeb.frm | 6369 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| NotaDeb.frm | 6377 | SELECT | " FROM percep_cli_tipo " & _ |
| NotaDeb.frm | 7546 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaDeb.frm | 14644 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| percep_ib_compras.frm | 802 | JOIN | '                "LEFT JOIN percep_cli_tipo ON percep_cli_ti… |
| VisualizarFichaArt.frm | 3247 | SELECT | '            rs_percep_calculo.Open "SELECT * FROM percep_cl… |
| NotaCred.frm | 8657 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| NotaCred.frm | 8776 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| NotaCred.frm | 8784 | SELECT | " FROM percep_cli_tipo " & _ |
| NotaCred.frm | 9760 | JOIN | "RIGHT JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_cl… |
| NotaCred.frm | 17130 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Visualiza_Presupuesto.frm | 7810 | SELECT | rs_percep_calculo.Open "SELECT * FROM percep_cli_tipo WHERE … |
| Visualiza_Presupuesto.frm | 7912 | JOIN | " INNER JOIN percep_cli_tipo ON (percep_cli_tipo.id_percep_c… |
| … | … | … | *(17 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)