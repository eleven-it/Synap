# Tabla `articulo_val_ce`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_val_ce | DOUBLE | No | ✓ |  |  |
| id_articulo | DOUBLE | No |  |  |  |
| id_articulo_ce | DOUBLE | Sí |  |  |  |
| valor_ce | VARCHAR | Sí |  |  |  |
| id_lista_valor_ce | DOUBLE | Sí |  |  |  |
| id_orden_lista | DOUBLE | Sí |  |  |  |

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
| AjustarSaldos.frm | 761 | SELECT | "FROM articulo_val_ce ", conn, adOpenDynamic, adLockOptimist… |
| AjustarSaldos.frm | 773 | SELECT | "From articulo_val_ce " & _ |
| CargaArticulo_Original.frm | 12080 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| CargaArticulo_Original.frm | 12099 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo_Original.frm | 12130 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo_Original.frm | 12884 | SELECT | rs_CampEspeciales.Open "SELECT * from articulo_val_ce " & _ |
| CargaArticulo_Original.frm | 12893 | SELECT | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo_Original.frm | 12893 | DELETE | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo_Original.frm | 13142 | SELECT | rs_CampEspeciales.Open "SELECT * FROM articulo_val_ce " & _ |
| ABMArticulo_seleccion.frm | 5898 | JOIN | "LEFT JOIN  articulo_val_ce ON articulo_val_ce.id_articulo =… |
| ABMArticulo_seleccion.frm | 5910 | JOIN | "LEFT JOIN  articulo_val_ce ON articulo_val_ce.id_articulo =… |
| Articulo_FormulacionNom.frm | 4303 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| Articulo_FormulacionNom.frm | 4322 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| Articulo_FormulacionNom.frm | 4359 | SELECT | '                            rs_val.Open "SELECT * FROM arti… |
| Articulo_FormulacionNom.frm | 4463 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| Articulo_FormulacionNom.frm | 4482 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| Articulo_FormulacionNom.frm | 4522 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo2.frm | 11986 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| CargaArticulo2.frm | 12005 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo2.frm | 12036 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo2.frm | 12790 | SELECT | rs_CampEspeciales.Open "SELECT * from articulo_val_ce " & _ |
| CargaArticulo2.frm | 12799 | SELECT | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo2.frm | 12799 | DELETE | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo2.frm | 13048 | SELECT | rs_CampEspeciales.Open "SELECT * FROM articulo_val_ce " & _ |
| Articulo_ce_CargaLista.frm | 621 | SELECT | rs_exist.Open "SELECT * FROM articulo_val_ce WHERE id_lista_… |
| Articulo_ce_CargaValor.frm | 407 | UPDATE | conn.Execute "UPDATE articulo_val_ce SET Valor_ce = '" & txt… |
| Info_Comercial.frm | 7257 | JOIN | "LEFT JOIN articulo_val_ce ON articulo_ce.id_articulo_ce = a… |
| AltaArticulo.frm | 6636 | JOIN | "LEFT JOIN  articulo_val_ce ON articulo_val_ce.id_articulo =… |
| AltaArticulo.frm | 6649 | JOIN | "LEFT JOIN  articulo_val_ce ON articulo_val_ce.id_articulo =… |
| CargaArticulo.frm | 14099 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| CargaArticulo.frm | 14118 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo.frm | 14149 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo.frm | 14903 | SELECT | rs_CampEspeciales.Open "SELECT * from articulo_val_ce " & _ |
| CargaArticulo.frm | 14912 | SELECT | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo.frm | 14912 | DELETE | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo.frm | 15161 | SELECT | rs_CampEspeciales.Open "SELECT * FROM articulo_val_ce " & _ |
| VisualizarFichaArt.frm | 2981 | SELECT | rs_CampEsp.Open "SELECT * from articulo_val_ce " & _ |
| Principal.frm | 11474 | JOIN | "LEFT JOIN articulo_val_ce ON articulo_ce.id_articulo_ce = a… |
| Principal.frm | 11725 | JOIN | "LEFT JOIN articulo_val_ce ON articulo_ce.id_articulo_ce = a… |
| Principal.frm | 12638 | SELECT | " FROM articulo_val_ce AS adicional " & _ |
| CargaArticulo2.frm | 11986 | SELECT | 'rs_CampEspeciales.Open "SELECT articulo_val_ce.*, articulo_… |
| CargaArticulo2.frm | 12005 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo2.frm | 12036 | SELECT | rs_val.Open "SELECT * FROM articulo_val_ce " & _ |
| CargaArticulo2.frm | 12790 | SELECT | rs_CampEspeciales.Open "SELECT * from articulo_val_ce " & _ |
| CargaArticulo2.frm | 12799 | SELECT | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo2.frm | 12799 | DELETE | conn.Execute "DELETE from articulo_val_ce where id_articulo … |
| CargaArticulo2.frm | 13048 | SELECT | rs_CampEspeciales.Open "SELECT * FROM articulo_val_ce " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)