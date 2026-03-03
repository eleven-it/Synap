# Tabla `precios_historial`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_precios_historial | INT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_modificacion | VARCHAR | Sí |  |  |  |
| id_articulo | DECIMAL | Sí |  |  |  |
| util1 | DECIMAL | Sí |  |  |  |
| util2 | DECIMAL | Sí |  |  |  |
| util3 | DECIMAL | Sí |  |  |  |
| util4 | DECIMAL | Sí |  |  |  |
| util5 | DECIMAL | Sí |  |  |  |
| precio_neto1 | DECIMAL | Sí |  |  |  |
| precio_neto2 | DECIMAL | Sí |  |  |  |
| precio_neto3 | DECIMAL | Sí |  |  |  |
| precio_neto4 | DECIMAL | Sí |  |  |  |
| precio_neto5 | DECIMAL | Sí |  |  |  |
| precio_neto_of | DECIMAL | Sí |  |  |  |
| alicuota_iva | DECIMAL | Sí |  |  |  |
| precio_iva1 | DECIMAL | Sí |  |  |  |
| precio_iva2 | DECIMAL | Sí |  |  |  |
| precio_iva3 | DECIMAL | Sí |  |  |  |
| precio_iva4 | DECIMAL | Sí |  |  |  |
| precio_iva5 | DECIMAL | Sí |  |  |  |
| precio_iva_of | DECIMAL | Sí |  |  |  |
| nombre_articulo | VARCHAR | Sí |  |  |  |
| precio_costo | DECIMAL | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| moneda | VARCHAR | Sí |  |  |  |
| id_proveedor | INT | Sí |  |  |  |
| precio_costo_neto | DECIMAL | Sí |  |  |  |
| descuento | DECIMAL | Sí |  |  |  |
| comp_factura | VARCHAR | Sí |  |  |  |
| porcentaje_dscto | DECIMAL | Sí |  |  |  |
| precio_costo_iva | DECIMAL | Sí |  |  |  |
| desc_porc_bonif | DECIMAL | Sí |  |  |  |
| desc_porc_pie | DECIMAL | Sí |  |  |  |
| porcentaje_aumento_costo | DECIMAL | Sí |  |  |  |
| modo_marcacion | VARCHAR | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| precios_historial | proveedor | CargaArticulo_Original.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo_Original.frm | 8882 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |
| precios_historial | proveedor | CargaArticulo2.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo2.frm | 8771 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |
| precios_historial | proveedor | CargaArticulo.frm | - | SELECT  precios_historial.*, proveedor.nombre as provee From precios_historial I… |
| precios_historial | proveedor | CargaArticulo.frm | 9860 | '    DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as… |
| precios_historial | proveedor | CargaArticulo.frm | 10117 | DataHistop.RecordSource = "SELECT  precios_historial.*, proveedor.nombre as prov… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Articulo_Carga_datos_adicional.frm | 2827 | SELECT | rs_historial.Open "SELECT  * FROM precios_historial limit 1"… |
| PrevPrec.frm | 1278 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| CargaArticulo_Original.frm | 8882 | SELECT | DataHistop.RecordSource = "SELECT  precios_historial.*, prov… |
| CargaArticulo_Original.frm | 9489 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| CargaArticulo_Original.frm | 10074 | SELECT | rs_historial.Open "SELECT  * FROM precios_historial limit 1"… |
| VariacionPrecio.frm | 5696 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |
| VariacionPrecio.frm | 6086 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |
| VariacionPrecio.frm | 6984 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |
| VariacionPrecio.frm | 7388 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |
| VariacionPrecio.frm | 7513 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| VariacionPrecio.frm | 8141 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |
| CargaArticulo2.frm | 8771 | SELECT | DataHistop.RecordSource = "SELECT  precios_historial.*, prov… |
| CargaArticulo2.frm | 9371 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| CargaArticulo2.frm | 9952 | SELECT | rs_historial.Open "SELECT  * FROM precios_historial limit 1"… |
| PFactura.frm | 5319 | SELECT | rs_historial.Open "SELECT * FROM precios_historial WHERE id_… |
| ActDescuento_Prov.frm | 2205 | INSERT | a = "INSERT INTO precios_historial (" & _ |
| ActDescuento_Prov.frm | 2223 | INSERT | conn2.Execute "INSERT INTO precios_historial (" & _ |
| Visualiza_PFactura_Copia.frm | 3995 | SELECT | rs_historial.Open "SELECT * FROM precios_historial WHERE id_… |
| HistoPrecio.frm | 721 | SELECT | DataArticulo.RecordSource = "SELECT precios_historial.*,usua… |
| CargaArticulo.frm | 9860 | SELECT | '    DataHistop.RecordSource = "SELECT  precios_historial.*,… |
| CargaArticulo.frm | 10117 | SELECT | DataHistop.RecordSource = "SELECT  precios_historial.*, prov… |
| CargaArticulo.frm | 10792 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| CargaArticulo.frm | 11519 | SELECT | rs_historial.Open "SELECT  * FROM precios_historial limit 1"… |
| Visualiza_PFacturaCopia2.frm | 4134 | SELECT | rs_historial.Open "SELECT * FROM precios_historial WHERE id_… |
| Visualiza_PFactura.frm | 4208 | SELECT | rs_historial.Open "SELECT * FROM precios_historial WHERE id_… |
| Principal.frm | 7612 | INSERT | conn2.Execute "INSERT INTO precios_historial (" & _ |
| Principal.frm | 7777 | INSERT | conn2.Execute "INSERT INTO precios_historial (" & _ |
| CargaArticulo2.frm | 8771 | SELECT | DataHistop.RecordSource = "SELECT  precios_historial.*, prov… |
| CargaArticulo2.frm | 9371 | SELECT | rs_historial.Open "SELECT * FROM precios_historial where id_… |
| CargaArticulo2.frm | 9952 | SELECT | rs_historial.Open "SELECT  * FROM precios_historial limit 1"… |
| Funciones.bas | 7655 | INSERT | conn.Execute "INSERT INTO precios_historial (" & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)