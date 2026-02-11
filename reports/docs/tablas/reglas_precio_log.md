# Tabla `reglas_precio_log`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_regla_precio_log | DOUBLE | No | ✓ |  |  |
| fecha | TIMESTAMP | No |  |  |  |
| tipo_actualizacion | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| descripcion | VARCHAR | Sí |  |  |  |
| alcance | VARCHAR | Sí |  |  |  |
| id_regla_precio | DOUBLE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |

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
| Rprecios_abm.frm | 2703 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_abm.frm | 2717 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_abm.frm | 2732 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_abm.frm | 3054 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| CargaArticulo_Original.frm | 12515 | INSERT | '                        "INSERT INTO reglas_precio_log (fec… |
| Rprecios_alta_art.frm | 2119 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_alta_art.frm | 2128 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_log.frm | 588 | SELECT | "FROM reglas_precio_log " & _ |
| Rprecios_log.frm | 598 | SELECT | "FROM reglas_precio_log " & _ |
| Rprecios_log.frm | 649 | SELECT | '                            "FROM reglas_precio_log " & _ |
| Rprecios_eliminar.frm | 2897 | INSERT | '                            "INSERT INTO reglas_precio_log … |
| Rprecios_eliminar.frm | 2911 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_eliminar.frm | 2923 | INSERT | '                            "INSERT INTO reglas_precio_log … |
| Rprecios_eliminar.frm | 2928 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_eliminar.frm | 2940 | INSERT | '                            "INSERT INTO reglas_precio_log … |
| Rprecios_Masivas.frm | 2407 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (tipo_actualizac… |
| CargaArticulo2.frm | 12421 | INSERT | '                        "INSERT INTO reglas_precio_log (fec… |
| Rprecios_carga.frm | 2543 | INSERT | '          "INSERT INTO reglas_precio_log (fecha, tipo_actua… |
| Rprecios_carga.frm | 2548 | INSERT | '     conn.Execute "INSERT INTO reglas_precio_log (fecha, ti… |
| Rprecios_carga.frm | 2553 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (tipo_actualizac… |
| Rprecios_carga.frm | 2567 | INSERT | '        conn.Execute "INSERT INTO reglas_precio_log (fecha,… |
| Rprecios_carga.frm | 2573 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (tipo_actualizac… |
| CargaArticulo.frm | 14534 | INSERT | '                        "INSERT INTO reglas_precio_log (fec… |
| Carga_Cliente.frm | 7520 | INSERT | '                        "INSERT INTO reglas_precio_log (fec… |
| Rprecios_abm_alta_art.frm | 739 | INSERT | conn.Execute "INSERT INTO reglas_precio_log (fecha, tipo_act… |
| Rprecios_copiar.frm | 938 | INSERT | a = "INSERT INTO reglas_precio_log (fecha, tipo_actualizacio… |
| Rprecios_copiar.frm | 969 | INSERT | a = "INSERT INTO reglas_precio_log (fecha, tipo_actualizacio… |
| CargaArticulo2.frm | 12421 | INSERT | '                        "INSERT INTO reglas_precio_log (fec… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)