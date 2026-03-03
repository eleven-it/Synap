# Tabla `articulo_tipo_cliente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_tipo_cliente | INT | No | ✓ |  |  |
| id_tipo_cliente | INT | Sí |  |  |  |
| id_articulo | INT | Sí |  |  |  |

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
| Articulo_tipo_cliente.frm | 790 | SELECT | "From articulo_tipo_cliente " & _ |
| Articulo_tipo_cliente.frm | 888 | SELECT | rs.Open "SELECT * FROM articulo_tipo_cliente WHERE id_articu… |
| Articulo_tipo_cliente.frm | 907 | INSERT | conn.Execute "INSERT INTO articulo_tipo_cliente (id_tipo_cli… |
| Articulo_tipo_cliente.frm | 938 | SELECT | conn.Execute "DELETE FROM articulo_tipo_cliente WHERE id_art… |
| Articulo_tipo_cliente.frm | 938 | DELETE | conn.Execute "DELETE FROM articulo_tipo_cliente WHERE id_art… |
| Articulo_tipo_cliente.frm | 960 | SELECT | "From articulo_tipo_cliente " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)