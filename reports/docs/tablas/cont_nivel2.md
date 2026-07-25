# Tabla `cont_nivel2`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cont_nivel2 | INT | No | ✓ |  |  |
| id_pc | INT | Sí |  |  |  |
| desc_cuenta | VARCHAR | Sí |  |  |  |

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
| Cont_CargaPlanCta.frm | 1832 | SELECT | rs_existe.Open "SELECT * FROM cont_nivel2 WHERE id_pc = " & … |
| Cont_CargaPlanCta.frm | 1836 | SELECT | rs_Nref.Open "SELECT * from cont_nivel2 where id_cont_nivel2… |
| Cont_CargaPlanCta.frm | 1927 | SELECT | conn.Execute "DELETE FROM cont_nivel2 WHERE id_pc = " & idpc… |
| Cont_CargaPlanCta.frm | 1927 | DELETE | conn.Execute "DELETE FROM cont_nivel2 WHERE id_pc = " & idpc… |
| Cont_CargaPlanCta.frm | 1969 | SELECT | rs_lev2.Open "SELECT * from cont_nivel2 where id_pc = " & id… |
| Cont_CargaPlanCta.frm | 2019 | SELECT | rs_lev2.Open "SELECT * from cont_nivel2 where id_pc = " & Co… |
| Cont_CargaPlanCta.frm | 2077 | SELECT | rs_lev2.Open "SELECT * from cont_nivel2 where id_pc = " & Co… |
| Cont_CargaPlanCta.frm | 2147 | SELECT | rs_lev2.Open "SELECT * from cont_nivel2 where id_pc = " & Co… |
| Cont_CargaPlanCta.frm | 2229 | SELECT | rs_lev2.Open "SELECT * from cont_nivel2 where id_pc = " & Co… |
| Cont_PlanCta.frm | 1310 | SELECT | conn.Execute "DELETE FROM cont_nivel2 WHERE id_pc = " & SSTr… |
| Cont_PlanCta.frm | 1310 | DELETE | conn.Execute "DELETE FROM cont_nivel2 WHERE id_pc = " & SSTr… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)