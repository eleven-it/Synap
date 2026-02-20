# Tabla `ecom_caract_plantilla`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ecom_caract_plantilla | BIGINT | No | ✓ |  |  |
| nombre_caract_plantilla | VARCHAR | Sí |  |  |  |
| datos_caract_plantilla | LONGTEXT | Sí |  |  |  |
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
| ecom_carga_caract_plantilla.frm | 563 | SELECT | "FROM ecom_caract_plantilla " |
| ecom_carga_caract_plantilla.frm | 761 | UPDATE | conn.Execute "UPDATE ecom_caract_plantilla " & _ |
| ecom_caract_plantilla.frm | 363 | SELECT | DataListaPA.RecordSource = "select *  from ecom_caract_plant… |
| ecom_caract_plantilla.frm | 392 | SELECT | DataListaPA.RecordSource = "select * from ecom_caract_planti… |
| ecom_plantilla.frm | 242 | SELECT | rs.Open "SELECT * FROM ecom_caract_plantilla WHERE nombre_ca… |
| ecom_plantilla.frm | 258 | SELECT | rs.Open "SELECT * FROM ecom_caract_plantilla WHERE id_ecom_c… |
| ecom_plantilla.frm | 273 | SELECT | ecom_caract_plantilla.DataListaPA.RecordSource = "SELECT * F… |
| ecom_plantilla.frm | 284 | SELECT | rs.Open "SELECT * FROM ecom_caract_plantilla WHERE id_ecom_c… |
| ecom_plantilla.frm | 297 | SELECT | ecom_caract_plantilla.DataListaPA.RecordSource = "SELECT * F… |
| ecom_datos_articulo.frm | 3058 | SELECT | DataCarac.RecordSource = "SELECT * FROM ecom_caract_plantill… |
| ecom_caract_datos.frm | 574 | SELECT | "FROM ecom_caract_plantilla  " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)