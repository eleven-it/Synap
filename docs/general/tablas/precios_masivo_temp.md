# Tabla `precios_masivo_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_precios_masivo_temp | INT | No | ✓ |  |  |
| id_articulo | DECIMAL | Sí |  |  |  |
| nombre_articulo | VARCHAR | Sí |  |  |  |
| precio_costo | DECIMAL | Sí |  |  |  |
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
| act_pv | INT | Sí |  |  |  |
| seleccion | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| porcentaje_dscto | DECIMAL | Sí |  |  |  |
| desc_porc_bonif | DECIMAL | Sí |  |  |  |
| desc_porc_pie | DECIMAL | Sí |  |  |  |
| descuento | DECIMAL | Sí |  |  |  |
| costo_proveedor | DOUBLE | Sí |  |  |  |
| costo_adicional | DOUBLE | Sí |  |  |  |

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
| PrevPrec.frm | 1485 | SELECT | conn.Execute "delete from precios_masivo_temp where id_usuar… |
| PrevPrec.frm | 1485 | DELETE | conn.Execute "delete from precios_masivo_temp where id_usuar… |
| PrevPrec.frm | 1511 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET seleccion = -1 … |
| PrevPrec.frm | 1512 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET act_pv = -1 WHE… |
| PrevPrec.frm | 1525 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET seleccion = 0 W… |
| PrevPrec.frm | 1526 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET act_pv = 0 WHER… |
| PrevPrec.frm | 1532 | SELECT | DataPrecTemp.RecordSource = "SELECT * FROM precios_masivo_te… |
| VariacionPrecio.frm | 5405 | SELECT | conn.Execute "DELETE FROM precios_masivo_temp WHERE id_usuar… |
| VariacionPrecio.frm | 5405 | DELETE | conn.Execute "DELETE FROM precios_masivo_temp WHERE id_usuar… |
| VariacionPrecio.frm | 6141 | SELECT | PrevPrec.DataPrecTemp.RecordSource = "SELECT * FROM precios_… |
| VariacionPrecio.frm | 6661 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET " & _ |
| VariacionPrecio.frm | 6668 | UPDATE | conn.Execute "UPDATE precios_masivo_temp SET " & _ |
| VariacionPrecio.frm | 6674 | SELECT | PrevPrec.DataPrecTemp.RecordSource = "SELECT * FROM precios_… |
| Principal.frm | 6097 | SELECT | conn.Execute "delete from precios_masivo_temp where id_usuar… |
| Principal.frm | 6097 | DELETE | conn.Execute "delete from precios_masivo_temp where id_usuar… |
| Principal.frm | 6163 | SELECT | conn.Execute "delete from precios_masivo_temp where id_usuar… |
| Principal.frm | 6163 | DELETE | conn.Execute "delete from precios_masivo_temp where id_usuar… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)