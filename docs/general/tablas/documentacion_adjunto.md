# Tabla `documentacion_adjunto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_doc_adjunto | INT | No | ✓ |  |  |
| id_cp_doc_adjunto | DECIMAL | Sí |  |  |  |
| fecha_doc_adjunto | DATE | Sí |  |  |  |
| nombre_doc_adjunto | VARCHAR | Sí |  |  |  |
| detalle_doc_adjunto | MEDIUMTEXT | Sí |  |  |  |
| tipo_doc_adjunto | VARCHAR | Sí |  |  |  |
| archivo_doc_adjunto | LONGBLOB | Sí |  |  |  |
| proceso | VARCHAR | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| id_mensaje | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| id_cliente_potencial | DOUBLE | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 2927 | SELECT | rs_pd_adjunto.Open "SELECT * FROM documentacion_adjunto WHER… |
| Erp_Carga_Parte_Diario.frm | 3168 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| mensaj_carga.frm | 859 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| mensaj_carga.frm | 901 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto where i… |
| Visualiza_Pedido.frm | 14630 | SELECT | '                            rs_adjunto.Open "SELECT * FROM … |
| Visualiza_POrden_Compra.frm | 5941 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| POrden_CompraCopia.frm | 5532 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| Crm_CargaCliPot.frm | 1932 | UPDATE | conn.Execute "UPDATE documentacion_adjunto " & _ |
| mensaj_abm.frm | 502 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE i… |
| mensaj_abm.frm | 547 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE i… |
| mensaj_abm.frm | 1085 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE i… |
| mensaj_abm.frm | 1152 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE i… |
| Documentacion.frm | 514 | SELECT | DataAdjunto.RecordSource = "SELECT * FROM documentacion_adju… |
| Documentacion.frm | 518 | SELECT | DataAdjunto.RecordSource = "SELECT * FROM documentacion_adju… |
| Documentacion.frm | 522 | SELECT | DataAdjunto.RecordSource = "SELECT * FROM documentacion_adju… |
| Documentacion.frm | 532 | SELECT | DataAdjunto.RecordSource = "SELECT * FROM documentacion_adju… |
| Documentacion.frm | 667 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| Documentacion.frm | 713 | SELECT | 'DataAdjunto.RecordSource = "select * from documentacion_adj… |
| Documentacion.frm | 794 | SELECT | rs_eliminar.Open "SELECT * FROM documentacion_adjunto WHERE … |
| Documentacion.frm | 799 | SELECT | conn.Execute "DELETE FROM documentacion_adjunto WHERE id_doc… |
| Documentacion.frm | 799 | DELETE | conn.Execute "DELETE FROM documentacion_adjunto WHERE id_doc… |
| Documentacion.frm | 813 | SELECT | '    DataAdjunto.RecordSource = "select * from documentacion… |
| CargaProveedor.frm | 4511 | SELECT | 'rs_adjunto_cli.Open "select * from documentacion_adjunto wh… |
| CargaProveedor.frm | 4518 | SELECT | '        DataAdjunto.RecordSource = "select * from documenta… |
| Pedido.frm | 4687 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| ConsultaComprobante.frm | 5025 | SELECT | conn.Execute "DELETE FROM documentacion_adjunto WHERE docume… |
| ConsultaComprobante.frm | 5025 | DELETE | conn.Execute "DELETE FROM documentacion_adjunto WHERE docume… |
| ConsultaComprobante.frm | 18449 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2372 | SELECT | rs_pd_adjunto.Open "SELECT * FROM documentacion_adjunto WHER… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2757 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| Visualiza_PPresupuesto.frm | 4751 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| PPresupuesto.frm | 5737 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| Visualiza_POrden_CompraC.frm | 5209 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| trz_trazabilidadComp.frm | 3250 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| trz_trazabilidadComp.frm | 4406 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| Carga_Cliente.frm | 6677 | SELECT | 'rs_adjunto_cli.Open "select * from documentacion_adjunto wh… |
| Carga_Cliente.frm | 6684 | SELECT | '        DataAdjunto.RecordSource = "select * from documenta… |
| Visualiza_PPresupuestoC.frm | 4581 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| POrden_Compra.frm | 6423 | SELECT | rs_adjunto.Open "select * from documentacion_adjunto", conn,… |
| Visualiza.bas | 4528 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| Visualiza.bas | 6018 | SELECT | rs_adjunto.Open "SELECT * FROM documentacion_adjunto WHERE c… |
| Visualiza.bas | 8545 | SELECT | rs_mensaje.Open "SELECT * FROM documentacion_adjunto WHERE c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)