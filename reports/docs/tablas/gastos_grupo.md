# Tabla `gastos_grupo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_gastos_grupo | BIGINT | No | ✓ |  |  |
| nombre_gastos_grupo | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| AltaGastos.frm | 509 | JOIN | " INNER JOIN gastos_grupo ON (gastos_grupo.id_gastos_grupo =… |
| ABMGastos_Grupo.frm | 425 | SELECT | " FROM gastos_grupo WHERE " & _ |
| Carga_Gastos_Grupo.frm | 220 | SELECT | rs_Gasto_Grupo.Open "SELECT * FROM gastos_grupo WHERE id_gas… |
| Carga_Gastos_Grupo.frm | 257 | SELECT | rs_Gasto_Grupo.Open "SELECT * FROM gastos_grupo WHERE id_gas… |
| CargaGasto.frm | 1027 | SELECT | Data_Grupo_Gasto.RecordSource = "SELECT * FROM gastos_grupo … |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 1466 | JOIN | LEFT JOIN gastos_grupo gg ON gg.id_gastos_grupo = g.id_gasto… |

[← Índice de tablas](../DB_INDICE_TABLAS.md)