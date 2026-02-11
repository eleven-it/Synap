# Tabla `menurapido`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_menurapido | INT | No | ✓ |  |  |
| grupo_menurapido | VARCHAR | Sí |  |  |  |
| index_grupo | INT | Sí |  |  |  |
| nombre_menurapido | VARCHAR | Sí |  |  |  |
| key_item | VARCHAR | Sí |  |  |  |
| index_item | INT | Sí |  |  |  |
| id_icono | INT | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| activo | INT | Sí |  |  |  |
| id_menurapido_conf | INT | Sí |  |  |  |

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
| CargaPuesto.frm | 930 | INSERT | conn.Execute "INSERT INTO `menurapido` (`id_menurapido_conf`… |
| CargaPuesto.frm | 985 | INSERT | conn.Execute "INSERT INTO `menurapido` (`grupo_menurapido`, … |
| CargaPuesto.frm | 994 | SELECT | " FROM `menurapido` WHERE id_puesto = " & Puesto_Base.BoundT… |
| CargaPermiso_Sistema_Puesto.frm | 3538 | SELECT | Data_Menu_Rapido.RecordSource = "SELECT * FROM menurapido WH… |
| Principal.frm | 2549 | SELECT | .Source = "SELECT * FROM menurapido WHERE " & _ |
| CargaPermiso_Sistema.frm | 4656 | SELECT | Data_Menu_Rapido.RecordSource = "SELECT * FROM menurapido WH… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)