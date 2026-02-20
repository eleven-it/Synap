# Tabla `nc_concepto_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_nc_temp | INT | No | ✓ |  |  |
| nombre_temp | VARCHAR | Sí |  |  |  |
| importe_temp | DECIMAL | Sí |  |  |  |
| id_gasto | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| CodIva_gasto | INT | Sí |  |  |  |
| IvaxR | DOUBLE | Sí |  |  |  |
| alicuota_iva | DOUBLE | Sí |  |  |  |

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
| NotaCredCon.frm | 6415 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| NotaCredCon.frm | 6415 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| NotaCredCon.frm | 10011 | SELECT | rs.Open "SELECT * FROM nc_concepto_temp WHERE id_gasto = " &… |
| NotaCredCon.frm | 10036 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM nc_conce… |
| NotaCredCon.frm | 10064 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM nc_conce… |
| NotaCredCon.frm | 10142 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_nc_temp … |
| NotaCredCon.frm | 10142 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_nc_temp … |
| NotaCredCon.frm | 10220 | SELECT | "From nc_concepto_temp " & _ |
| Visualiza_NotaCredCon.frm | 5886 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Visualiza_NotaCredCon.frm | 5886 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Visualiza_NotaCredCon.frm | 8775 | SELECT | rs.Open "SELECT * FROM nc_concepto_temp WHERE id_gasto = " &… |
| Visualiza_NotaCredCon.frm | 8797 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM nc_conce… |
| Visualiza_NotaCredCon.frm | 8814 | SELECT | data_otro_egreso_temp.RecordSource = "SELECT * FROM nc_conce… |
| Visualiza_NotaCredCon.frm | 8882 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_nc_temp … |
| Visualiza_NotaCredCon.frm | 8882 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_nc_temp … |
| Principal.frm | 6119 | SELECT | conn.Execute "delete from nc_concepto_temp where id_usuario … |
| Principal.frm | 6119 | DELETE | conn.Execute "delete from nc_concepto_temp where id_usuario … |
| Principal.frm | 6185 | SELECT | conn.Execute "delete from nc_concepto_temp where id_usuario … |
| Principal.frm | 6185 | DELETE | conn.Execute "delete from nc_concepto_temp where id_usuario … |
| Principal.frm | 13171 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Principal.frm | 13171 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Principal.frm | 13174 | INSERT | conn.Execute "INSERT INTO nc_concepto_temp " & _ |
| Principal.frm | 13182 | SELECT | rs_Tot.Open "SELECT SUM(importe_temp) As TotGasto FROM nc_co… |
| Principal.frm | 13197 | SELECT | Visualiza_NotaCredCon.data_otro_egreso_temp.RecordSource = "… |
| Visualiza.bas | 3583 | SELECT | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Visualiza.bas | 3583 | DELETE | conn.Execute "DELETE FROM nc_concepto_temp WHERE id_usuario … |
| Visualiza.bas | 3586 | INSERT | conn.Execute "INSERT INTO nc_concepto_temp " & _ |
| Visualiza.bas | 3594 | SELECT | rs_Tot.Open "SELECT SUM(importe_temp) As TotGasto FROM nc_co… |
| Visualiza.bas | 3609 | SELECT | Visualiza_NotaCredCon.data_otro_egreso_temp.RecordSource = "… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)