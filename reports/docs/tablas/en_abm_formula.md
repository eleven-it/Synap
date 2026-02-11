# Tabla `en_abm_formula`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_abm_formula | DOUBLE | No | ✓ |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| cantidad_articulo | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| cantidad_unidad_display | DOUBLE | Sí |  |  |  |
| cantidad_dividir | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| articulo | en_abm_formula | Principal.frm | 7532 | " FROM articulo LEFT JOIN en_abm_formula as formula ON formula.id_articulo = art… |
| en_abm_formula | articulo | Principal.frm | 7549 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |
| en_abm_formula | articulo | Principal.frm | 7693 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |
| en_abm_formula | articulo | Principal.frm | 7702 | " FROM en_abm_formula As formula LEFT JOIN articulo AS insumo ON insumo.IDArt=fo… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| FacturaB_COPIA.frm | 4975 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| FacturaB_COPIA.frm | 17942 | SELECT | "FROM en_abm_formula " & _ |
| TPV.frm | 9896 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| TPV.frm | 35787 | SELECT | "FROM en_abm_formula " & _ |
| TPV.frm | 40273 | JOIN | '                                  "INNER JOIN en_abm_formul… |
| Lista_Pedidos_OPT.frm | 2845 | SELECT | "FROM en_abm_formula " & _ |
| Lista_Pedidos_OPT.frm | 2884 | SELECT | "FROM en_abm_formula " & _ |
| FacturaB.frm | 6104 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| FacturaB.frm | 8935 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| FacturaB.frm | 24701 | SELECT | "FROM en_abm_formula " & _ |
| NotaCred_SinCompO.frm | 14830 | JOIN | "LEFT JOIN en_abm_formula ON (en_abm_formula.id_en_abm = en_… |
| FacturaA.frm | 5820 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| FacturaA.frm | 21251 | SELECT | "FROM en_abm_formula " & _ |
| Remito.frm | 5002 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| Remito.frm | 12690 | SELECT | "FROM en_abm_formula " & _ |
| En_CargaOE_ArtE.frm | 909 | SELECT | '                    rs_Formula.Open "SELECT en_abm_formula.… |
| En_CargaOE_ArtE.frm | 921 | SELECT | " articulo.Lote FROM en_abm_formula " & _ |
| En_CargaOE_ArtE.frm | 1241 | SELECT | rs_Formula.Open "SELECT en_abm_formula.*,articulo.NombreArti… |
| En_Info.frm | 3832 | SELECT | "FROM en_abm_formula AS f " & _ |
| En_abm.frm | 884 | SELECT | DataFormula.RecordSource = "SELECT * FROM en_abm_formula " &… |
| En_abm.frm | 1107 | SELECT | '                rs_EstaDef.Open "SELECT * from en_abm_formu… |
| En_abm.frm | 1122 | SELECT | "  FROM en_abm_formula " & _ |
| En_abm.frm | 1305 | SELECT | "FROM en_abm_formula " & _ |
| En_abm.frm | 1342 | SELECT | "FROM en_abm_formula " & _ |
| En_abm.frm | 1391 | SELECT | "FROM en_abm_formula WHERE id_en_abm = " & DataArtEn.Records… |
| En_abmDef.frm | 813 | SELECT | conn.Execute "DELETE FROM en_abm_formula WHERE id_en_abm = "… |
| En_abmDef.frm | 813 | DELETE | conn.Execute "DELETE FROM en_abm_formula WHERE id_en_abm = "… |
| En_abmDef.frm | 816 | SELECT | rs_Formula.Open "SELECT * FROM en_abm_formula where id_en_ab… |
| En_abmDef.frm | 884 | SELECT | '    rs_consulta_art.Open "SELECT * FROM en_abm_formula WHER… |
| En_abmDef.frm | 939 | SELECT | rs_Formula.Open "SELECT * FROM en_abm_formula where id_en_ab… |
| En_abm2.frm | 666 | SELECT | DataFormula.RecordSource = "SELECT * FROM en_abm_formula " &… |
| En_abm2.frm | 785 | SELECT | rs_EstaDef.Open "SELECT * from en_abm_formula WHERE id_en_ab… |
| En_abm2.frm | 872 | SELECT | DataFormula.RecordSource = "SELECT articulo.NombreArticulo, … |
| CargaMovStock.frm | 3671 | SELECT | '                            "From en_abm_formula " & _ |
| CargaMovStock.frm | 8641 | SELECT | "FROM en_abm_formula " & _ |
| CargaMovStock.frm | 8667 | SELECT | "FROM en_abm_formula " & _ |
| CargaMovStock.frm | 8719 | SELECT | "FROM en_abm_formula " & _ |
| En_CargaRef.frm | 898 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_articulo = … |
| En_CargaRef.frm | 1040 | SELECT | "FROM en_abm_formula WHERE anulado = 'No' AND en_abm_formula… |
| TPV_2.frm | 9621 | JOIN | "INNER JOIN en_abm_formula ON (en_abm_formula.id_en_abm = ar… |
| TPV_2.frm | 33225 | SELECT | "FROM en_abm_formula " & _ |
| Principal.frm | 7532 | JOIN | " FROM articulo LEFT JOIN en_abm_formula as formula ON formu… |
| Principal.frm | 7549 | SELECT | " FROM en_abm_formula As formula LEFT JOIN articulo AS insum… |
| Principal.frm | 7664 | SELECT | " FROM en_abm_formula AS formula" & _ |
| Principal.frm | 7693 | SELECT | " FROM en_abm_formula As formula LEFT JOIN articulo AS insum… |
| Principal.frm | 7702 | SELECT | " FROM en_abm_formula As formula LEFT JOIN articulo AS insum… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)