# Tabla `articulo_prov_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_prov_temp | DOUBLE | No | ✓ |  |  |
| codProveedor | DOUBLE | Sí |  |  |  |
| IDArt | DOUBLE | No |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| nombreArticulo_prov | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| multiplicador_comp | DECIMAL | Sí |  |  |  |
| cantidad_uni | DECIMAL | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nombre_proveedor | VARCHAR | Sí |  |  |  |
| nombre_unimed | VARCHAR | Sí |  |  |  |
| id_presentacionC | DOUBLE | Sí |  |  |  |

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
| AsigProvArt.frm | 752 | JOIN | "INNER JOIN articulo_prov_temp b on " & _ |
| AsigProvArt.frm | 771 | SELECT | "From articulo_prov_temp " & _ |
| AsigProvArt.frm | 854 | SELECT | conn.Execute "DELETE FROM articulo_prov_temp WHERE id_articu… |
| AsigProvArt.frm | 854 | DELETE | conn.Execute "DELETE FROM articulo_prov_temp WHERE id_articu… |
| AsigProvArt.frm | 897 | SELECT | "From Articulo_prov_temp WHERE id_usuario= " & Principal.idU… |
| AsigProvArt.frm | 1084 | SELECT | conn.Execute "delete from articulo_prov_temp where id_usuari… |
| AsigProvArt.frm | 1084 | DELETE | conn.Execute "delete from articulo_prov_temp where id_usuari… |
| AsigProvArt.frm | 1132 | INSERT | conn.Execute "INSERT INTO articulo_prov_temp (anulado,cantid… |
| AsigProvArt.frm | 1151 | SELECT | "From Articulo_prov_temp WHERE id_usuario= " & Principal.idU… |
| AsigProvArt_Carga.frm | 1038 | SELECT | rs_prov.Open "SELECT codProveedor from articulo_prov_temp WH… |
| AsigProvArt_Carga.frm | 1058 | SELECT | DataProveedor.RecordSource = "SELECT * FROM articulo_prov_te… |
| AsigProvArt_Carga.frm | 1091 | SELECT | AsigProvArt.DataProveedor.RecordSource = "SELECT * FROM arti… |
| AsigProvArt_Carga.frm | 1129 | SELECT | AsigProvArt.DataProveedor.RecordSource = "SELECT * FROM arti… |
| Principal.frm | 6104 | SELECT | conn.Execute "delete from articulo_prov_temp where id_usuari… |
| Principal.frm | 6104 | DELETE | conn.Execute "delete from articulo_prov_temp where id_usuari… |
| Principal.frm | 6170 | SELECT | conn.Execute "delete from articulo_prov_temp where id_usuari… |
| Principal.frm | 6170 | DELETE | conn.Execute "delete from articulo_prov_temp where id_usuari… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)