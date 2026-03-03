# Tabla `crm_intereses`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_intereses | DOUBLE | No | ✓ |  |  |
| descrip_intereses | VARCHAR | Sí |  |  |  |
| id_rubro | DOUBLE | Sí |  |  |  |
| id_sub_rubro | DOUBLE | Sí |  |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_intereses | rubro | Crm_Intereses.frm | 431 | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbreRubro,NombreSubrubro… |
| crm_intereses | subrubro | Crm_Intereses.frm | 431 | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbreRubro,NombreSubrubro… |
| crm_llamada_interes | crm_intereses | Crm_CargaLlamada.frm | 4038 | sql_lista = "SELECT sql_no_cache * from crm_llamada_interes INNER JOIN crm_inter… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Crm_Intereses.frm | 431 | SELECT | sql_lista = " SELECT id_intereses, descrip_intereses, NOmbre… |
| Crm_Intereses.frm | 506 | JOIN | DataIntereses.CommandType = adCmdUnknown                    … |
| Crm_Intereses.frm | 507 | SELECT | DataIntereses.RecordSource = "SELECT * FROM crm_intereses  "… |
| Crm_VisualizaInt.frm | 271 | JOIN | "LEFT JOIN crm_intereses ON (crm_intereses.id_intereses = cr… |
| Crm_VisualizaInt.frm | 281 | JOIN | "LEFT JOIN crm_intereses ON (crm_intereses.id_intereses = cr… |
| Crm_AbmIntereses.frm | 410 | SELECT | "FROM crm_intereses " & _ |
| Crm_AbmIntereses.frm | 440 | SELECT | "FROM crm_intereses " & _ |
| Crm_CargaLlamada.frm | 3343 | SELECT | DataInteres.RecordSource = "SELECT * FROM crm_intereses ORDE… |
| Crm_CargaLlamada.frm | 4038 | JOIN | sql_lista = "SELECT sql_no_cache * from crm_llamada_interes … |
| Crm_Info.frm | 1463 | SELECT | DataIntereses.RecordSource = "SELECT * FROM crm_intereses ;" |
| Crm_AbmCli_Int.frm | 644 | JOIN | "LEFT JOIN crm_intereses ON (crm_intereses.id_intereses = cr… |
| Crm_CargaIntereses.frm | 640 | INSERT | conn.Execute "INSERT INTO crm_intereses (descrip_intereses, … |
| Crm_CargaIntereses.frm | 646 | INSERT | conn.Execute "INSERT INTO crm_intereses (descrip_intereses, … |
| Crm_AsignaCli_Interes.frm | 956 | SELECT | "From crm_intereses " & _ |
| Crm_AsignaCli_Interes.frm | 971 | SELECT | "From crm_intereses " & _ |
| Crm_AsignaCli_Interes.frm | 1023 | SELECT | DataInteres.RecordSource = "SELECT * FROM crm_intereses ORDE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)