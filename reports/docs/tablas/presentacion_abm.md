# Tabla `presentacion_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_presentacion | DOUBLE | No | ✓ |  |  |
| nombre_presentacion | VARCHAR | Sí |  |  |  |
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
| Articulo_Carga_datos_adicional.frm | 2210 | SELECT | "FROM presentacion_abm WHERE anulado = 'No' " |
| AMBPresentacion.frm | 426 | SELECT | consulta = "SELECT * FROM presentacion_abm WHERE Nombre_pres… |
| AMBPresentacion.frm | 429 | SELECT | consulta = "SELECT * FROM presentacion_abm WHERE anulado = '… |
| AMBPresentacion.frm | 488 | SELECT | ' DataPres.RecordSource = "select * from presentacion_abm or… |
| FacturaB_COPIA.frm | 7486 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| FacturaB_COPIA.frm | 7505 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| TPV.frm | 16392 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| TPV.frm | 16411 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| AsigProvArt_Carga.frm | 1195 | SELECT | "From presentacion_abm " |
| Visualiza_Pedido.frm | 5349 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Visualiza_Pedido.frm | 5368 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| CargaArticulo_Original.frm | 8692 | SELECT | rs_presentacion.Open "SELECT * FROM presentacion_abm WHERE a… |
| Articulo.frm | 10740 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 10759 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 12594 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 12613 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 13601 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 13620 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 14603 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 14622 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 15602 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 15621 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 16557 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo.frm | 16576 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Articulo_FormulacionNom.frm | 4076 | SELECT | "From presentacion_abm " |
| Articulo_FormulacionNom.frm | 4089 | SELECT | "From presentacion_abm where anulado='No'" |
| Lista_Confeccion_OC_Gral.frm | 1100 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| FacturaB.frm | 12526 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| FacturaB.frm | 12545 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| FacturaA.frm | 7974 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| FacturaA.frm | 7994 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| CargaArticuloProv.frm | 1045 | SELECT | "From presentacion_abm where anulado='No'" |
| stock_consulta_avanzada.frm | 2067 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| Remito.frm | 7283 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Remito.frm | 7302 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| CargaArticulo2.frm | 8589 | SELECT | rs_presentacion.Open "SELECT * FROM presentacion_abm WHERE a… |
| TPV_Modifica_Renglon.frm | 1901 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| TPV_Modifica_Renglon.frm | 1921 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Presupuesto.frm | 5402 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Presupuesto.frm | 5421 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Pedido.frm | 5902 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Pedido.frm | 5921 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ActDatos_Articulo.frm | 3927 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| ActDatos_Articulo.frm | 4067 | SELECT | data_presentacion.RecordSource = "SELECT * FROM presentacion… |
| ABMArticulo_Datos_Adicional.frm | 1225 | SELECT | "FROM presentacion_abm WHERE anulado = 'No' " |
| Articulo_Promo_ABM.frm | 611 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| CargaArticulo.frm | 9629 | SELECT | rs_presentacion.Open "SELECT * FROM presentacion_abm WHERE a… |
| CargaPresentacion.frm | 292 | SELECT | rs.Open "SELECT * FROM presentacion_abm WHERE Nombre_present… |
| CargaPresentacion.frm | 308 | SELECT | rs.Open "SELECT * FROM presentacion_abm where id_presentacio… |
| CargaPresentacion.frm | 323 | SELECT | ABMPresentacion.DataPres.RecordSource = "SELECT * FROM prese… |
| CargaPresentacion.frm | 334 | SELECT | rs.Open "SELECT * FROM presentacion_abm WHERE id_presentacio… |
| CargaPresentacion.frm | 348 | SELECT | ABMPresentacion.DataPres.RecordSource = "SELECT * FROM prese… |
| Logi_Renglon.frm | 2408 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Logi_Renglon.frm | 2428 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| VisualizarFichaArt.frm | 2808 | SELECT | rs_pres.Open "SELECT * FROM presentacion_abm WHERE id_presen… |
| VisualizarFichaArt.frm | 2844 | SELECT | rs_presC.Open "SELECT * FROM presentacion_abm WHERE id_prese… |
| Facturacion_Ciclica_Renglon.frm | 2793 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Facturacion_Ciclica_Renglon.frm | 2813 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Visualiza_Presupuesto.frm | 5171 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Visualiza_Presupuesto.frm | 5190 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| TPV_2.frm | 14703 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| TPV_2.frm | 14722 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 3481 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 3748 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 3990 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 4179 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 4357 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 7038 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| ArticuloProv.frm | 7060 | JOIN | "LEFT JOIN presentacion_abm ON (presentacion_abm.id_presenta… |
| Principal.frm | 12601 | JOIN | '                            "LEFT JOIN presentacion_abm AS … |
| Principal.frm | 12602 | JOIN | '                            "LEFT JOIN presentacion_abm AS … |
| Principal.frm | 12713 | SELECT | " FROM presentacion_abm AS presV " & _ |
| Principal.frm | 12740 | SELECT | " FROM presentacion_abm AS presC " & _ |
| Lista_Confeccion_OC.frm | 1278 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| CargaArticulo2.frm | 8589 | SELECT | rs_presentacion.Open "SELECT * FROM presentacion_abm WHERE a… |
| Funciones.bas | 5758 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| Funciones.bas | 6273 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |
| Funciones.bas | 6374 | JOIN | " LEFT JOIN presentacion_abm ON (presentacion_abm.id_present… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)