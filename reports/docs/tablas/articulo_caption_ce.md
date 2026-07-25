# Tabla `articulo_caption_ce`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_caption_ce | DOUBLE | No | ✓ |  |  |
| caption1 | VARCHAR | Sí |  |  |  |
| caption2 | VARCHAR | Sí |  |  |  |
| caption3 | VARCHAR | Sí |  |  |  |
| caption4 | VARCHAR | Sí |  |  |  |
| caption5 | VARCHAR | Sí |  |  |  |
| caption6 | VARCHAR | Sí |  |  |  |
| caption7 | VARCHAR | Sí |  |  |  |
| caption8 | VARCHAR | Sí |  |  |  |
| caption9 | VARCHAR | Sí |  |  |  |
| caption10 | VARCHAR | Sí |  |  |  |

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
| Articulo_ce.frm | 941 | SELECT | rs_articulo_caption_ce.Open "SELECT * from articulo_caption_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)