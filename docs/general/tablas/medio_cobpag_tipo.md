# Tabla `medio_cobpag_tipo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_mcp_tipo | DOUBLE | No | ✓ |  |  |
| nombre_mcp_tipo | VARCHAR | Sí |  |  |  |
| tipo_datos_adicional | VARCHAR | Sí |  |  |  |
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
| Carga_ABM_medio_cobpag.frm | 678 | SELECT | data_medio_cobpago_tipo.RecordSource = "select * from medio_… |
| ABM_medio_cobpag_tipo.frm | 463 | SELECT | data_mcp_tipo.RecordSource = "SELECT * FROM medio_cobpag_tip… |
| Carga_medio_cobpag_tipo.frm | 295 | SELECT | rs_medio_cobpag_tipo.Open "SELECT * FROM medio_cobpag_tipo W… |
| Carga_medio_cobpag_tipo.frm | 311 | SELECT | rs_medio_cobpag_tipo.Open "SELECT * FROM medio_cobpag_tipo W… |
| Carga_medio_cobpag_tipo.frm | 327 | SELECT | ABM_medio_cobpag_tipo.data_mcp_tipo.RecordSource = "SELECT *… |
| Carga_medio_cobpag_tipo.frm | 338 | SELECT | rs_medio_cobpag_tipo.Open "SELECT * FROM medio_cobpag_tipo W… |
| Carga_medio_cobpag_tipo.frm | 352 | SELECT | ABM_medio_cobpag_tipo.data_mcp_tipo.RecordSource = "SELECT *… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)