# Tabla `permisos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_permisos | DOUBLE | No | ✓ |  |  |
| Clavemenu | VARCHAR | Sí |  |  |  |
| IDpuesto | VARCHAR | Sí |  |  |  |
| Permiso | VARCHAR | Sí |  |  |  |

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
| ABMPuesto.frm | 847 | SELECT | DataPermisos.RecordSource = "select * from permisos where ID… |
| ABMPuesto.frm | 1011 | SELECT | DataPermisos.RecordSource = "select * from permisos WHERE ID… |
| ABMPuesto.frm | 1022 | SELECT | DataPermisos.RecordSource = "select * from permisos where ID… |
| CargaPuesto.frm | 521 | SELECT | DataPermisos.RecordSource = "select * from permisos" |
| CargaPuesto.frm | 524 | SELECT | rs_permisos.Open "SELECT * FROM permisos where Clavemenu = '… |
| CargaPuesto.frm | 622 | SELECT | conn.Execute "delete from permisos where IDpuesto = " & vIDp… |
| CargaPuesto.frm | 622 | DELETE | conn.Execute "delete from permisos where IDpuesto = " & vIDp… |
| CargaPuesto.frm | 635 | INSERT | conn.Execute "INSERT INTO permisos(IDpuesto,Permiso,Clavemen… |
| CargaPuesto.frm | 1014 | INSERT | conn.Execute "INSERT INTO `permisos` (`Clavemenu`, `Permiso`… |
| CargaPuesto.frm | 1018 | SELECT | " FROM `permisos` WHERE IDpuesto = " & Puesto_Base.BoundText… |
| CargaPuesto.frm | 1458 | SELECT | DataPermisos.RecordSource = "select * from permisos where ID… |
| CargaPuesto.frm | 1462 | SELECT | DataPermisos.RecordSource = "select * from permisos where ID… |
| Principal.frm | 5718 | SELECT | .Source = "SELECT  * FROM permisos WHERE idpuesto=" & idpues… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)