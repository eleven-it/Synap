# Tabla `crm_cliente_interes`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_crm_ci | DOUBLE | No | ✓ |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_cliente_potencial | DOUBLE | Sí |  |  |  |
| id_intereses | DOUBLE | Sí |  |  |  |

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
| Crm_VisualizaInt.frm | 270 | SELECT | "FROM crm_cliente_interes " & _ |
| Crm_VisualizaInt.frm | 280 | SELECT | "FROM crm_cliente_interes " & _ |
| Crm_CargaCliPot.frm | 1924 | UPDATE | conn.Execute "UPDATE crm_cliente_interes " & _ |
| Crm_AbmCli_Int.frm | 403 | SELECT | "FROM crm_cliente_interes " & _ |
| Crm_AbmCli_Int.frm | 437 | SELECT | "FROM crm_cliente_interes " & _ |
| Crm_AbmCli_Int.frm | 628 | SELECT | "From crm_cliente_interes " & _ |
| Crm_AbmCli_Int.frm | 643 | SELECT | "From crm_cliente_interes " & _ |
| Crm_AsignaCli_Interes.frm | 939 | SELECT | rs_cliInt.Open "SELECT * FROM crm_cliente_interes WHERE " & … |
| Crm_AsignaCli_Interes.frm | 954 | INSERT | conn.Execute "INSERT INTO crm_cliente_interes(" & varI & ", … |
| Crm_AsignaCli_Interes.frm | 965 | SELECT | conn.Execute "DELETE crm_cliente_interes.* FROM crm_cliente_… |
| Crm_AsignaCli_Interes.frm | 968 | INSERT | conn.Execute "INSERT INTO crm_cliente_interes(" & varI & ", … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)