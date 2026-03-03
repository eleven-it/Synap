# Tabla `permiso_sistema`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_permiso_sistema | BIGINT | No | ✓ |  |  |
| key_permiso | VARCHAR | Sí |  |  |  |
| nombre_permiso | VARCHAR | Sí |  |  |  |
| detalle_permiso | VARCHAR | Sí |  |  |  |
| grupo_permiso | VARCHAR | Sí |  |  |  |
| tipo_permiso | VARCHAR | Sí |  |  |  |
| default_permiso | VARCHAR | Sí |  |  |  |
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
| CargaPuesto.frm | 957 | SELECT | " FROM `permiso_sistema` " |
| CargaPermiso_Sistema_Puesto.frm | 3457 | SELECT | '    data_permiso_sistema.RecordSource = "SELECT permiso_sis… |
| CargaPermiso_Sistema_Puesto.frm | 3464 | JOIN | '    "LEFT JOIN permiso_sistema ON (permiso_sistema.id_permi… |
| Funciones.bas | 2005 | SELECT | sql = "SELECT SQL_NO_CACHE s.id_permiso_sistema as id_permis… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)