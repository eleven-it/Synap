# Tabla `imp_fiscal`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_imp_fiscal | INT | No | ✓ |  |  |
| modelo_imp_fiscal | VARCHAR | Sí |  |  |  |
| codigo_modelo_imp_fiscal | VARCHAR | Sí |  |  |  |
| marca_imp_fiscal | VARCHAR | Sí |  |  |  |
| id_codigo_modelo_imp_fiscal | INT | Sí |  |  |  |
| tipo_imp_fiscal | VARCHAR | Sí |  |  |  |

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
| Proceso_Fiscal.frm | 1730 | SELECT | rs_consulta_if.Open "SELECT * FROM imp_fiscal WHERE " & _ |
| Proceso_Fiscal.frm | 2009 | SELECT | '     rs_consulta_if.Open "SELECT * FROM imp_fiscal WHERE " … |
| Proceso_Fiscal.frm | 2171 | SELECT | rs_consulta_if.Open "SELECT * FROM imp_fiscal WHERE " & _ |
| Configuracion2.frm | 5337 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion2.frm | 5588 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion.frm | 5436 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion.frm | 5687 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| IngresoUsuario.frm | 3503 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3569 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3634 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3726 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3791 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3852 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3932 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 3992 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 4056 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| IngresoUsuario.frm | 4176 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Proceso_Fiscal_Conf.frm | 1327 | SELECT | rs_consulta_if.Open "SELECT * FROM imp_fiscal WHERE " & _ |
| Proceso_Fiscal_Conf.frm | 1591 | SELECT | rs_consulta_if.Open "SELECT * FROM imp_fiscal WHERE " & _ |
| Configuracion_COPIA.frm | 4835 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion_COPIA.frm | 4993 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion.frm | 5783 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Configuracion.frm | 5941 | SELECT | data_mod_imp_fiscal.RecordSource = "SELECT * FROM imp_fiscal… |
| Funciones.bas | 10270 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10336 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10401 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10479 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10544 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10591 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10671 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10731 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10781 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |
| Funciones.bas | 10848 | SELECT | .Source = "SELECT * FROM imp_fiscal WHERE id_imp_fiscal = " … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)