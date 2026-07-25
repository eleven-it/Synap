# Tabla `rubro_categoria`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_categoria | BIGINT | No | ✓ |  |  |
| nombre_categoria | VARCHAR | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| url_foto | VARCHAR | Sí |  |  |  |

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
| Rubro.frm | 462 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| Programa_Descuentos.frm | 2181 | SELECT | Data_Categoria.RecordSource = "SELECT * FROM rubro_categoria… |
| Programa_Descuentos.frm | 2377 | JOIN | "LEFT JOIN rubro_categoria ON(rubro_categoria.id_categoria =… |
| stock_consulta_avanzada.frm | 2072 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| stock_consulta_avanzada.frm | 2179 | SELECT | Data_Categoria.RecordSource = "SELECT * FROM rubro_categoria… |
| Exportacion.frm | 7663 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| CargaRubro.frm | 502 | SELECT | data_rubro_categoria.RecordSource = "select * from rubro_cat… |
| Info_Comercial.frm | 8219 | SELECT | DataCategoria.RecordSource = "SELECT * FROM rubro_categoria … |
| ActDatos_Articulo.frm | 3921 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| ActDatos_Articulo.frm | 3990 | SELECT | Data_Categoria.RecordSource = "SELECT * FROM rubro_categoria… |
| ecom_datos_articulo.frm | 3214 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| ActDescuento_Prov.frm | 1863 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| ActDescuento_Prov.frm | 1931 | SELECT | Data_Categoria.RecordSource = "SELECT * FROM rubro_categoria… |
| ABMRubroCategoria.frm | 334 | SELECT | DataRubroCategoria.RecordSource = "select * from rubro_categ… |
| ABMRubroCategoria.frm | 427 | SELECT | consulta = "SELECT * FROM rubro_categoria WHERE nombre_categ… |
| ABMRubroCategoria.frm | 462 | SELECT | DataRubroCategoria.RecordSource = "select * from rubro_categ… |
| Programa_Descuentos_Carga.frm | 2685 | SELECT | Data_Categoria.RecordSource = "SELECT * FROM rubro_categoria… |
| ml_sincronizacion.frm | 1277 | SELECT | DataCategoria.RecordSource = "SELECT * FROM rubro_categoria … |
| ml_sincronizacion.frm | 1636 | JOIN | '"INNER JOIN rubro_categoria on (rubro_categoria.id_categori… |
| Programa_Descuentos_Canje.frm | 972 | JOIN | "LEFT JOIN rubro_categoria ON(rubro_categoria.id_categoria =… |
| Programa_Descuentos_Canje.frm | 1008 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| Programa_Descuentos_Canje.frm | 1383 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| AltaSubRubro.frm | 777 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| AltaSubRubro.frm | 1145 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1970 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |
| CargaRubroCategoria.frm | 233 | SELECT | rs_rubro_categoria_cons.Open "SELECT * FROM rubro_categoria … |
| CargaRubroCategoria.frm | 244 | SELECT | rs_rubro_categoria.Open "SELECT * FROM rubro_categoria WHERE… |
| CargaRubroCategoria.frm | 259 | SELECT | ABMRubroCategoria.DataRubroCategoria.RecordSource = "SELECT … |
| CargaRubroCategoria.frm | 270 | SELECT | rs_rubro_categoria_cons.Open "SELECT * FROM rubro_categoria … |
| CargaRubroCategoria.frm | 281 | SELECT | rs_rubro_categoria.Open "SELECT * FROM rubro_categoria WHERE… |
| CargaRubroCategoria.frm | 297 | SELECT | ABMRubroCategoria.DataRubroCategoria.RecordSource = "SELECT … |
| Informes.bas | 3218 | JOIN | " LEFT JOIN rubro_categoria ON (rubro_categoria.id_categoria… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)