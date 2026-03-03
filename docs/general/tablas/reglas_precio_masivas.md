# Tabla `reglas_precio_masivas`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_regla_precio_masivas | DOUBLE | No | ✓ |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| tipo_regla | VARCHAR | Sí |  |  |  |
| tipo_calculo | VARCHAR | Sí |  |  |  |
| importe_regla | DECIMAL | Sí |  |  |  |
| vigencia_desde | DATE | Sí |  |  |  |
| vigencia_hasta | DATE | Sí |  |  |  |
| orden_regla | INT | Sí |  |  |  |
| id_rubro | DOUBLE | Sí |  |  |  |
| id_sub_rubro | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_marca | DOUBLE | Sí |  |  |  |

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
| Cliente.frm | 4006 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4132 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| Cliente.frm | 4176 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4191 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4206 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4221 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4237 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4255 | SELECT | "FROM reglas_precio_masivas " & _ |
| Cliente.frm | 4270 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 16856 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 16999 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| FacturaB_COPIA.frm | 17043 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17058 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17073 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17088 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17104 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17122 | SELECT | "FROM reglas_precio_masivas " & _ |
| FacturaB_COPIA.frm | 17137 | SELECT | "FROM reglas_precio_masivas " & _ |
| Rprecios_abm.frm | 2722 | SELECT | conn.Execute "DELETE FROM reglas_precio_masivas WHERE id_reg… |
| Rprecios_abm.frm | 2722 | DELETE | conn.Execute "DELETE FROM reglas_precio_masivas WHERE id_reg… |
| Rprecios_abm.frm | 2864 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34069 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| TPV.frm | 34210 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| TPV.frm | 34258 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34273 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34288 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34303 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34318 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34334 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34352 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34367 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34382 | SELECT | "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34649 | SELECT | '            rs_regla.Open "SELECT * FROM reglas_precio_masi… |
| TPV.frm | 34786 | SELECT | '    rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE An… |
| TPV.frm | 34830 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34845 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34860 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34875 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34891 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34909 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| TPV.frm | 34924 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 1846 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 1942 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| Modifica_LP_Global.frm | 1986 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2001 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2016 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2031 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2047 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2065 | SELECT | "FROM reglas_precio_masivas " & _ |
| Modifica_LP_Global.frm | 2080 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1008 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1131 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| Importador_Excel.frm | 1179 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1194 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1209 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1224 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1239 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1255 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1273 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1288 | SELECT | "FROM reglas_precio_masivas " & _ |
| Importador_Excel.frm | 1303 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 11870 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12011 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE Anulado… |
| Visualiza_Pedido.frm | 12059 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12074 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12089 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12104 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12119 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12135 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12153 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12168 | SELECT | "FROM reglas_precio_masivas " & _ |
| Visualiza_Pedido.frm | 12183 | SELECT | "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13276 | SELECT | '    rs_r.Open "SELECT * FROM reglas_precio_masivas WHERE An… |
| CargaArticulo_Original.frm | 13303 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13317 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13331 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13345 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13360 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13377 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| CargaArticulo_Original.frm | 13391 | SELECT | '                      "FROM reglas_precio_masivas " & _ |
| … | … | … | *(260 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)