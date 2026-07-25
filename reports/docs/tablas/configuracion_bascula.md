# Tabla `configuracion_bascula`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_configuracion_bascula | INT | No | ✓ |  |  |
| puerto | INT | Sí |  |  |  |
| baudios | BIGINT | Sí |  |  |  |
| bits_datos | INT | Sí |  |  |  |
| bits_stop | INT | Sí |  |  |  |
| paridad | VARCHAR | Sí |  |  |  |

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
| Carga_Unidad_Peso.frm | 1077 | SELECT | rs_configuracion_bascula.Open "SELECT * FROM configuracion_b… |
| Configuracion_Carga_Bascula.frm | 270 | SELECT | rs_configuracion_bascula.Open "SELECT * FROM configuracion_b… |
| Configuracion_Carga_Bascula.frm | 324 | SELECT | rs_configuracion_bascula.Open "SELECT * FROM configuracion_b… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)