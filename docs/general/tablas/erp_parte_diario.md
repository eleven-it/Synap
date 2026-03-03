# Tabla `erp_parte_diario`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_parte_diario | INT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| fecha_carga | DATE | Sí |  |  |  |
| nro_ot_cliente | VARCHAR | Sí |  |  |  |
| nro_parte_diario | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_tarea | INT | Sí |  |  |  |
| detalle | TEXT | Sí |  |  |  |
| equipo | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| NroCompBusq | INT | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| CodSucursal | INT | Sí |  |  |  |
| adjunto | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 2483 | SELECT | rs_erp_parte_diario.Open "SELECT * from erp_parte_diario WHE… |
| Erp_Carga_Parte_Diario.frm | 2491 | SELECT | rs_erp_parte_diario.Open "SELECT * FROM erp_parte_diario WHE… |
| Erp_Carga_Parte_Diario.frm | 2971 | SELECT | rs_erp_parte_diario.Open "SELECT * FROM erp_parte_diario WHE… |
| Erp_Carga_Parte_Diario.frm | 3322 | JOIN | '                                            " LEFT JOIN `er… |
| Erp_Carga_Parte_Diario.frm | 3330 | JOIN | '                                            " LEFT JOIN `er… |
| Erp_Carga_Parte_Diario.frm | 3803 | SELECT | 'rs_estado_pd.Open "SELECT estado FROM erp_parte_diario WHER… |
| Erp_Carga_Parte_Diario.frm | 3804 | SELECT | rs_estado_pd.Open "SELECT estado FROM erp_parte_diario WHERE… |
| Visualiza_Pedido.frm | 14614 | SELECT | '                        rs_pd_consulta.Open "SELECT * FROM … |
| Pedido.frm | 4671 | SELECT | rs_pd_consulta.Open "SELECT * FROM erp_parte_diario WHERE Co… |
| ConsultaComprobante.frm | 3030 | SELECT | " FROM erp_parte_diario AS pd " & _ |
| ConsultaComprobante.frm | 3064 | SELECT | " FROM erp_parte_diario AS pd " & _ |
| ConsultaComprobante.frm | 5020 | UPDATE | conn.Execute "UPDATE erp_parte_diario SET anulado ='Si' WHER… |
| ConsultaComprobante.frm | 10315 | SELECT | rs_pd.Open "SELECT * FROM erp_parte_diario WHERE CodigoMovim… |
| ConsultaComprobante.frm | 10335 | UPDATE | '                conn.Execute "UPDATE erp_parte_diario as pd… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2416 | SELECT | rs_erp_parte_diario.Open "SELECT * FROM erp_parte_diario WHE… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2921 | JOIN | '                                            " LEFT JOIN `er… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2929 | JOIN | '                                            " LEFT JOIN `er… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3390 | SELECT | 'rs_estado_pd.Open "SELECT estado FROM erp_parte_diario WHER… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3391 | SELECT | rs_estado_pd.Open "SELECT estado FROM erp_parte_diario WHERE… |
| Erp_Busqueda_PD.frm | 1328 | SELECT | '            "erp_parte_diario.TipoComprobante, erp_parte_di… |
| Erp_Busqueda_PD.frm | 1352 | SELECT | '    rs_pd.Open "SELECT erp_parte_diario.*,erp_zona.id_zona,… |
| Erp_Busqueda_PD.frm | 1379 | SELECT | '    rs_pd.Open "SELECT erp_parte_diario.*,erp_zona.id_zona,… |
| Erp_Busqueda_PD.frm | 1405 | SELECT | '    rs_pd.Open "SELECT erp_parte_diario.*,erp_zona.id_zona,… |
| Erp_Busqueda_PD.frm | 1562 | SELECT | "erp_parte_diario.TipoComprobante, erp_parte_diario.id_pv, e… |
| Visualiza.bas | 8505 | SELECT | " FROM erp_parte_diario AS pd " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)