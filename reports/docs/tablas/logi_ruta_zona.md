# Tabla `logi_ruta_zona`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ruta_zona | DOUBLE | No | ✓ |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| id_zona | DOUBLE | Sí |  |  |  |

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
| Logi_ABMRuta.frm | 520 | SELECT | "From logi_ruta_zona " & _ |
| Logi_ABMRuta.frm | 533 | SELECT | "From logi_ruta_zona " & _ |
| Logi_ABMRuta.frm | 763 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_ABMRuta.frm | 783 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Stock_Control_Entrada.frm | 662 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Pedido_prep_consulta.frm | 1690 | JOIN | '                                    "LEFT JOIN logi_ruta_zo… |
| Pedido_prep_consulta.frm | 1755 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = prepp… |
| Logi_Gestion2.frm | 4829 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion2.frm | 4850 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion2.frm | 5402 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Info.frm | 1322 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion.frm | 6056 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion.frm | 6081 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion.frm | 6641 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_Gestion.frm | 6668 | JOIN | '                            "LEFT JOIN logi_ruta_zona ON (l… |
| Carga_DatosAdicionales.frm | 1542 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Carga_DatosAdicionales.frm | 1716 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Carga_DatosAdicionales.frm | 1902 | SELECT | '                                           "FROM logi_ruta_… |
| Carga_DatosAdicionales.frm | 1975 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Stock_Control.frm | 1648 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Pedido_prep.frm | 4107 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_CargaRuta.frm | 1771 | INSERT | conn.Execute "INSERT INTO logi_ruta_zona(id_ruta, id_zona) "… |
| Logi_CargaRuta.frm | 1889 | SELECT | conn.Execute "DELETE logi_ruta_zona.* FROM logi_ruta_zona WH… |
| Logi_CargaRuta.frm | 1891 | INSERT | conn.Execute "INSERT INTO logi_ruta_zona(id_ruta, id_zona) "… |
| Pedido_Avanzado.frm | 3464 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Indicadores.frm | 814 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| ConsultaComprobante.frm | 4234 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Logi_OrdenRuta.frm | 706 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Lista_Comp_Fact.frm | 2357 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| ml_sincronizacion.frm | 1401 | JOIN | '                            "LEFT JOIN logi_ruta_zona ON (l… |
| Geolocalizacion_Comprobante.frm | 1933 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Geolocalizacion_Cliente.frm | 1700 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Carga_Datos_Comprobante.frm | 527 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Visualiza_DatosAdicionales.frm | 1625 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |
| Visualiza_DatosAdicionales.frm | 2539 | JOIN | "LEFT JOIN logi_ruta_zona ON (logi_ruta_zona.id_ruta = logi_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)