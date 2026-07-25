# Tabla `cont_nivel6`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cont_nivel6 | INT | No | ✓ |  |  |
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
| Cont_CargaPlanCta.frm | 1931 | SELECT | conn.Execute "DELETE FROM cont_nivel6 WHERE id_pc = " & idpc… |
| Cont_CargaPlanCta.frm | 1931 | DELETE | conn.Execute "DELETE FROM cont_nivel6 WHERE id_pc = " & idpc… |
| Cont_CargaPlanCta.frm | 2176 | SELECT | rs_lev6.Open "SELECT * from cont_nivel6 where id_pc = " & id… |
| Cont_PlanCta.frm | 1314 | SELECT | conn.Execute "DELETE FROM cont_nivel6 WHERE id_pc = " & SSTr… |
| Cont_PlanCta.frm | 1314 | DELETE | conn.Execute "DELETE FROM cont_nivel6 WHERE id_pc = " & SSTr… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)