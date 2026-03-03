# Tabla `en_vehiculo_vale_art_pesaje`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_vehiculo_vale_art_pesaje | BIGINT | No | ✓ |  |  |
| id_en_art_vehiculo_pesaje | BIGINT | Sí |  |  |  |
| id_vale_vehiculo | BIGINT | Sí |  |  |  |
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
| En_Carga_Pesaje.frm | 5455 | INSERT | conn.Execute "INSERT INTO en_vehiculo_vale_art_pesaje(id_en_… |
| En_Carga_Vale.frm | 4750 | INSERT | conn.Execute "INSERT INTO en_vehiculo_vale_art_pesaje(id_en_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)