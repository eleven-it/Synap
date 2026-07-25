# Tabla `articulo_qr`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_articulo_qr | BIGINT | No | ✓ |  |  |
| id_articulo | BIGINT | Sí |  |  |  |
| img_qr | LONGBLOB | Sí |  |  |  |
| texto_cod_qr | VARCHAR | Sí |  |  |  |
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
| Funciones.bas | 9336 | SELECT | conn.Execute "DELETE FROM articulo_qr WHERE id_usuario = " &… |
| Funciones.bas | 9336 | DELETE | conn.Execute "DELETE FROM articulo_qr WHERE id_usuario = " &… |
| Funciones.bas | 9351 | SELECT | rs_consulta.Open "SELECT * FROM articulo_qr WHERE id_articul… |
| Funciones.bas | 9414 | SELECT | conn.Execute "DELETE FROM articulo_qr WHERE id_usuario = " &… |
| Funciones.bas | 9414 | DELETE | conn.Execute "DELETE FROM articulo_qr WHERE id_usuario = " &… |
| Funciones.bas | 9425 | SELECT | rs_consulta2.Open "SELECT * FROM articulo_qr WHERE id_articu… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)