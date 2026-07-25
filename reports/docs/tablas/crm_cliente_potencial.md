# Tabla `crm_cliente_potencial`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cliente_potencial | DOUBLE | No | ✓ |  |  |
| id_intereses | DOUBLE | Sí |  |  |  |
| id_cliente_fijo | DOUBLE | Sí |  |  |  |
| id_departamento_cp | DOUBLE | Sí |  |  |  |
| id_provincia_cp | DOUBLE | Sí |  |  |  |
| id_distrito_cp | DOUBLE | Sí |  |  |  |
| id_zona | DOUBLE | Sí |  |  |  |
| nombre_cp | VARCHAR | Sí |  |  |  |
| apellido_cp | VARCHAR | Sí |  |  |  |
| cargo_cp | VARCHAR | Sí |  |  |  |
| telefono_cp | VARCHAR | Sí |  |  |  |
| celular_cp | VARCHAR | Sí |  |  |  |
| email_cp | VARCHAR | Sí |  |  |  |
| descripcion_cp | VARCHAR | Sí |  |  |  |
| tipo_cliente | VARCHAR | Sí |  |  |  |
| nro_calle_cp | INT | Sí |  |  |  |
| nombre_calle_cp | VARCHAR | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| tipo_doc | VARCHAR | Sí |  |  |  |
| id_categoria | DOUBLE | Sí |  |  |  |

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
| Crm_CargaCliPot.frm | 1836 | SELECT | rs_cliente_consulta.Open "SELECT * FROM crm_cliente_potencia… |
| Crm_CargaCliPot.frm | 1916 | UPDATE | conn.Execute "UPDATE crm_cliente_potencial " & _ |
| Crm_CargaCliPot.frm | 1966 | SELECT | rs_cliente.Open "SELECT * FROM crm_cliente_potencial " & _ |
| Crm_CargaCliPot.frm | 1987 | INSERT | conn.Execute "INSERT INTO crm_cliente_potencial " & _ |
| Crm_CargaCliPot.frm | 2005 | INSERT | '        conn.Execute "INSERT INTO crm_cliente_potencial " &… |
| Crm_CargaCliPot.frm | 2022 | SELECT | Crm_CargaLlamada.DataCliP.RecordSource = "SELECT * FROM crm_… |
| Crm_AbmCliPot.frm | 498 | SELECT | "FROM crm_cliente_potencial " & _ |
| Crm_AbmCliPot.frm | 525 | SELECT | "FROM crm_cliente_potencial " & _ |
| Crm_CargaLlamada.frm | 3282 | SELECT | DataCliP.RecordSource = "SELECT * FROM crm_cliente_potencial… |
| Crm_CargaLlamada.frm | 3283 | SELECT | 'DataCliP.RecordSource = "SELECT * FROM crm_cliente_potencia… |
| Crm_CargaLlamada.frm | 3293 | SELECT | "From crm_cliente_potencial " & _ |
| Crm_Info.frm | 1418 | SELECT | DataCliP.RecordSource = "SELECT * FROM crm_cliente_potencial… |
| Crm_AbmLlamada.frm | 674 | JOIN | "LEFT JOIN crm_cliente_potencial ON (crm_cliente_potencial.i… |
| Crm_AbmLlamada.frm | 908 | JOIN | '                                   "LEFT JOIN crm_cliente_p… |
| Crm_AbmLlamada.frm | 922 | JOIN | '                                   "LEFT JOIN crm_cliente_p… |
| Crm_AbmLlamada.frm | 939 | JOIN | '                                       "LEFT JOIN crm_clien… |
| Crm_AbmLlamada.frm | 951 | JOIN | '                                   "LEFT JOIN crm_cliente_p… |
| Crm_AbmCli_Int.frm | 405 | JOIN | "LEFT JOIN crm_cliente_potencial ON (crm_cliente_potencial.i… |
| Crm_AbmCli_Int.frm | 439 | JOIN | "LEFT JOIN crm_cliente_potencial ON (crm_cliente_potencial.i… |
| Crm_Presupuesto_Llamada.frm | 852 | JOIN | Sql = Sql & " LEFT JOIN crm_cliente_potencial ON (crm_client… |
| Crm_BusquedaCli.frm | 538 | SELECT | "From crm_cliente_potencial " & _ |
| Crm_AsignaCli_Interes.frm | 1017 | SELECT | DataCliP.RecordSource = "SELECT * FROM crm_cliente_potencial… |
| Crm_Historial.frm | 458 | JOIN | "LEFT JOIN crm_cliente_potencial ON (crm_cliente_potencial.i… |
| Visualiza.bas | 8755 | JOIN | sql_llamada = sql_llamada & " LEFT JOIN crm_cliente_potencia… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)