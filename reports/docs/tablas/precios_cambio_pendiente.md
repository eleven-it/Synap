# Tabla `precios_cambio_pendiente`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_precio_cp | BIGINT | No | ✓ |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| PrecioCosto | DOUBLE | Sí |  |  |  |
| Util1 | DOUBLE | Sí |  |  |  |
| Util2 | DOUBLE | Sí |  |  |  |
| Util3 | DOUBLE | Sí |  |  |  |
| Util4 | DOUBLE | Sí |  |  |  |
| Util5 | DOUBLE | Sí |  |  |  |
| Precio1V | DOUBLE | Sí |  |  |  |
| Precio2V | DOUBLE | Sí |  |  |  |
| Precio3V | DOUBLE | Sí |  |  |  |
| Precio4V | DOUBLE | Sí |  |  |  |
| Precio5V | DOUBLE | Sí |  |  |  |
| Precio1VI | DOUBLE | Sí |  |  |  |
| Precio2VI | DOUBLE | Sí |  |  |  |
| Precio3VI | DOUBLE | Sí |  |  |  |
| Precio4VI | DOUBLE | Sí |  |  |  |
| Precio5VI | DOUBLE | Sí |  |  |  |
| PNOficial | DOUBLE | Sí |  |  |  |
| PFOficial | DOUBLE | Sí |  |  |  |
| PorOficial1 | DOUBLE | Sí |  |  |  |
| PorOficial2 | DOUBLE | Sí |  |  |  |
| PorOficial3 | DOUBLE | Sí |  |  |  |
| UtilOficial | DOUBLE | Sí |  |  |  |
| pendiente | VARCHAR | Sí |  |  |  |
| seleccionado | INT | Sí |  |  |  |
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
| Articulo_Carga_datos_adicional.frm | 2274 | JOIN | " LEFT JOIN precios_cambio_pendiente ON (precios_cambio_pend… |
| Articulo_Carga_datos_adicional.frm | 2887 | SELECT | rs_act_precio_pendiente.Open "SELECT  * FROM precios_cambio_… |
| Articulo_Carga_datos_adicional.frm | 2889 | SELECT | rs_act_precio_pendiente.Open "SELECT  * FROM precios_cambio_… |
| Articulo_Carga_datos_adicional.frm | 2932 | SELECT | conn.Execute "DELETE FROM precios_cambio_pendiente WHERE id_… |
| Articulo_Carga_datos_adicional.frm | 2932 | DELETE | conn.Execute "DELETE FROM precios_cambio_pendiente WHERE id_… |
| VariacionPrecio.frm | 7592 | SELECT | conn.Execute "DELETE FROM precios_cambio_pendiente WHERE pen… |
| VariacionPrecio.frm | 7592 | DELETE | conn.Execute "DELETE FROM precios_cambio_pendiente WHERE pen… |
| VariacionPrecio.frm | 9156 | SELECT | " FROM precios_cambio_pendiente " & _ |
| TPV_Seleccion_Articulo_Simple.frm | 836 | SELECT | " FROM precios_cambio_pendiente " & _ |
| TPV_Seleccion_Articulo_Simple.frm | 917 | SELECT | '        conn.Execute "DELETE FROM precios_cambio_pendiente … |
| TPV_Seleccion_Articulo_Simple.frm | 917 | DELETE | '        conn.Execute "DELETE FROM precios_cambio_pendiente … |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2125 | SELECT | " FROM precios_cambio_pendiente " & _ |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2432 | SELECT | " FROM precios_cambio_pendiente " & _ |
| Funciones.bas | 8680 | SELECT | rs_consulta.Open "SELECT precios_cambio_pendiente.id_articul… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)