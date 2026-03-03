# Tabla `en_art_pesaje_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_articulo_pesaje | BIGINT | No | ✓ |  |  |
| id_articulo_contenedor | BIGINT | Sí |  |  |  |
| nombre_articulo | VARCHAR | Sí |  |  |  |
| peso_articulo_unidad | DECIMAL | Sí |  |  |  |
| capacidad_articulo_unidad | DECIMAL | Sí |  |  |  |
| cantidad_articulo | DECIMAL | Sí |  |  |  |
| peso_articulo_total | DECIMAL | Sí |  |  |  |
| nro_cod_barra | VARCHAR | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| id_en_vehiculo | BIGINT | Sí |  |  |  |
| id_manual_art_contenedor | VARCHAR | Sí |  |  |  |
| id_iva_art | BIGINT | Sí |  |  |  |
| alicuota_art | DECIMAL | Sí |  |  |  |
| moneda_art | VARCHAR | Sí |  |  |  |
| precio_costo_art | DECIMAL | Sí |  |  |  |
| id_alic_ib | BIGINT | Sí |  |  |  |

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
| En_Carga_Pesaje.frm | 5230 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| En_Carga_Pesaje.frm | 6083 | SELECT | rs_temp_bines.Open "SELECT * FROM en_art_pesaje_temp AS bi W… |
| En_Carga_Pesaje.frm | 6097 | SELECT | rs_temp_bines.Open "SELECT * FROM en_art_pesaje_temp WHERE  … |
| En_Carga_Pesaje.frm | 6124 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Pesaje.frm | 6326 | SELECT | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE id_en_art… |
| En_Carga_Pesaje.frm | 6326 | DELETE | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE id_en_art… |
| En_Carga_Pesaje.frm | 6329 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Pesaje.frm | 6452 | SELECT | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Pesaje.frm | 6452 | DELETE | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Pesaje.frm | 6783 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| En_Carga_Pesaje.frm | 6838 | UPDATE | conn.Execute "UPDATE en_art_pesaje_temp AS bb SET  bb.id_en_… |
| En_Carga_Pesaje.frm | 6900 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Pesaje.frm | 6956 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| En_Carga_Vale.frm | 4310 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| En_Carga_Vale.frm | 5009 | SELECT | rs_temp_bines.Open "SELECT * FROM en_art_pesaje_temp AS bi W… |
| En_Carga_Vale.frm | 5023 | SELECT | rs_temp_bines.Open "SELECT * FROM en_art_pesaje_temp WHERE  … |
| En_Carga_Vale.frm | 5050 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Vale.frm | 5256 | SELECT | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE id_en_art… |
| En_Carga_Vale.frm | 5256 | DELETE | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE id_en_art… |
| En_Carga_Vale.frm | 5259 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Vale.frm | 5381 | SELECT | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Vale.frm | 5381 | DELETE | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Vale.frm | 5684 | SELECT | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Vale.frm | 5684 | DELETE | conn.Execute "DELETE FROM en_art_pesaje_temp WHERE en_art_pe… |
| En_Carga_Vale.frm | 5748 | SELECT | rs_temp_bines.Open "SELECT * FROM en_art_pesaje_temp WHERE  … |
| En_Carga_Vale.frm | 5875 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| En_Carga_Vale.frm | 5930 | UPDATE | conn.Execute "UPDATE en_art_pesaje_temp AS bb SET  bb.id_en_… |
| En_Carga_Vale.frm | 5992 | SELECT | consulta = "SELECT * FROM en_art_pesaje_temp AS bt WHERE bt.… |
| En_Carga_Vale.frm | 6048 | SELECT | " FROM en_art_pesaje_temp AS bb " & _ |
| Principal.frm | 6109 | SELECT | conn.Execute "delete from en_art_pesaje_temp where id_usuari… |
| Principal.frm | 6109 | DELETE | conn.Execute "delete from en_art_pesaje_temp where id_usuari… |
| Principal.frm | 6175 | SELECT | conn.Execute "delete from en_art_pesaje_temp where id_usuari… |
| Principal.frm | 6175 | DELETE | conn.Execute "delete from en_art_pesaje_temp where id_usuari… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)