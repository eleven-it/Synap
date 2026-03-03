# Tabla `error`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_error | INT | No | ✓ |  |  |
| fecha_error | DATE | Sí |  |  |  |
| detalle_error | LONGTEXT | Sí |  |  |  |
| ventana_error | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| nro_error | INT | Sí |  |  |  |
| hora_error | TIMESTAMP | No |  |  |  |

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
| LogError.frm | 551 | SELECT | DataError.RecordSource = "SELECT error.*, usuarios.id_usuari… |
| LogError.frm | 558 | SELECT | DataError.RecordSource = "SELECT error.*, usuarios.id_usuari… |
| Principal.frm | 7128 | SELECT | rs_error.Open "select * from error where id_error = 0", conn… |
| Funciones.bas | 8500 | SELECT | rs_error.Open "select * from error where id_error = 0", conn… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)