# Tabla `percep_cli_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_cli_abm | INT | No | ✓ |  |  |
| nombre_percep_cli_abm | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |

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
| NotaCredCon.frm | 6980 | SELECT | "From percep_cli_abm " & _ |
| NotaCredCon.frm | 10841 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCredCon.frm | 11388 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| FacturaB_COPIA.frm | 11595 | SELECT | "From percep_cli_abm " & _ |
| FacturaB_COPIA.frm | 18498 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCredDesc.frm | 4090 | SELECT | "From percep_cli_abm " & _ |
| NotaCredDesc.frm | 8640 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCredDesc.frm | 9123 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred_COPIA.frm | 8327 | SELECT | "From percep_cli_abm " & _ |
| NotaCred_COPIA.frm | 13502 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV.frm | 18898 | SELECT | "From percep_cli_abm " & _ |
| TPV.frm | 19871 | SELECT | "From percep_cli_abm " & _ |
| TPV.frm | 37316 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV.frm | 37702 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV.frm | 38321 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV.frm | 38714 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| Info_Impositivo.frm | 2401 | SELECT | DataPercepCli.RecordSource = "SELECT * FROM percep_cli_abm O… |
| FacturaB.frm | 17403 | SELECT | "From percep_cli_abm " & _ |
| FacturaB.frm | 25296 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| FacturaB.frm | 25641 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| Percep_parametrizacion.frm | 832 | JOIN | "LEFT JOIN percep_cli_abm pca ON pca.id_percep_cli_abm = pcp… |
| Percep_parametrizacion.frm | 877 | JOIN | "LEFT JOIN percep_cli_abm pca ON pca.id_percep_cli_abm = pcp… |
| Percep_parametrizacion.frm | 910 | JOIN | "LEFT JOIN percep_cli_abm pca ON pca.id_percep_cli_abm = pcp… |
| Percep_parametrizacion.frm | 924 | SELECT | DataPercep.RecordSource = "select * from Percep_cli_abm wher… |
| NotaCred_SinCompO.frm | 10661 | SELECT | "From percep_cli_abm " & _ |
| NotaCred_SinCompO.frm | 17144 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred_SinCompO.frm | 17697 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| ABMPercepcionesCli.frm | 384 | SELECT | Data_percepciones.RecordSource = "select * from percep_cli_a… |
| ABMPercepcionesCli.frm | 609 | SELECT | Data_percepciones.RecordSource = "SELECT * FROM percep_cli_a… |
| FacturaA.frm | 13460 | SELECT | "From percep_cli_abm " & _ |
| FacturaA.frm | 14950 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| FacturaA.frm | 21806 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred_Importe.frm | 6389 | SELECT | "From percep_cli_abm " & _ |
| NotaCred_Importe.frm | 10524 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred_Importe.frm | 11070 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| Exportacion.frm | 1178 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |
| Exportacion.frm | 11711 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |
| Exportacion.frm | 12061 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |
| Exportacion.frm | 12214 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |
| Exportacion.frm | 12425 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |
| NotaCredCopia.frm | 9175 | SELECT | "From percep_cli_abm " & _ |
| NotaCredCopia.frm | 14752 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCredCopia.frm | 15313 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| CargaPercepcionesCli.frm | 363 | SELECT | rs_percep.Open "SELECT nombre_percep_cli_abm FROM percep_cli… |
| CargaPercepcionesCli.frm | 379 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_abm where id_percep… |
| CargaPercepcionesCli.frm | 395 | SELECT | ABMPercepcionesCli.Data_percepciones.RecordSource = "SELECT … |
| CargaPercepcionesCli.frm | 407 | SELECT | rs_percep.Open "SELECT * FROM percep_cli_abm WHERE id_percep… |
| CargaPercepcionesCli.frm | 421 | SELECT | ABMPercepcionesCli.Data_percepciones.RecordSource = "SELECT … |
| NotaDeb.frm | 7545 | SELECT | "From percep_cli_abm " & _ |
| NotaDeb.frm | 12610 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaDeb.frm | 13193 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred.frm | 9759 | SELECT | "From percep_cli_abm " & _ |
| NotaCred.frm | 15435 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaCred.frm | 15996 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaDebCopia.frm | 7196 | SELECT | "From percep_cli_abm " & _ |
| NotaDebCopia.frm | 12261 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| NotaDebCopia.frm | 12844 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| Visualiza_NotaCredCon.frm | 6459 | SELECT | "From percep_cli_abm " & _ |
| TPV_2.frm | 16995 | SELECT | "From percep_cli_abm " & _ |
| TPV_2.frm | 17968 | SELECT | "From percep_cli_abm " & _ |
| TPV_2.frm | 34696 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV_2.frm | 35079 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV_2.frm | 35694 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| TPV_2.frm | 36081 | SELECT | "FROM percep_cli_abm,percep_cli_tipo,percep_cli_temp " & _ |
| CargaPercepcionesCliTipo.frm | 853 | SELECT | DataPercepcion.RecordSource = "select * from percep_cli_abm" |
| ABMPercepcionesCliTipo.frm | 427 | JOIN | '                                     " LEFT JOIN percep_cli… |
| ABMPercepcionesCliTipo.frm | 654 | JOIN | " LEFT JOIN percep_cli_abm ON (percep_cli_abm.id_percep_cli_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)