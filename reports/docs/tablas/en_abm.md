# Tabla `en_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_abm | DOUBLE | No | ✓ |  |  |
| nombre_en_abm | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle | VARCHAR | Sí |  |  |  |
| descuenta_en | VARCHAR | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 17923 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| TPV.frm | 35756 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| Lista_Pedidos_OPT.frm | 2830 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| FacturaB.frm | 24669 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| NotaCred_SinCompO.frm | 14829 | SELECT | "From En_abm " & _ |
| NotaCred_SinCompO.frm | 14835 | JOIN | "INNER JOIN en_abm ON (en_abm.id_en_abm = articulo.id_en_abm… |
| FacturaA.frm | 21219 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| En_GestionOE.frm | 1560 | JOIN | "RIGHT OUTER JOIN en_abm ON (en_abm.id_en_abm = en_orden_ren… |
| Remito.frm | 12656 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| En_CargaOE_ArtE.frm | 599 | SELECT | "From En_abm " & _ |
| En_abm.frm | 855 | JOIN | " RIGHT JOIN en_abm ON (en_abm.id_en_abm=articulo.id_en_abm)… |
| En_abm.frm | 862 | SELECT | " FROM en_abm " & _ |
| En_abm.frm | 872 | SELECT | DataArtEn.RecordSource = "SELECT en_abm.* FROM en_abm WHERE … |
| En_abm.frm | 1141 | SELECT | rs_detalle.Open "SELECT detalle from en_abm WHERE id_en_abm … |
| Visualiza_En_GeneraOE.frm | 5686 | JOIN | "RIGHT JOIN en_abm ON (en_abm.id_en_abm = en_orden_renglon.i… |
| Visualiza_En_GeneraOE.frm | 5692 | JOIN | "RIGHT JOIN en_abm ON (en_abm.id_en_abm = en_orden_renglon.i… |
| En_CargaAbm.frm | 357 | SELECT | 'rs_EnArt.Open "SELECT * FROM en_abm WHERE Nombre_en_abm = '… |
| En_CargaAbm.frm | 373 | SELECT | 'rs_EnArt.Open "SELECT * FROM en_abm WHERE  id_en_abm = 0", … |
| En_CargaAbm.frm | 413 | SELECT | rs_EnArt.Open "SELECT * FROM en_abm WHERE  id_en_abm = 0", c… |
| En_CargaAbm.frm | 461 | SELECT | '                En_abm.DataArtEn.RecordSource = "SELECT en_… |
| En_CargaAbm.frm | 487 | SELECT | rs_EnArt.Open "SELECT * FROM en_abm WHERE id_en_abm = " & id… |
| En_CargaAbm.frm | 543 | SELECT | '            En_abm.DataArtEn.RecordSource = "SELECT en_abm.… |
| En_abmDef.frm | 809 | UPDATE | conn.Execute "UPDATE en_abm SET detalle = '" & Detalle.Text … |
| En_abmDef.frm | 935 | UPDATE | conn.Execute "UPDATE en_abm SET detalle = '" & Detalle.Text … |
| En_abmDef.frm | 1036 | SELECT | En_abm.DataArtEn.RecordSource = "SELECT en_abm.*, articulo.I… |
| En_abm2.frm | 657 | SELECT | DataArtEn.RecordSource = "SELECT * FROM en_abm WHERE Nombre_… |
| CargaMovStock.frm | 6313 | SELECT | "From En_abm " & _ |
| CargaMovStock.frm | 8157 | SELECT | '                                "FROM En_abm " & _ |
| CargaMovStock.frm | 8168 | JOIN | "RIGHT JOIN en_abm ON (en_abm.id_en_abm = articulo.id_en_abm… |
| CargaMovStock.frm | 8177 | JOIN | "RIGHT JOIN en_abm ON (en_abm.id_en_abm = articulo.id_en_abm… |
| CargaMovStock.frm | 8626 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| TPV_2.frm | 33206 | SELECT | rs_enVta.Open "SELECT descuenta_en FROM en_abm " & _ |
| Principal.frm | 7665 | JOIN | " LEFT JOIN en_abm AS ensamblado ON ensamblado.id_en_abm=for… |
| Visualiza.bas | 8132 | JOIN | "RIGHT OUTER JOIN en_abm ON (en_abm.id_en_abm = en_orden_ren… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)