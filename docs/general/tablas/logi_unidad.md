# Tabla `logi_unidad`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_unidad | DOUBLE | No | ✓ |  |  |
| nombre_unidad | VARCHAR | Sí |  |  |  |
| patente_unidad | VARCHAR | No |  |  |  |
| limite_carga_peso | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |

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
| Stock_Control_Entrada.frm | 664 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Pedido_prep_consulta.frm | 1691 | JOIN | '                                    "LEFT JOIN logi_unidad … |
| Pedido_prep_consulta.frm | 1756 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Logi_Info.frm | 1324 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Stock_Control.frm | 1650 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Pedido_prep.frm | 4109 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Pedido_prep.frm | 5408 | SELECT | rs_vehiculo.Open "SELECT * FROM logi_unidad WHERE id_unidad … |
| Logi_CargaRuta.frm | 1975 | SELECT | data_unidad.RecordSource = "SELECT id_unidad, nombre_unidad … |
| Pedido_Avanzado.frm | 3466 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Indicadores.frm | 816 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| ConsultaComprobante.frm | 4236 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Logi_ABMUnidad.frm | 479 | SELECT | DataUnidad.RecordSource = "SELECT * FROM logi_unidad WHERE n… |
| Logi_ABMUnidad.frm | 513 | SELECT | DataUnidad.RecordSource = "SELECT * FROM logi_unidad ORDER B… |
| Logi_OrdenRuta.frm | 708 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Logi_CargaUnidad.frm | 280 | SELECT | rs_uni.Open "SELECT * FROM logi_unidad WHERE patente_unidad … |
| Logi_CargaUnidad.frm | 296 | SELECT | rs_uni.Open "SELECT * FROM logi_unidad WHERE id_unidad = 0",… |
| Logi_CargaUnidad.frm | 313 | SELECT | Logi_ABMUnidad.DataUnidad.RecordSource = "SELECT * FROM logi… |
| Logi_CargaUnidad.frm | 324 | SELECT | rs_uni.Open "SELECT * FROM logi_unidad WHERE id_unidad = " &… |
| Logi_CargaUnidad.frm | 340 | SELECT | Logi_ABMUnidad.DataUnidad.RecordSource = "SELECT * FROM logi… |
| Lista_Comp_Fact.frm | 2359 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| ml_sincronizacion.frm | 1403 | JOIN | '                            "LEFT JOIN logi_unidad ON (logi… |
| Geolocalizacion_Comprobante.frm | 1935 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Geolocalizacion_Cliente.frm | 1702 | JOIN | "LEFT JOIN logi_unidad ON (logi_unidad.id_unidad = logi_hoja… |
| Cot.bas | 420 | SELECT | rsT.Open "SELECT patente_unidad FROM logi_unidad " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)