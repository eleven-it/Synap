# Tabla `reporte_flujofondos_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_flujofondo | DOUBLE | No | ✓ |  |  |
| fecha | VARCHAR | Sí |  |  |  |
| imp_caja | DOUBLE | Sí |  |  |  |
| imp_banco | DECIMAL | Sí |  |  |  |
| imp_depcheque | DECIMAL | Sí |  |  |  |
| imp_chequemitido | DECIMAL | Sí |  |  |  |
| imp_cobranza | DECIMAL | Sí |  |  |  |
| imp_gastos | DECIMAL | Sí |  |  |  |
| imp_pagos | DECIMAL | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| imp_otrosingresos | DECIMAL | Sí |  |  |  |
| imp_deuda | DECIMAL | Sí |  |  |  |
| imp_impuesto | DECIMAL | Sí |  |  |  |

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
| Info_Estadistica.frm | 3678 | SELECT | '        conn.Execute "DELETE FROM reporte_flujofondos_temp … |
| Info_Estadistica.frm | 3678 | DELETE | '        conn.Execute "DELETE FROM reporte_flujofondos_temp … |
| Info_Estadistica.frm | 3778 | INSERT | '                        conn.Execute "INSERT INTO reporte_f… |
| Info_Estadistica.frm | 3791 | UPDATE | '                        conn.Execute "UPDATE reporte_flujof… |
| Info_Estadistica.frm | 3798 | SELECT | '                                             "From reporte_… |
| Info_Estadistica.frm | 3803 | UPDATE | '                            conn.Execute "UPDATE reporte_fl… |
| Info_Estadistica.frm | 3823 | UPDATE | '                        conn.Execute "Update reporte_flujof… |
| Info_Estadistica.frm | 3833 | UPDATE | '                        conn.Execute "Update reporte_flujof… |
| Info_Estadistica.frm | 3843 | UPDATE | '                    conn.Execute "Update reporte_flujofondo… |
| Info_Estadistica.frm | 3852 | UPDATE | '                    conn.Execute "Update reporte_flujofondo… |
| Info_Estadistica.frm | 3940 | SELECT | conn.Execute "DELETE FROM reporte_flujofondos_temp WHERE id_… |
| Info_Estadistica.frm | 3940 | DELETE | conn.Execute "DELETE FROM reporte_flujofondos_temp WHERE id_… |
| Info_Estadistica.frm | 4034 | INSERT | conn.Execute "INSERT INTO reporte_flujofondos_temp (id_usuar… |
| Info_Estadistica.frm | 4047 | UPDATE | conn.Execute "UPDATE reporte_flujofondos_temp SET reporte_fl… |
| Info_Estadistica.frm | 4056 | SELECT | "From reporte_flujofondos_temp WHERE reporte_flujofondos_tem… |
| Info_Estadistica.frm | 4061 | UPDATE | conn.Execute "UPDATE reporte_flujofondos_temp SET reporte_fl… |
| Info_Estadistica.frm | 4077 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4086 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4095 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4107 | UPDATE | conn.Execute " Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4120 | UPDATE | conn.Execute " Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4133 | UPDATE | conn.Execute " Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4144 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Estadistica.frm | 4154 | UPDATE | conn.Execute " Update reporte_flujofondos_temp " & _ |
| Info_Banco.frm | 2768 | SELECT | conn.Execute "DELETE FROM reporte_flujofondos_temp WHERE id_… |
| Info_Banco.frm | 2768 | DELETE | conn.Execute "DELETE FROM reporte_flujofondos_temp WHERE id_… |
| Info_Banco.frm | 2868 | INSERT | conn.Execute "INSERT INTO reporte_flujofondos_temp (id_usuar… |
| Info_Banco.frm | 2881 | UPDATE | conn.Execute "UPDATE reporte_flujofondos_temp SET reporte_fl… |
| Info_Banco.frm | 2888 | SELECT | "From reporte_flujofondos_temp WHERE reporte_flujofondos_tem… |
| Info_Banco.frm | 2893 | UPDATE | conn.Execute "UPDATE reporte_flujofondos_temp SET reporte_fl… |
| Info_Banco.frm | 2913 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Banco.frm | 2923 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Banco.frm | 2933 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Info_Banco.frm | 2942 | UPDATE | conn.Execute "Update reporte_flujofondos_temp " & _ |
| Principal.frm | 6123 | SELECT | conn.Execute "delete from reporte_flujofondos_temp where id_… |
| Principal.frm | 6123 | DELETE | conn.Execute "delete from reporte_flujofondos_temp where id_… |
| Principal.frm | 6189 | SELECT | conn.Execute "delete from reporte_flujofondos_temp where id_… |
| Principal.frm | 6189 | DELETE | conn.Execute "delete from reporte_flujofondos_temp where id_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)