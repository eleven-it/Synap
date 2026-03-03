# Tabla `percep_cli_param`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_cli_param | DOUBLE | No | ✓ |  |  |
| id_percep_cli_abm | INT | Sí |  |  |  |
| id_percep_cli_tipo | INT | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |

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
| NotaCredCon.frm | 5998 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCredCon.frm | 9834 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCredCon.frm | 11684 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| FacturaB_COPIA.frm | 9801 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCredDesc.frm | 1506 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCredDesc.frm | 9409 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred_COPIA.frm | 7392 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| TPV.frm | 16824 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| TPV.frm | 16923 | SELECT | " FROM percep_cli_param " & _ |
| TPV.frm | 40475 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_Pedido.frm | 8055 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_Pedido.frm | 8160 | SELECT | " FROM percep_cli_param " & _ |
| Visualiza_Pedido.frm | 8456 | SELECT | '    rs_percep.Open "SELECT * FROM percep_cli_param WHERE id… |
| Visualiza_Pedido.frm | 13246 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| FacturaB.frm | 15329 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Percep_parametrizacion.frm | 787 | INSERT | ' conn.Execute "INSERT INTO percep_cli_param (id_percep_cli_… |
| Percep_parametrizacion.frm | 790 | INSERT | conn.Execute "INSERT INTO percep_cli_param (id_percep_cli_ab… |
| Percep_parametrizacion.frm | 803 | UPDATE | 'conn.Execute "UPDATE percep_cli_param SET id_percep_cli_tip… |
| Percep_parametrizacion.frm | 806 | UPDATE | conn.Execute "UPDATE percep_cli_param SET " & _ |
| Percep_parametrizacion.frm | 830 | SELECT | "FROM percep_cli_param pcp " & _ |
| Percep_parametrizacion.frm | 856 | SELECT | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |
| Percep_parametrizacion.frm | 856 | DELETE | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |
| Percep_parametrizacion.frm | 875 | SELECT | "FROM percep_cli_param pcp " & _ |
| Percep_parametrizacion.frm | 908 | SELECT | "FROM percep_cli_param pcp " & _ |
| Percep_parametrizacion.frm | 1138 | SELECT | rs_concepto_param.Open "SELECT concepto_dpip_sl, sujeto_dpip… |
| NotaCred_SinCompO.frm | 9545 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred_SinCompO.frm | 9669 | SELECT | " FROM percep_cli_param " & _ |
| NotaCred_SinCompO.frm | 18353 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| FacturaA.frm | 11030 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| FacturaA.frm | 11124 | SELECT | " FROM percep_cli_param " & _ |
| FacturaA.frm | 23480 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred_Importe.frm | 5524 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred_Importe.frm | 9339 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred_Importe.frm | 11362 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Exportacion.frm | 2626 | JOIN | "LEFT JOIN percep_cli_param pcp ON pcp.id_cliente = pc.id_cl… |
| Exportacion.frm | 2654 | JOIN | "LEFT JOIN percep_cli_param pcp ON pcp.id_cliente = pc.id_cl… |
| Exportacion.frm | 2692 | JOIN | "LEFT JOIN percep_cli_param pcp ON pcp.id_cliente = pc.id_cl… |
| NotaCredCopia.frm | 8234 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Remito.frm | 14025 | SELECT | '        rs_percep.Open "SELECT * FROM percep_cli_param WHER… |
| Presupuesto.frm | 7762 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Presupuesto.frm | 7867 | SELECT | " FROM percep_cli_param " & _ |
| Presupuesto.frm | 10971 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Pedido.frm | 9071 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Pedido.frm | 9177 | SELECT | " FROM percep_cli_param " & _ |
| Pedido.frm | 9475 | SELECT | '    rs_percep.Open "SELECT * FROM percep_cli_param WHERE id… |
| Pedido.frm | 12884 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaDeb.frm | 6249 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaDeb.frm | 6368 | SELECT | " FROM percep_cli_param " & _ |
| NotaDeb.frm | 14640 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| VisualizarFichaArt.frm | 3242 | SELECT | '    rs_percep.Open "SELECT * FROM percep_cli_param WHERE id… |
| NotaCred.frm | 8653 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaCred.frm | 8775 | SELECT | " FROM percep_cli_param " & _ |
| NotaCred.frm | 17126 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_Presupuesto.frm | 7806 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_Presupuesto.frm | 7911 | SELECT | " FROM percep_cli_param " & _ |
| Visualiza_Presupuesto.frm | 8196 | SELECT | '    rs_percep.Open "SELECT * FROM percep_cli_param WHERE id… |
| Visualiza_Presupuesto.frm | 11774 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| NotaDebCopia.frm | 6068 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_NotaCredCon.frm | 5476 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| Visualiza_NotaCredCon.frm | 8598 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| TPV_2.frm | 15105 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_param WHERE id_clie… |
| ABMPercepcionesCliTipo.frm | 708 | SELECT | rs_abmpercep.Open "SELECT * from percep_cli_param where id_p… |
| ABMPercepcionesCliTipo.frm | 724 | SELECT | rs_existePercep.Open "SELECT * from percep_cli_param where i… |
| ABMPercepcionesCliTipo.frm | 729 | SELECT | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |
| ABMPercepcionesCliTipo.frm | 729 | DELETE | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |
| ABMPercepcionesCliTipo.frm | 737 | INSERT | conn.Execute "INSERT INTO percep_cli_param " & _ |
| ABMPercepcionesCliTipo.frm | 779 | SELECT | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |
| ABMPercepcionesCliTipo.frm | 779 | DELETE | conn.Execute "DELETE FROM percep_cli_param WHERE id_percep_c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)