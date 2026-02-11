# Tabla `cont_configuracion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cont_configuracion | DOUBLE | No | ✓ |  |  |
| nivel1_arbol | INT | Sí |  |  |  |
| nivel2_arbol | INT | Sí |  |  |  |
| nivel3_arbol | INT | Sí |  |  |  |
| nivel4_arbol | INT | Sí |  |  |  |
| nivel5_arbol | INT | Sí |  |  |  |
| nivel6_arbol | INT | Sí |  |  |  |

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
| Cont_CargaPlanCta.frm | 515 | SELECT | rs_CantDigitos.Open "Select * from cont_configuracion", conn… |
| Cont_PlanCta.frm | 656 | SELECT | rs_config.Open "select * from cont_configuracion", conn, adO… |
| Cont_PlanCta.frm | 797 | SELECT | rs_config.Open "Select * from cont_configuracion", conn, adO… |
| Cont_ParametrosIni.frm | 367 | SELECT | rs_ActContConfig.Open "Select * from cont_configuracion", co… |
| Cont_ParametrosIni.frm | 422 | SELECT | rs_ContConfig.Open "Select * from cont_configuracion", conn,… |
| Cont_pc.frm | 503 | SELECT | rs_config.Open "select * from cont_configuracion", conn, adO… |
| Cont_pc.frm | 644 | SELECT | rs_config.Open "Select * from cont_configuracion", conn, adO… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)