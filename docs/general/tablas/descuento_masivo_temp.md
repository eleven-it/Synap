# Tabla `descuento_masivo_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_descuento_masivo_temp | DOUBLE | No | ✓ |  |  |
| id_articulo | DECIMAL | Sí |  |  |  |
| nombre_articulo | VARCHAR | Sí |  |  |  |
| seleccion | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| ActDescuento.frm | 1274 | SELECT | conn.Execute "delete from descuento_masivo_temp where id_usu… |
| ActDescuento.frm | 1274 | DELETE | conn.Execute "delete from descuento_masivo_temp where id_usu… |
| ActDescuento.frm | 1324 | SELECT | PrevDesc.DataCuerpo.RecordSource = "SELECT * FROM descuento_… |
| ActDescuento.frm | 1509 | SELECT | DataCuerpo.RecordSource = "select * from descuento_masivo_te… |
| Principal.frm | 6079 | SELECT | conn.Execute "delete from descuento_masivo_temp where id_usu… |
| Principal.frm | 6079 | DELETE | conn.Execute "delete from descuento_masivo_temp where id_usu… |
| Principal.frm | 6145 | SELECT | conn.Execute "delete from descuento_masivo_temp where id_usu… |
| Principal.frm | 6145 | DELETE | conn.Execute "delete from descuento_masivo_temp where id_usu… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)