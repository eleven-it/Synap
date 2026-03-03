# Tabla `articulo_ce`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_ce | DOUBLE | No | ✓ |  |  |
| caption | VARCHAR | Sí |  |  |  |
| tipo_campo | VARCHAR | Sí |  |  |  |

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
| CargaArticulo_Original.frm | 12056 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| CargaArticulo_Original.frm | 12081 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| CargaArticulo_Original.frm | 12084 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |
| ABMArticulo_seleccion.frm | 4729 | SELECT | dataAdic.RecordSource = "select * from articulo_ce order by … |
| Articulo.frm | 7395 | SELECT | dataAdic.RecordSource = "select * from articulo_ce order by … |
| Articulo_FormulacionNom.frm | 4279 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| Articulo_FormulacionNom.frm | 4304 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| Articulo_FormulacionNom.frm | 4307 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |
| Articulo_FormulacionNom.frm | 4439 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| Articulo_FormulacionNom.frm | 4464 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| Articulo_FormulacionNom.frm | 4467 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |
| Articulo_ce.frm | 902 | SELECT | rs_matriz.Open "SELECT * from articulo_ce WHERE id_articulo_… |
| Articulo_ce.frm | 1036 | SELECT | rs_RecupMat.Open "SELECT * from articulo_ce", conn, adOpenDy… |
| CargaArticulo2.frm | 11962 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| CargaArticulo2.frm | 11987 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| CargaArticulo2.frm | 11990 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |
| Info_Comercial.frm | 7256 | SELECT | rs_articulo_ce.Open "SELECT articulo_ce.id_articulo_ce,artic… |
| AltaArticulo.frm | 5183 | SELECT | dataAdic.RecordSource = "select * from articulo_ce order by … |
| CargaArticulo.frm | 14075 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| CargaArticulo.frm | 14100 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| CargaArticulo.frm | 14103 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |
| VisualizarFichaArt.frm | 2956 | SELECT | rs_CampEsplbl.Open "SELECT * from articulo_ce", conn, adOpen… |
| ArticuloProv.frm | 4989 | SELECT | dataAdic.RecordSource = "select * from articulo_ce order by … |
| Principal.frm | 11473 | SELECT | rs_articulo_ce.Open "SELECT articulo_ce.id_articulo_ce,artic… |
| Principal.frm | 11724 | SELECT | rs_articulo_ce.Open "SELECT articulo_ce.id_articulo_ce,artic… |
| CargaArticulo2.frm | 11962 | SELECT | rs_LblCEspeciales.Open "SELECT * from articulo_ce", conn, ad… |
| CargaArticulo2.frm | 11987 | JOIN | "LEFT JOIN articulo_ce ON (articulo_ce.id_articulo_ce = arti… |
| CargaArticulo2.frm | 11990 | SELECT | rs_CampEspeciales.Open "SELECT * From articulo_ce ", conn, a… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)