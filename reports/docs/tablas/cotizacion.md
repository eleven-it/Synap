# Tabla `cotizacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ValorPesos | DECIMAL | Sí |  |  |  |
| id_cotizacion | INT | No | ✓ |  |  |
| nombre_cotizacion | VARCHAR | Sí |  |  |  |
| defecto | VARCHAR | Sí |  |  |  |
| simbolo | VARCHAR | Sí |  |  |  |
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
| Info_Estadistica.frm | 3681 | SELECT | '                rs_cotizacion.Open "SELECT * from cotizacio… |
| Info_Estadistica.frm | 3949 | SELECT | rs_cotizacion.Open "SELECT * from cotizacion", conn, adOpenD… |
| FacturaB_COPIA.frm | 7899 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| ABMCotizacion.frm | 634 | SELECT | consulta = "SELECT * FROM cotizacion WHERE nombre_cotizacion… |
| ABMCotizacion.frm | 677 | SELECT | 'Data_Cotizacion.RecordSource = "select * from Cotizacion" |
| ABMCotizacion.frm | 682 | SELECT | 'Data_Cotizacion.RecordSource = "select * from cotizacion" |
| Visualiza_Pedido.frm | 3818 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| CargaArticulo_Original.frm | 8712 | SELECT | rs_cotizacion.Open "SELECT * FROM cotizacion WHERE anulado =… |
| Info_Banco.frm | 2771 | SELECT | rs_cotizacion.Open "SELECT * from cotizacion", conn, adOpenD… |
| Info_Venta_respaldo_bruno.frm | 8350 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion", conn… |
| Info_Venta.frm | 8747 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion", conn… |
| IngresoUsuario.frm | 2807 | SELECT | .Source = "SELECT  * FROM cotizacion" |
| FacturaB.frm | 12987 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| FacturaA.frm | 8529 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| Presupuesto.frm | 5774 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| Pedido.frm | 6293 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| ActDatos_Articulo.frm | 3928 | JOIN | " LEFT JOIN cotizacion ON (cotizacion.id_cotizacion = articu… |
| ActDatos_Articulo.frm | 4100 | SELECT | data_cotizacion.RecordSource = "SELECT * FROM cotizacion WHE… |
| Cotizador.frm | 1526 | SELECT | DataMoneda.RecordSource = "select * from Cotizacion" |
| CargaArticulo.frm | 9649 | SELECT | rs_cotizacion.Open "SELECT * FROM cotizacion WHERE anulado =… |
| Visualiza_Presupuesto.frm | 5608 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion ", con… |
| Carga_Cotizacion.frm | 339 | SELECT | rs_cotizacion.Open "SELECT * FROM cotizacion WHERE id_cotiza… |
| Carga_Cotizacion.frm | 366 | SELECT | rs_cotizacion.Open "SELECT * FROM cotizacion WHERE id_cotiza… |
| ReciboCobro.frm | 9867 | SELECT | '                            "From Cotizacion, logi_gestion_… |
| Info_Compra.frm | 3003 | SELECT | rs_cotizacion.Open "SELECT ValorPesos FROM cotizacion", conn… |
| Funciones.bas | 7264 | SELECT | .Source = "SELECT * FROM cotizacion WHERE id_cotizacion = 1" |
| Funciones.bas | 7297 | SELECT | rs_consulta.Open "SELECT * FROM cotizacion WHERE id_cotizaci… |
| Funciones.bas | 7334 | SELECT | " FROM cotizacion " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)