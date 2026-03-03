# Tabla `articulo_lista_valor_ce`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_lista_valor_ce | DOUBLE | No | ✓ |  |  |
| id_articulo_ce | DOUBLE | Sí |  |  |  |
| valor_lista | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| nro_orden | DOUBLE | Sí |  |  |  |

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
| CargaArticulo_Original.frm | 12125 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |
| Articulo_FormulacionNom.frm | 4354 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |
| Articulo_FormulacionNom.frm | 4517 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |
| CargaArticulo2.frm | 12031 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |
| Articulo_ce_CargaLista.frm | 496 | SELECT | DataCe.RecordSource = "SELECT * From articulo_lista_valor_ce… |
| Articulo_ce_CargaLista.frm | 574 | SELECT | DataCe.RecordSource = "SELECT * FROM articulo_lista_valor_ce… |
| Articulo_ce_CargaValor.frm | 351 | SELECT | rs_exist.Open "SELECT * FROM articulo_lista_valor_ce " & _ |
| Articulo_ce_CargaValor.frm | 392 | SELECT | rs_exist.Open "SELECT * FROM articulo_lista_valor_ce " & _ |
| CargaArticulo.frm | 14144 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |
| CargaArticulo2.frm | 12031 | SELECT | DataComboCe(rs_CampEspeciales.Fields!id_articulo_ce).RecordS… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)