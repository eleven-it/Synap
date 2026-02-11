# Tabla `logi_ruta_chofer`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ruta_chofer | DOUBLE | No | ✓ |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| id_chofer | INT | Sí |  |  |  |

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
| Logi_ABMRuta.frm | 561 | SELECT | "From logi_ruta_chofer " & _ |
| Logi_ABMRuta.frm | 574 | SELECT | "From logi_ruta_chofer " & _ |
| Pedido_prep_consulta.frm | 1689 | JOIN | '                                    "LEFT JOIN logi_ruta_ch… |
| Pedido_prep_consulta.frm | 1754 | JOIN | "LEFT JOIN logi_ruta_chofer ON (logi_ruta_chofer.id_ruta = p… |
| Logi_CargaRuta.frm | 1779 | INSERT | conn.Execute "INSERT INTO logi_ruta_chofer(id_ruta, id_chofe… |
| Logi_CargaRuta.frm | 1900 | SELECT | conn.Execute "DELETE logi_ruta_chofer.* FROM logi_ruta_chofe… |
| Logi_CargaRuta.frm | 1902 | INSERT | conn.Execute "INSERT INTO logi_ruta_chofer(id_ruta, id_chofe… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)