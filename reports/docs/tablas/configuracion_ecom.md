# Tabla `configuracion_ecom`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_configuracion_ecom | BIGINT | No | ✓ |  |  |
| key_permiso | VARCHAR | Sí |  |  |  |
| nombre_permiso | VARCHAR | Sí |  |  |  |
| detalle_permiso | VARCHAR | Sí |  |  |  |
| grupo_permiso | VARCHAR | Sí |  |  |  |
| tipo_permiso | VARCHAR | Sí |  |  |  |
| valor_permiso | VARCHAR | Sí |  |  |  |
| detalle_valor_permiso | VARCHAR | Sí |  |  |  |

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
| Configuracion_Adicional2.frm | 4186 | SELECT | " FROM configuracion_ecom ORDER By nombre_permiso ASC" |
| Configuracion_Adicional.frm | 4429 | SELECT | " FROM configuracion_ecom ORDER By nombre_permiso ASC" |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)