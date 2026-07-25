# Tabla `ref_movstock`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ref_movstock | INT | No | ✓ |  |  |
| nombre_ref_movstock | VARCHAR | Sí |  |  |  |
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
| Info_Stock.frm | 11692 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| Info_Stock.frm | 11698 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| Visualiza_CargaMovStock.frm | 2783 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| Visualiza_CargaMovStock.frm | 2789 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| ABMref_movstock.frm | 334 | SELECT | dataRmovstock.RecordSource = "select * from ref_movstock" |
| ABMref_movstock.frm | 494 | SELECT | consulta = "select * from ref_movstock  WHERE " & _ |
| CargaPermiso_Sistema_Puesto.frm | 3395 | SELECT | sql_adicional = ", COALESCE((SELECT ref_movstock.nombre_ref_… |
| CargaPermiso_Sistema_Puesto.frm | 3873 | SELECT | Permisos_Complejos 38, "nombre_ref_movstock", "SELECT * FROM… |
| ConsultaComprobante.frm | 13895 | SELECT | rs_movstock.Open "SELECT * FROM ref_movstock WHERE id_ref_mo… |
| CargaRef_movstock.frm | 245 | SELECT | rs_Rmovstock.Open "SELECT * FROM ref_movstock WHERE nombre_r… |
| CargaRef_movstock.frm | 261 | SELECT | rs_Rmovstock.Open "SELECT * FROM ref_movstock", conn, adOpen… |
| CargaRef_movstock.frm | 289 | SELECT | rs_Rmovstock.Open "SELECT * FROM ref_movstock WHERE id_ref_m… |
| CargaMovStock.frm | 3127 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| CargaMovStock.frm | 3133 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| ABMPermiso_Sistema.frm | 584 | SELECT | '    CargaPermiso_Sistema.data_ref_movstock.RecordSource = "… |
| Visualiza_CargaMovStock_Copia.frm | 2622 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |
| Visualiza_CargaMovStock_Copia.frm | 2628 | SELECT | data_ref_movstock.RecordSource = "SELECT * FROM ref_movstock… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)