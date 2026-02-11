# Tabla `ecom_caract`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ecom_caract | BIGINT | No | ✓ |  |  |
| id_ecom_caract_plantilla | BIGINT | Sí |  |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| valor_ecom_caract | LONGTEXT | Sí |  |  |  |
| valor_ecom_caract_json | LONGTEXT | Sí |  |  |  |

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
| ecom_caract_datos.frm | 575 | JOIN | "LEFT JOIN ecom_caract ON (ecom_caract.id_ecom_caract_planti… |
| ecom_caract_datos.frm | 843 | SELECT | rs.Open "SELECT * FROM ecom_caract " & _ |
| ecom_caract_datos.frm | 850 | INSERT | conn.Execute "INSERT INTO ecom_caract (id_ecom_caract_planti… |
| ecom_caract_datos.frm | 855 | UPDATE | conn.Execute "UPDATE ecom_caract " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)