# Tabla `permiso_sistema_puesto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_permiso_sistema_puesto | BIGINT | No | ✓ |  |  |
| id_permiso_sistema | BIGINT | Sí |  |  |  |
| key_permiso | VARCHAR | Sí |  |  |  |
| valor_permiso | VARCHAR | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |

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
| CargaPermiso_Sistema_Puesto_Valor.frm | 543 | SELECT | rs_actualizar.Open "SELECT * FROM permiso_sistema_puesto WHE… |
| CargaPermiso_Sistema_Puesto_Valor.frm | 693 | SELECT | rs_actualizar.Open "SELECT * FROM permiso_sistema_puesto WHE… |
| CargaPermiso_Sistema_Puesto_Valor.frm | 722 | UPDATE | Debug.Print "UPDATE permiso_sistema_puesto SET permiso_siste… |
| CargaPermiso_Sistema_Puesto_Valor.frm | 723 | UPDATE | conn.Execute "UPDATE permiso_sistema_puesto SET permiso_sist… |
| IngresoUsuario.frm | 2598 | SELECT | "FROM permiso_sistema_puesto,permiso_sistema " & _ |
| CargaPuesto.frm | 952 | INSERT | conn.Execute "INSERT INTO `permiso_sistema_puesto` (`id_perm… |
| CargaPuesto.frm | 1006 | INSERT | conn.Execute "INSERT INTO `permiso_sistema_puesto` (`id_perm… |
| CargaPuesto.frm | 1011 | SELECT | " FROM `permiso_sistema_puesto` WHERE id_puesto = " & Puesto… |
| CargaPermiso_Sistema_Puesto.frm | 3446 | SELECT | sql_permiso_sistema = sql_permiso_sistema & " FROM permiso_s… |
| CargaPermiso_Sistema_Puesto.frm | 3458 | JOIN | '    "LEFT JOIN permiso_sistema_puesto ON (permiso_sistema_p… |
| CargaPermiso_Sistema_Puesto.frm | 3463 | SELECT | '    data_permiso_sistema.RecordSource = "SELECT permiso_sis… |
| Funciones.bas | 2006 | JOIN | "LEFT JOIN permiso_sistema_puesto p ON (p.id_permiso_sistema… |
| Funciones.bas | 2021 | INSERT | InX = "INSERT INTO permiso_sistema_puesto SET " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)