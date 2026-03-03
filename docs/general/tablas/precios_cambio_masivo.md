# Tabla `precios_cambio_masivo`

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
| imprime | VARCHAR | Sí |  |  |  |
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
| TPV_Seleccion_Articulo_Simple.frm | 840 | SELECT | rs_act_Etiqueta_Masiva.Open "SELECT * FROM precios_cambio_ma… |
| TPV_Seleccion_Articulo_Simple.frm | 875 | SELECT | rs_act_Etiqueta_Masiva.Open "SELECT * FROM precios_cambio_ma… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1524 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1524 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1533 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1533 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1542 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1542 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1551 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1551 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1560 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1560 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1569 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1569 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1578 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1578 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1587 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1587 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1596 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1596 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1605 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1605 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1614 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1614 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1623 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1623 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1632 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1632 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1641 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1641 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1650 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1650 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1659 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1659 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1674 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1689 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1704 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1719 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1719 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1734 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1734 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1749 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1764 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1779 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1794 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1809 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1824 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1840 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET imprime = 'No… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1886 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET precios_cambi… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1888 | UPDATE | conn.Execute "UPDATE precios_cambio_masivo SET precios_cambi… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 1987 | SELECT | rs_act_Etiqueta_Masiva.Open "SELECT * FROM precios_cambio_ma… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2067 | SELECT | '            conn.Execute "UPDATE  FROM precios_cambio_masiv… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2072 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2072 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE id_pre… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2120 | SELECT | rs_act_Etiqueta_Masiva.Open "SELECT * FROM precios_cambio_ma… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2228 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE precio… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2228 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE precio… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2388 | SELECT | " FROM precios_cambio_masivo " & _ |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2402 | SELECT | rs_total.Open "SELECT SQL_CALC_FOUND_ROWS id_articulo FROM p… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2429 | SELECT | conn.Execute "DELETE FROM precios_cambio_masivo WHERE precio… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2429 | DELETE | conn.Execute "DELETE FROM precios_cambio_masivo WHERE precio… |
| Articulo_Impresion_Etiquetas_Masiva.frm | 2439 | SELECT | rs_consulta2.Open "SELECT * FROM precios_cambio_masivo WHERE… |
| Funciones.bas | 13727 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 13817 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 13907 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 13998 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 14088 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 14177 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 14265 | SELECT | " FROM precios_cambio_masivo " & _ |
| Funciones.bas | 14273 | SELECT | " FROM precios_cambio_masivo " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)