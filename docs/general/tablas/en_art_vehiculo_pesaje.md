# Tabla `en_art_vehiculo_pesaje`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_art_vehiculo_pesaje | BIGINT | No | ✓ |  |  |
| id_pesaje | BIGINT | Sí |  |  |  |
| CodMovPesaje | BIGINT | Sí |  |  |  |
| id_en_vehiculo | BIGINT | Sí |  |  |  |
| id_art_bin | BIGINT | Sí |  |  |  |
| peso_art_unidad | DECIMAL | Sí |  |  |  |
| capacidad_art_unidad | DECIMAL | Sí |  |  |  |
| cantidad | DECIMAL | Sí |  |  |  |
| peso_art_total | DECIMAL | Sí |  |  |  |
| capacidad_art_total | DECIMAL | Sí |  |  |  |
| nro_cod_barra_art | VARCHAR | Sí |  |  |  |
| nombre_bin | VARCHAR | Sí |  |  |  |
| CodMovVale | BIGINT | Sí |  |  |  |
| id_vale | BIGINT | Sí |  |  |  |

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
| En_Carga_Pesaje.frm | 5237 | SELECT | rs_pesaje_bines_vehiculo.Open "SELECT * FROM en_art_vehiculo… |
| En_Carga_Pesaje.frm | 5461 | JOIN | "LEFT JOIN en_art_vehiculo_pesaje AS av On av.id_en_vehiculo… |
| En_Carga_Vale.frm | 4317 | SELECT | rs_pesaje_bines_vehiculo.Open "SELECT * FROM en_art_vehiculo… |
| En_Carga_Vale.frm | 4755 | JOIN | "LEFT JOIN en_art_vehiculo_pesaje AS av On av.id_en_vehiculo… |
| En_Carga_Vale.frm | 5741 | SELECT | " FROM en_art_vehiculo_pesaje AS bb" & _ |
| Informes.bas | 4267 | SELECT | " FROM en_art_vehiculo_pesaje AS bin" & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)