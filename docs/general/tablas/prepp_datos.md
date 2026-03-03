# Tabla `prepp_datos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_prepp_datos | BIGINT | No | ✓ |  |  |
| codigo_mov_prepp | DOUBLE | Sí |  |  |  |
| id_ruta | DOUBLE | Sí |  |  |  |
| total_peso_actual | DOUBLE | Sí |  |  |  |
| detalle_prepp | MEDIUMTEXT | Sí |  |  |  |
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
| Pedido_prep_consulta.frm | 1687 | JOIN | '                                    "LEFT JOIN prepp_datos … |
| Pedido_prep_consulta.frm | 1752 | JOIN | "LEFT JOIN prepp_datos ON (prepp_datos.codigo_mov_prepp = pe… |
| Pedido_prep.frm | 3444 | SELECT | rs_prepp_datos.Open "SELECT * FROM prepp_datos WHERE codigo_… |
| Pedido_prep.frm | 3550 | SELECT | rs_valid.Open "SELECT * FROM prepp_datos WHERE id_ruta = " &… |
| Pedido_prep.frm | 3653 | SELECT | rs_prepp_datos.Open "SELECT * FROM prepp_datos WHERE codigo_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)