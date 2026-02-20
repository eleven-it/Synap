# Tabla `articulo_valor_ce`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| articulo_valor_ce | DOUBLE | No | ✓ |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| valor1 | VARCHAR | Sí |  |  |  |
| valor2 | VARCHAR | Sí |  |  |  |
| valor3 | VARCHAR | No |  |  |  |
| valor4 | VARCHAR | No |  |  |  |
| valor5 | VARCHAR | No |  |  |  |
| valor6 | VARCHAR | No |  |  |  |
| valor7 | VARCHAR | No |  |  |  |
| valor8 | VARCHAR | No |  |  |  |
| valor9 | VARCHAR | No |  |  |  |
| valor10 | VARCHAR | No |  |  |  |

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
| AjustarSaldos.frm | 780 | SELECT | rs_Art_valor_Ce.Open "SELECT * from articulo_valor_ce", conn… |
| CargaArticulo_Original.frm | 12962 | SELECT | rs_articulo_valor_ce.Open "SELECT * from articulo_valor_ce W… |
| CargaArticulo_Original.frm | 13186 | SELECT | rs_articulo_valor_ce.Open "SELECT * FROM articulo_valor_ce W… |
| CargaArticulo2.frm | 12868 | SELECT | rs_articulo_valor_ce.Open "SELECT * from articulo_valor_ce W… |
| CargaArticulo2.frm | 13092 | SELECT | rs_articulo_valor_ce.Open "SELECT * FROM articulo_valor_ce W… |
| CargaArticulo.frm | 14981 | SELECT | rs_articulo_valor_ce.Open "SELECT * from articulo_valor_ce W… |
| CargaArticulo.frm | 15205 | SELECT | rs_articulo_valor_ce.Open "SELECT * FROM articulo_valor_ce W… |
| En_Carga_Pesaje.frm | 6560 | JOIN | " LEFT JOIN articulo_valor_ce AS artv ON artv.id_articulo = … |
| En_Carga_Vale.frm | 5489 | JOIN | " LEFT JOIN articulo_valor_ce AS artv ON artv.id_articulo = … |
| En_Carga_Vale.frm | 5743 | JOIN | " LEFT JOIN articulo_valor_ce AS artv ON artv.id_articulo = … |
| CargaArticulo2.frm | 12868 | SELECT | rs_articulo_valor_ce.Open "SELECT * from articulo_valor_ce W… |
| CargaArticulo2.frm | 13092 | SELECT | rs_articulo_valor_ce.Open "SELECT * FROM articulo_valor_ce W… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)