# Tabla `laboratorio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodLaboratorio | INT | No | ✓ |  |  |
| NombreLaboratorio | VARCHAR | No |  |  |  |
| Observaciones | LONGTEXT | Sí |  |  |  |
| Domicilio | TEXT | Sí |  |  |  |
| Provincia | VARCHAR | Sí |  |  |  |
| TelLab | VARCHAR | Sí |  |  |  |
| FaxLab | VARCHAR | Sí |  |  |  |
| EmailLab | VARCHAR | Sí |  |  |  |
| Contacto | VARCHAR | Sí |  |  |  |
| CelContacto | VARCHAR | Sí |  |  |  |
| TelContacto | VARCHAR | Sí |  |  |  |
| EmailContacto | VARCHAR | Sí |  |  |  |
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
| Info_Stock.frm | 11615 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| ABMArticulo_seleccion.frm | 3205 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| ABMArticulo_seleccion.frm | 5039 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE  anulad… |
| ABMArticulo_seleccion.frm | 5771 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| Articulo.frm | 7821 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE  anulad… |
| Articulo.frm | 8126 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| Articulo.frm | 8417 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| Info_Venta_respaldo_bruno.frm | 10109 | SELECT | DataLaboratorio.RecordSource = "select * from laboratorio or… |
| Info_Venta.frm | 10197 | SELECT | DataLaboratorio.RecordSource = "select * from laboratorio or… |
| stock_consulta_avanzada.frm | 3920 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE anulado… |
| Sup_importacion_tablas.frm | 6155 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| ActDatos_Articulo.frm | 4924 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE anulado… |
| ActDescuento_Prov.frm | 2827 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE anulado… |
| AltaArticulo.frm | 3490 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| AltaArticulo.frm | 5555 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE anulado… |
| AltaArticulo.frm | 6499 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| VisualizarFichaArt.frm | 2290 | JOIN | "LEFT JOIN Laboratorio ON (Laboratorio.CodLaboratorio = arti… |
| ABMLaboratorio.frm | 483 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| ABMLaboratorio.frm | 560 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio wh… |
| ABMLaboratorio.frm | 568 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio wh… |
| ABMLaboratorio.frm | 580 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio or… |
| ABMLaboratorio.frm | 589 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio wh… |
| ABMLaboratorio.frm | 598 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio wh… |
| ABMLaboratorio.frm | 611 | SELECT | DataLaboratorio.RecordSource = "select * from Laboratorio wh… |
| ABMLaboratorio.frm | 653 | SELECT | DataLaboratorio.RecordSource = "select * from laboratorio or… |
| ABMLaboratorio.frm | 656 | SELECT | DataLaboratorio.RecordSource = "select * from laboratorio wh… |
| CargaLaboratorio.frm | 413 | SELECT | rs_validacion.Open "SELECT * FROM laboratorio WHERE NombreLa… |
| CargaLaboratorio.frm | 425 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE CodLabo… |
| CargaLaboratorio.frm | 489 | SELECT | ABMLaboratorio.DataLaboratorio.RecordSource = "SELECT * FROM… |
| CargaLaboratorio.frm | 496 | SELECT | rs_validacion.Open "SELECT * FROM laboratorio WHERE NombreLa… |
| CargaLaboratorio.frm | 508 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE CodLabo… |
| ArticuloProv.frm | 5646 | SELECT | rs_laboratorio.Open "SELECT * FROM laboratorio WHERE  anulad… |
| ArticuloProv.frm | 5906 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| ArticuloProv.frm | 6105 | SELECT | '        DataLaboratorio.RecordSource = "SELECT * FROM labor… |
| ArticuloProv.frm | 6478 | SELECT | DataLaboratorio.RecordSource = "SELECT * FROM laboratorio WH… |
| Informes.bas | 3221 | JOIN | " LEFT JOIN laboratorio ON (laboratorio.codlaboratorio = art… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)