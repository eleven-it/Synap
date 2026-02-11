# Tabla `unidmed`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_unimed | INT | No | ✓ |  |  |
| nombre_unimed | VARCHAR | Sí |  |  |  |
| descrip_corta | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |
| modifica | VARCHAR | Sí |  |  |  |

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
| CargaUniMed.frm | 329 | SELECT | rs_unimed.Open "SELECT * FROM unidmed WHERE Nombre_unimed = … |
| CargaUniMed.frm | 345 | SELECT | rs_unimed.Open "SELECT * FROM unidmed where id_unimed <> 1",… |
| CargaUniMed.frm | 362 | SELECT | ABMUniMed.DataUmed.RecordSource = "SELECT * FROM unidmed WHE… |
| CargaUniMed.frm | 373 | SELECT | rs_unimed.Open "SELECT * FROM unidmed WHERE id_unimed = " & … |
| CargaUniMed.frm | 388 | SELECT | ABMUniMed.DataUmed.RecordSource = "SELECT * FROM unidmed ord… |
| PNotaCred.frm | 5087 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Erp_Carga_Parte_Diario.frm | 3883 | JOIN | " LEFT JOIN unidmed as umed ON rec.`id_unimed` = umed.`id_un… |
| ABMUniMed.frm | 459 | SELECT | consulta = "SELECT * FROM unidmed WHERE Nombre_unimed LIKE '… |
| ABMUniMed.frm | 461 | SELECT | consulta = "SELECT * FROM unidmed WHERE anulado = 'No' AND  … |
| ABMUniMed.frm | 508 | SELECT | 'DataUmed.RecordSource = "select * from unidmed order by Nom… |
| Articulo_Carga_datos_adicional.frm | 2222 | SELECT | "FROM unidmed WHERE anulado='No'" |
| AsigProvArt.frm | 1142 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo_prov.id_… |
| FacturaB_COPIA.frm | 7462 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaB_COPIA.frm | 7485 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaB_COPIA.frm | 7504 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| FacturaB_COPIA.frm | 9615 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| TPV.frm | 13695 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| TPV.frm | 16368 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| TPV.frm | 16391 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| TPV.frm | 16410 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| AsigProvArt_Carga.frm | 1207 | SELECT | "From unidmed where anulado='No'" |
| Visualiza_Pedido.frm | 5348 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Visualiza_Pedido.frm | 5367 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Visualiza_Pedido.frm | 7640 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| CargaArticulo_Original.frm | 8675 | SELECT | rs_unimed.Open "SELECT * FROM unidmed WHERE anulado = 'No' "… |
| ABMArticulo_seleccion.frm | 3461 | JOIN | " LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unim… |
| ABMArticulo_seleccion.frm | 3485 | JOIN | " LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unim… |
| Articulo.frm | 3632 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 4023 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 4411 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 4787 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 5165 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 5815 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 6133 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo.frm | 10716 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 10739 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 10758 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Articulo.frm | 12572 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 12593 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 12612 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Articulo.frm | 13579 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 13600 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 13619 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Articulo.frm | 14581 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 14602 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 14621 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Articulo.frm | 15580 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 15601 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 15620 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Articulo.frm | 16535 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 16556 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| Articulo.frm | 16575 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| Visualiza_POrden_Compra.frm | 5584 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Articulo_FormulacionNom.frm | 4070 | SELECT | "From unidmed where anulado='No'" |
| Articulo_FormulacionNom.frm | 4083 | SELECT | "From unidmed where anulado='No'" |
| PRemito.frm | 5794 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Lista_Confeccion_OC_Gral.frm | 1101 | JOIN | " LEFT JOIN unidmed ON (unidmed.id_unimed = articulo_prov.id… |
| ABM_ImpuestoInterno.frm | 431 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = impuesto_interno_… |
| FacturaB.frm | 12502 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaB.frm | 12525 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaB.frm | 12544 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| FacturaB.frm | 15055 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| NotaCred_SinCompO.frm | 9351 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| FacturaA.frm | 7949 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaA.frm | 7973 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo.id_unime… |
| FacturaA.frm | 7993 | JOIN | "LEFT JOIN unidMed ON (unidMed.id_unimed = articulo_prov.id_… |
| FacturaA.frm | 10771 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| CargaArticuloProv.frm | 1039 | SELECT | "From unidmed where anulado='No'" |
| stock_consulta_avanzada.frm | 2068 | JOIN | " LEFT JOIN unidmed ON (unidmed.id_unimed = articulo_prov.id… |
| Exportacion.frm | 8090 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8102 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8144 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8156 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8363 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8375 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8417 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 8429 | JOIN | "LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unime… |
| Exportacion.frm | 9514 | SELECT | "FROM unidmed " & _ |
| IMP_Precios_Excel.frm | 609 | SELECT | data_excel.RecordSource = "SELECT id_unimed,nombre_unimed FR… |
| ABMArticulo_seleccion_simple.frm | 2055 | JOIN | " LEFT JOIN unidmed ON (unidmed.id_unimed = articulo.id_unim… |
| … | … | … | *(102 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)