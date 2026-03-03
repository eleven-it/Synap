# Tabla `crm_pre_llamada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pre_llamada | BIGINT | No | ✓ |  |  |
| CodigoMovimientoPre | BIGINT | Sí |  |  |  |
| id_llamada | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | No |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| crm_pre_llamada | crm_llamada | Crm_CargaLlamada.frm | 3002 | sql_llamada = "SELECT * FROM crm_pre_llamada p INNER JOIN crm_llamada c ON (c.id… |
| comp_ped | crm_pre_llamada | Funciones.bas | 8279 | sql_ped = "SELECT * FROM comp_ped INNER JOIN crm_pre_llamada  ON (crm_pre_llamad… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| trz_trazabilidad.frm | 2809 | JOIN | sql_rc = sql_rc & "INNER JOIN crm_pre_llamada as cpl ON (cpl… |
| trz_trazabilidad.frm | 3243 | JOIN | sql_rc = sql_rc & "INNER JOIN crm_pre_llamada as cpl ON (cpl… |
| Crm_CargaLlamada.frm | 3002 | SELECT | sql_llamada = "SELECT * FROM crm_pre_llamada p INNER JOIN cr… |
| Presupuesto.frm | 3733 | UPDATE | conn.Execute "UPDATE crm_pre_llamada SET CodigoMovimientoPre… |
| Presupuesto.frm | 5835 | SELECT | conn.Execute "DELETE FROM crm_pre_llamada WHERE CodigoMovimi… |
| Presupuesto.frm | 5835 | DELETE | conn.Execute "DELETE FROM crm_pre_llamada WHERE CodigoMovimi… |
| Presupuesto.frm | 6665 | SELECT | 'rs_llamada.Open "SELECT * FROM crm_pre_llamada WHERE Codigo… |
| ConsultaComprobante.frm | 10171 | SELECT | sql_llamada = "SELECT * FROM crm_pre_llamada WHERE CodigoMov… |
| ConsultaComprobante.frm | 10175 | UPDATE | 'conn.Execute "UPDATE crm_pre_llamada SET anulado = 'Si' etc… |
| Visualiza_Presupuesto.frm | 5658 | SELECT | sql_llamada = "SELECT * FROM crm_pre_llamada WHERE CodigoMov… |
| Crm_Presupuesto_Llamada.frm | 663 | SELECT | conn.Execute "DELETE FROM crm_pre_llamada WHERE CodigoMovimi… |
| Crm_Presupuesto_Llamada.frm | 663 | DELETE | conn.Execute "DELETE FROM crm_pre_llamada WHERE CodigoMovimi… |
| Crm_Presupuesto_Llamada.frm | 667 | SELECT | rs_llamada.Open "SELECT id_llamada FROM crm_pre_llamada WHER… |
| Crm_Presupuesto_Llamada.frm | 671 | INSERT | conn.Execute "INSERT INTO crm_pre_llamada (id_llamada, Codig… |
| Crm_Presupuesto_Llamada.frm | 946 | UPDATE | conn.Execute "UPDATE crm_pre_llamada SET CodigoMovimientoPre… |
| Crm_Presupuesto_Llamada.frm | 964 | SELECT | conn.Execute "DELETE FROM crm_pre_llamada WHERE id_llamada =… |
| Crm_Presupuesto_Llamada.frm | 964 | DELETE | conn.Execute "DELETE FROM crm_pre_llamada WHERE id_llamada =… |
| Funciones.bas | 8279 | JOIN | sql_ped = "SELECT * FROM comp_ped INNER JOIN crm_pre_llamada… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)