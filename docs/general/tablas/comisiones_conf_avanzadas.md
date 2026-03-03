# Tabla `comisiones_conf_avanzadas`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_conf | INT | No | ✓ |  |  |
| codViajante | INT | No |  |  |  |
| tipo_comision | VARCHAR | No |  |  |  |
| codigo_referencia | INT | No |  |  |  |
| porcentaje | DECIMAL | No |  |  |  |
| tipo_calculo | VARCHAR | No |  |  |  |
| incluir_impuestos | TINYINT | Sí |  |  |  |

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
| Liq_Carga_Comision_avanzada.frm | 472 | INSERT | Sql = "INSERT INTO comisiones_conf_avanzadas (codViajante, t… |
| Liq_Carga_Comision_avanzada.frm | 497 | SELECT | "FROM comisiones_conf_avanzadas c " & _ |
| Liq_Carga_Comision_avanzada.frm | 555 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_Comision_avanzada.frm | 555 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_Comision_avanzada.frm | 569 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE id_… |
| Liq_Carga_Comision_avanzada.frm | 569 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE id_… |
| Liq_Carga_Comision_avanzada.frm | 855 | SELECT | "FROM comisiones_conf_avanzadas c " & _ |
| Liq_Carga_Comision_avanzada.frm | 918 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_Comision_avanzada.frm | 918 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_Comision_avanzada.frm | 940 | INSERT | sqlInsert = "INSERT INTO comisiones_conf_avanzadas (codViaja… |
| Liq_Carga_Comision_avanzada.frm | 957 | SELECT | Sql = "SELECT id_conf FROM comisiones_conf_avanzadas WHERE c… |
| Liq_Carga_Comision_avanzada.frm | 965 | UPDATE | sqlUpdate = "UPDATE comisiones_conf_avanzadas SET porcentaje… |
| Liq_Carga_Comision_avanzada.frm | 1048 | SELECT | rs.Open "SELECT * FROM comisiones_conf_avanzadas WHERE id_co… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 720 | SELECT | "  FROM comisiones_conf_avanzadas " & _ |
| Liq_Carga_ComisionAvanzada.frm | 784 | INSERT | sql = "INSERT INTO comisiones_conf_avanzadas (codViajante, t… |
| Liq_Carga_ComisionAvanzada.frm | 810 | SELECT | "FROM comisiones_conf_avanzadas c " & _ |
| Liq_Carga_ComisionAvanzada.frm | 875 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_ComisionAvanzada.frm | 875 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_ComisionAvanzada.frm | 889 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE id_… |
| Liq_Carga_ComisionAvanzada.frm | 889 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE id_… |
| Liq_Carga_ComisionAvanzada.frm | 1238 | SELECT | "FROM comisiones_conf_avanzadas c " & _ |
| Liq_Carga_ComisionAvanzada.frm | 1318 | SELECT | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_ComisionAvanzada.frm | 1318 | DELETE | sqlDelete = "DELETE FROM comisiones_conf_avanzadas WHERE cod… |
| Liq_Carga_ComisionAvanzada.frm | 1342 | INSERT | sqlInsert = "INSERT INTO comisiones_conf_avanzadas (codViaja… |
| Liq_Carga_ComisionAvanzada.frm | 1363 | SELECT | sql = "SELECT id_conf FROM comisiones_conf_avanzadas WHERE c… |
| Liq_Carga_ComisionAvanzada.frm | 1371 | UPDATE | sqlUpdate = "UPDATE comisiones_conf_avanzadas SET porcentaje… |
| Liq_Carga_ComisionAvanzada.frm | 1481 | SELECT | rs.Open "SELECT * FROM comisiones_conf_avanzadas WHERE id_co… |
| Liq_Impresion_ComisionesAvanzadas.frm | 727 | SELECT | "  FROM comisiones_conf_avanzadas " & _ |
| Liq_ABM_Comision_avanzada.frm | 773 | JOIN | "JOIN comisiones_conf_avanzadas c ON v.CodViajante = c.codVi… |
| Liq_ABM_Comision_avanzada.frm | 1181 | SELECT | "  FROM comisiones_conf_avanzadas " & _ |
| Liq_ABM_Comision_avanzada.frm | 1528 | SELECT | "porcentaje FROM comisiones_conf_avanzadas " & _ |
| Liq_ABM_Comision_avanzada.frm | 1663 | JOIN | sql = sql & "LEFT JOIN comisiones_conf_avanzadas com ON c.Co… |
| Liq_ABM_Comision_avanzada.frm | 1711 | SELECT | "    FROM comisiones_conf_avanzadas " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)