# Tabla `transferencia_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_transf_temp | BIGINT | No | ✓ |  |  |
| fecha_transf | DATE | Sí |  |  |  |
| nro_referencia | DOUBLE | Sí |  |  |  |
| id_cuentabancaria | INT | Sí |  |  |  |
| importe_transf | DOUBLE | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| detalle_transf | VARCHAR | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| id_transf | BIGINT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 12813 | SELECT | rs_transferencia_temp.Open "SELECT transferencia_temp.*, ban… |
| Visualiza_ReciboCobro.frm | 15872 | SELECT | Data_transferencia.RecordSource = "SELECT transferencia_temp… |
| OrdenPago.frm | 12555 | SELECT | conn.Execute "delete from transferencia_temp where id_usuari… |
| OrdenPago.frm | 12555 | DELETE | conn.Execute "delete from transferencia_temp where id_usuari… |
| OrdenPago.frm | 16477 | SELECT | conn.Execute "DELETE FROM transferencia_temp WHERE id_transf… |
| OrdenPago.frm | 16477 | DELETE | conn.Execute "DELETE FROM transferencia_temp WHERE id_transf… |
| OrdenPago.frm | 16495 | SELECT | rs_transferencia_temp_total.Open "SELECT SUM(importe_transf)… |
| OrdenPago.frm | 16506 | SELECT | OrdenPago.Data_transferencia.RecordSource = "SELECT transfer… |
| Carga_Transferencia_REC_OP.frm | 610 | SELECT | Data_transferencia_temp.RecordSource = "SELECT * FROM transf… |
| Carga_Transferencia_REC_OP.frm | 634 | SELECT | Data_transferencia_temp.RecordSource = "SELECT * FROM transf… |
| Carga_Transferencia_REC_OP.frm | 682 | SELECT | Data_transferencia_temp.RecordSource = "SELECT * FROM transf… |
| Carga_Transferencia_REC_OP.frm | 706 | SELECT | Data_transferencia_temp.RecordSource = "SELECT * FROM transf… |
| Carga_Transferencia_REC_OP.frm | 764 | SELECT | '    rs_transferencia_temp_total.Open "SELECT SUM(importe_tr… |
| Carga_Transferencia_REC_OP.frm | 775 | SELECT | '    ReciboCobro.Data_transferencia.RecordSource = "SELECT t… |
| ReciboCobro.frm | 8880 | SELECT | conn.Execute "DELETE FROM transferencia_temp WHERE id_transf… |
| ReciboCobro.frm | 8880 | DELETE | conn.Execute "DELETE FROM transferencia_temp WHERE id_transf… |
| ReciboCobro.frm | 11744 | SELECT | conn.Execute "delete from transferencia_temp where id_usuari… |
| ReciboCobro.frm | 11744 | DELETE | conn.Execute "delete from transferencia_temp where id_usuari… |
| ReciboCobro.frm | 17348 | SELECT | rs_transferencia_temp_total.Open "SELECT SUM(importe_transf)… |
| ReciboCobro.frm | 17359 | SELECT | ReciboCobro.Data_transferencia.RecordSource = "SELECT transf… |
| Visualiza_OrdenPago.frm | 9427 | SELECT | rs_transferencia_temp.Open "SELECT transferencia_temp.*, ban… |
| Visualiza_OrdenPago.frm | 11964 | SELECT | '    rs_transferencia_temp_total.Open "SELECT SUM(importe_tr… |
| Visualiza_OrdenPago.frm | 11975 | SELECT | Data_transferencia.RecordSource = "SELECT transferencia_temp… |
| Visualiza.bas | 6148 | SELECT | conn.Execute "delete from transferencia_temp where id_usuari… |
| Visualiza.bas | 6148 | DELETE | conn.Execute "delete from transferencia_temp where id_usuari… |
| Visualiza.bas | 6377 | SELECT | Visualiza_ReciboCobro.Data_transferencia.RecordSource = "SEL… |
| Visualiza.bas | 6422 | SELECT | Visualiza_ReciboCobro.Data_transferencia.RecordSource = "SEL… |
| Visualiza.bas | 7378 | SELECT | conn.Execute "delete from transferencia_temp where id_usuari… |
| Visualiza.bas | 7378 | DELETE | conn.Execute "delete from transferencia_temp where id_usuari… |
| Visualiza.bas | 7669 | SELECT | Visualiza_OrdenPago.Data_transferencia.RecordSource = "SELEC… |
| Visualiza.bas | 7711 | SELECT | Visualiza_OrdenPago.Data_transferencia.RecordSource = "SELEC… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)