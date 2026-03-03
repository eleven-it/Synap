# Tabla `sesion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sesion | DOUBLE | No | ✓ |  |  |
| id_usuario | INT | No |  |  |  |
| id_sucursal | INT | No |  |  |  |
| IP | VARCHAR | No |  |  |  |
| FechaInicio | DATETIME | Sí |  |  |  |
| FechaFin | DATETIME | Sí |  |  |  |

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
| IngresoUsuario.frm | 2057 | UPDATE | '        conn.Execute "UPDATE sesion SET FechaFin = NOW()  W… |
| IngresoUsuario.frm | 2163 | UPDATE | 'update sesion SET fechafin = NOW() where ISNULL(fechafin) a… |
| IngresoUsuario.frm | 2168 | SELECT | .Source = "SELECT * FROM sesion WHERE " & _ |
| IngresoUsuario.frm | 2219 | UPDATE | '                        conn.Execute "UPDATE sesion SET fec… |
| IngresoUsuario.frm | 2244 | INSERT | '            conn.Execute "INSERT INTO sesion(id_usuario,id_… |
| IngresoUsuario.frm | 2258 | INSERT | conn.Execute "INSERT INTO sesion(id_usuario,id_sucursal,fech… |
| IngresoUsuario.frm | 2274 | SELECT | rs_sesion_consulta.Open "SELECT * FROM sesion WHERE " & _ |
| Adm_Sesion.frm | 409 | SELECT | DataSesiones.RecordSource = "SELECT usuarios.cod_usuario, su… |
| Adm_Sesion.frm | 423 | SELECT | DataSesiones.RecordSource = "SELECT * FROM sesion " & _ |
| Adm_Sesion.frm | 435 | SELECT | DataSesiones.RecordSource = "SELECT usuarios.cod_usuario, su… |
| Adm_Sesion.frm | 473 | SELECT | DataSesiones.RecordSource = "SELECT * FROM sesion " & _ |
| Adm_Sesion.frm | 614 | SELECT | rs_sesion.Open "SELECT * FROM sesion " & _ |
| Principal.frm | 2805 | UPDATE | conn.Execute "UPDATE sesion SET fechafin=NOW() WHERE id_sesi… |
| Funciones.bas | 8363 | SELECT | rs_sesion.Open "SELECT * FROM sesion WHERE " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)