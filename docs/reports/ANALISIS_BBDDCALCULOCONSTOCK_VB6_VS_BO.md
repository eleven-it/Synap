# Análisis BBDDCALCULOCONSTOCK: información extraída, cálculos en Excel y comparación con el reporte BO

**Fecha:** 2026-03-02  
**Objetivo:** Unificar en un solo documento (1) la información que extraen los dos informes VB6 que alimentan el Excel BBDDCALCULOCONSTOCK, (2) los cálculos y filtros que se aplican en el Excel (hoja Hoja1), y (3) la comparación con el reporte BO. El reporte BO es la evolución del Excel; la validación consiste en comprobar que **datos y cálculos** del BO coincidan con el resultado de **Hoja1**, considerando los filtros de estado aplicados en el Excel (no en las consultas VB6).

---

## 1. Origen del Excel BBDDCALCULOCONSTOCK

El libro **bbddcalculoconstock.xls** se arma a partir de dos informes VB6:


| Orden | Informe VB6                         | id_reporte | Formulario     | Archivo .rpt en uso                     |
| ----- | ----------------------------------- | ---------- | -------------- | --------------------------------------- |
| 1     | **Pedidos por cliente general**     | 208        | Info_Venta.frm | ventas_pedidos_cliente_todos.rpt        |
| 2     | **Lista de existencias valorizado** | 27         | Info_Stock.frm | stock_listado_existencia_valorizado.rpt |


Los datos exportados de cada informe se vuelcan al Excel y allí se realizan cruces y cálculos (“cálculo con stock”). El resultado es el artefacto que el reporte BO de Synap debe poder replicar (tabla única o exportación equivalente).

---

## 2. Información que extrae cada informe VB6

### 2.1 Pedidos por cliente general (id 208)

**Fuente de datos:** comp_ped + stockp (+ cliente, articulo y demás maestros según el .rpt).

**Filtros aplicados (caso estándar: todas sucursales, todos PV, lista completa, rango de fechas):**

- comp_ped.TipoComprobante = 'PED'
- comp_ped.Anulado = 'No'
- comp_ped.Fecha en [Desde, Hasta] (ej. 01/01/2026 a hoy)
- comp_ped.CodigoMovimiento <> 0
- comp_ped.CodSucursal <> 0 (todas las sucursales; no se filtra por una)
- Sin filtro por id_pv (todos los puntos de venta)
- Sin filtro por cliente (todos los clientes)
- Sin filtro por estado del comprobante (a diferencia del id 6)

**Importante:** Los filtros por **estado** del pedido (En preparación, Preparado, Pendiente, etc.) **no** se aplican en la consulta VB6; se aplican **en el Excel** al armar la hoja de resultado (Hoja1), mediante las fórmulas SUMAR.SI.CONJUNTO que usan los criterios en I1, J1, L1 (véase sección 3). Para comparar con el reporte BO hay que considerar estos filtros de estado aplicados en el Excel.

**Información que aporta al Excel (inferida):**

- **Por pedido (cabecera):** cliente (Codigo, nombre), sucursal, punto de venta, fecha, NroComprobante, Estado, etc.
- **Por renglón (stockp):** artículo (IDArt, id_manual, descripción), cantidad pedida, precios (PrecioNetoxR u otros según .rpt), posible estado del renglón (remitido_facturado, etc.).
- **Totales o subtotales:** por cliente, por artículo, por período, según diseño del Crystal.

En síntesis: **demanda de venta en el período** (pedidos) a nivel cliente, artículo, y opcionalmente sucursal/PV, con cantidades e importes.

### 2.2 Lista de existencias valorizado (id 27)

**Fuente de datos:** articulo + stock_deposito (+ deposito, rubro, subrubro, proveedor, marca, modelo; opcionalmente stock para variante “a fecha”).

**Filtros aplicados:**

- articulo.tipo_art <> 'Gasto'
- Depósito: todos (id_deposito <> 0) o uno (id_deposito = X)
- Opcional: stock_deposito.saldo > 0 (solo con saldo)
- Opcionales: artículo, rubro, subrubro, proveedor, marca, modelo
- Variante “fecha determinada”: stock.Fecha en [Desde, Hasta]

**Parámetros que afectan la valorización:**

- **lista_precio:** En VB6 viene del combo **ListaPrecio** del formulario Info_Stock (ListIndex se pasa al Crystal como parámetro `lista_precio`). Opciones en Info_Stock: 0 = Costo (PrecioCosto), 1 = Lista Oficial (PNOficial), 2 = Lista 1 (Precio1V), 3 = Lista 2 (Precio2V), 4 = Lista 3 (Precio3V), 5 = Lista 4 (Precio4V), 6 = Lista 5 (Precio5V). Las etiquetas “Lista 1” a “Lista 5” usan Principal.desc_util1..desc_util5 (configuración). En el reporte BO se usa el filtro `lista_precio` (0-6) con el mismo mapeo; por defecto 2 (Lista 1 / Precio1V).
- TipoPres (Venta/Compra) si aplica embalaje

**Información que aporta al Excel (inferida):**

- **Por artículo (y opcionalmente por depósito):** id_manual, descripción, rubro/subrubro, proveedor, marca, modelo, depósito.
- **Saldos:** stock_deposito.saldo (cantidad disponible por artículo y depósito, o suma si “todos”).
- **Valorización:** saldo × precio según lista de precios (y TipoPres) → valor en dinero del stock.

En síntesis: **stock actual (existencias)** por artículo (y depósito), con **valorización** según lista de precios, lista completa de artículos no “Gasto” que cumplan los filtros.

---

## 3. Cálculos típicos en el Excel (inferidos)

El nombre “BBDDCALCULOCONSTOCK” sugiere una **base de datos de cálculo con stock**: cruce entre **demanda (pedidos)** y **oferta (existencias)** para evaluar cobertura o faltantes. Sin poder leer el .xls, los cálculos que suelen hacerse en este tipo de libro son:


| Cálculo / concepto                     | Descripción esperada                                                                                                                                                                                                     |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Demanda por artículo**               | Desde la exportación de “Pedidos por cliente general”: suma de cantidades pedidas por artículo (y opcionalmente por cliente/sucursal/periodo). Puede usarse Cantidad o cantidad_pendiente según qué se exporte del .rpt. |
| **Stock disponible por artículo**      | Desde “Lista de existencias valorizado”: saldo por artículo (suma sobre depósitos si el reporte es “todos”), o por artículo y depósito.                                                                                  |
| **Cobertura (cantidad)**               | Comparación: stock disponible vs demanda (ej. mínimo entre stock y demanda, o indicador “cubre” / “no cubre”).                                                                                                           |
| **Faltante / excedente**               | Demanda − stock (si > 0 sería faltante; si < 0, excedente de stock).                                                                                                                                                     |
| **Valorización de stock**              | Stock × precio (lista de precios) = valor del inventario por artículo (ya viene del informe “Lista de existencias valorizado”).                                                                                          |
| **Valorización de demanda o faltante** | Demanda (o faltante) × precio (lista o precio del pedido) para obtener importes en dinero.                                                                                                                               |
| **Totales / resúmenes**                | Totales por rubro, por cliente, por depósito, etc., según cómo esté armado el Excel.                                                                                                                                     |


El **eje de cruce** entre los dos informes es normalmente el **artículo** (IDArt / id_manual): a cada artículo se le asocia la demanda extraída de los pedidos y el stock (y valorización) extraído de existencias valorizado.

**Nota:** Las fórmulas concretas extraídas de capturas del Excel se documentan en las subsecciones 3.1–3.3 siguiente.

### 3.1 Fórmulas extraídas de las imágenes (literal)

Obtenidas de la barra de fórmulas en capturas del libro; no se infieren datos de celdas.

| Celda (Hoja1) | Columna | Fórmula Excel |
|---------------|---------|----------------|
| I10 | En preparación | `=SUMAR.SI.CONJUNTO(Sheet1!F:F;Sheet1!D:D;Hoja1!B10;Sheet1!G:G;Hoja1!$I$1)` |
| J10 | Preparado | `=+SUMAR.SI.CONJUNTO(Sheet1!F:F;Sheet1!D:D;Hoja1!B10;Sheet1!G:G;Hoja1!$J$1)` |
| K10 | DISPONIBLE | `=D10-I10-J10` |
| L10 | Pendiente | `=+SUMAR.SI.CONJUNTO(Sheet1!F:F;Sheet1!D:D;Hoja1!B10;Sheet1!G:G;Hoja1!$L$1)` |
| M10 | Pendiente Valorizado | `=+SUMAR.SI.CONJUNTO(Sheet1!J:J;Sheet1!D:D;Hoja1!B10;Sheet1!G:G;Hoja1!$L$1)` |
| N10 | Unitario | `=SI(L10=0;0;M10/L10)` |

### 3.2 Interpretación

- **SUMAR.SI.CONJUNTO** (SUMIFS): suma un rango cuando se cumplen varios criterios. I10, J10 y L10 suman **Sheet1!F:F** cuando **Sheet1!D** = Cod. Manual (Hoja1!B10) y **Sheet1!G** = valor en I1, J1 o L1 (p. ej. estado “En preparación”, “Preparado”, “Pendiente”). M10 suma **Sheet1!J:J** con criterios D = B10 y G = $L$1.
- **K10:** DISPONIBLE = Saldo (D10) − En preparación (I10) − Preparado (J10).
- **N10:** Unitario = si Pendiente (L10) = 0 entonces 0, si no M10/L10 (Pendiente Valorizado / Pendiente).

### 3.3 Hojas y columnas

- **Hoja1:** columnas A–N (Cod. Sistema, Cod. Manual, Articulo, Saldo, Costo, Saldo_Valorizado, Rubro, Subrubro, En preparación, Preparado, DISPONIBLE, Pendiente, Pendiente Valorizado, Unitario). Fila 1 = encabezados; I1, J1, L1 se usan como criterio en SUMAR.SI.CONJUNTO.
- **Sheet1:** columnas D, F, G, J usadas en las fórmulas (identificador artículo, valor sumado, criterio estado/rubro, valor sumado en M10).

### 3.4 Filtros de estado en el Excel (para la comparación con BO)

Las consultas de los informes VB6 (id 208 y 27) **no** aplican filtros por estado del pedido. Esos filtros se aplican **solo en el Excel** al construir el resultado:

- Los valores en **Hoja1!I1**, **Hoja1!J1**, **Hoja1!L1** (encabezados “En preparación”, “Preparado”, “Pendiente”) actúan como **criterios** en SUMAR.SI.CONJUNTO: se segmenta la demanda por artículo según el estado del renglón/pedido en Sheet1 (columna G).
- Por tanto, al validar el reporte BO frente al Excel, hay que comparar el resultado considerando estos mismos criterios de estado: el **referente de validación** es el resultado final de la **hoja Hoja1** (datos + cálculos), no las exportaciones crudas de los informes VB6.

---

## 4. Comparación con el reporte BO de Synap

**Objeto de la comparación:** El reporte BO es la **evolución** del reporte Excel BBDDCALCULOCONSTOCK. El formato y la forma de mostrar los datos se mantienen como BO; **solo debe validarse que los datos y los cálculos sean correctos**. La comparación real es:

- **Referente Excel:** resultado final de la hoja **Hoja1** (columnas A–N y las fórmulas documentadas en 3.1–3.3), incluyendo los filtros de estado aplicados en el Excel (3.4).
- **Referente BO:** salida del reporte BO que replique o evolucione BBDDCALCULOCONSTOCK.

A continuación se resume la situación del único reporte BO que hoy combina pedidos y stock, **bo-stock-facturacion** (slug `bo-stock-facturacion`), para ver qué coincide y qué habría que ajustar o añadir para que la validación “Hoja1 vs BO” sea posible.

### 4.1 Qué datos usa cada uno


| Dato / concepto              | BBDDCALCULOCONSTOCK (Excel desde VB6)                                                                                                                                              | Reporte BO (bo-stock-facturacion)                                                                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pedidos**                  | **Todos** los PED en el período (id 208: sin filtro por estado). Todos los clientes, todas sucursales, todos PV.                                                                   | Solo PED en estado **Pendiente** (backorder). Filtro por stockp.Fecha en el período. Opcional: clientes excluidos.                                |
| **Detalle pedidos**          | comp_ped + stockp; todos los renglones de esos PED.                                                                                                                                | stockp + comp_ped solo para Estado = 'Pendiente'; renglones con cantidad/importe (PrecioNetoxR).                                                  |
| **Stock**                    | Lista de existencias **valorizado**: saldo por artículo (y depósito), valorización por **lista de precios** (parámetro). Incluye todos los artículos no Gasto que cumplan filtros. | SUM(stock_deposito.saldo) por artículo. Sin valorización por lista de precios. Solo se usa para artículos que tienen **backorder** en el período. |
| **Valorización**             | Lista de precios (lista_precio) × saldo; parámetro TipoPres.                                                                                                                       | PrecioNetoxR de stockp para importes de backorder (y prorrateos CON STOCK / CON INGRESO / SIN STOCK).                                             |
| **Alcance por artículo**     | Todos los artículos con stock (y opcionalmente con saldo 0) según filtros de existencias; demanda por artículo desde todos los PED del período.                                    | Solo artículos con backorder > 0 en el período (HAVING bo_qty > 0).                                                                               |
| **Reservado / OC pendiente** | No forma parte de los dos informes VB6 que alimentan el Excel.                                                                                                                     | Sí: reservado (PED En preparación/Preparado/Parcial), OC pendiente (para cobertura “CON INGRESO”).                                                |
| **Facturación / remitos**    | No.                                                                                                                                                                                | Sí: facturación neta, remitos no facturados.                                                                                                      |


### 4.2 Cálculos: Excel vs BO


| Cálculo                   | Excel (BBDDCALCULOCONSTOCK)                                                                          | BO (bo-stock-facturacion)                                                                                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Demanda**               | Suma de cantidades (y posiblemente importes) de **todos** los PED del período por artículo.          | “Demanda” = backorder (solo Pendiente): bo_qty, bo_importe (PrecioNetoxR).                                                    |
| **Stock disponible**      | Saldo desde “Lista de existencias valorizado” (por artículo/depósito, con opción “todos” depósitos). | stock_actual = SUM(stock_deposito.saldo) por artículo (con opción depositos_excluidos).                                       |
| **Cobertura**             | Implícita en el cruce: stock vs demanda por artículo (fórmulas en el .xls).                          | Explícita: disponible = stock − reservado; clasificación CON STOCK / CON INGRESO / SIN STOCK según disponible y OC pendiente. |
| **Valorización de stock** | Saldo × precio según **lista de precios**.                                                           | No se calcula valor de inventario por lista de precios.                                                                       |
| **Faltante**              | Típicamente demanda − stock (por artículo).                                                          | Sin stock = bo_qty no cubierto por disponible ni por OC pendiente (y su importe).                                             |


### 4.3 Resumen de diferencias

- **Alcance de pedidos:** Excel usa **todos** los PED del período (208); BO solo **PED Pendiente** (backorder).
- **Alcance de artículos:** Excel puede listar **todos** los artículos con stock (y/o con demanda); BO solo artículos con **backorder > 0**.
- **Valorización:** Excel usa **lista de precios** para valorizar existencias; BO usa **PrecioNetoxR** de stockp para importes de backorder.
- **Objetivo:** Excel = “cálculo con stock” (demanda vs existencias valorizadas, posible cobertura/faltante por artículo). BO = dashboard de facturación, remitos, backorder y cobertura (stock/reservado/OC) para ese backorder.
- **Facturación y remitos:** Solo el BO los incluye; no forman parte de los dos informes VB6 que alimentan BBDDCALCULOCONSTOCK.

### 4.4 Reanálisis con los cálculos documentados (Excel vs BO)

Con las fórmulas del Excel (sección 3.1–3.3) y el SQL del BO documentados, las diferencias se precisan así:

**Columnas Hoja1 y equivalente en BO:**

| Columna Excel (Hoja1) | Origen / fórmula Excel | Equivalente BO | ¿Coincide? |
|------------------------|------------------------|----------------|------------|
| **Saldo (D)** | Lista existencias valorizado: saldo por artículo (stock_deposito). | `stock_actual` = SUM(stock_deposito.saldo) por artículo. | **Sí**, mismo origen. BO puede usar depositos_excluidos. |
| **Costo (E)** | Existencia valorizado (costo/valor). | `costo` = articulo.PrecioCosto. | **Sí** (incorporado en BO). |
| **Saldo_Valorizado (F)** | Saldo × precio lista (valorización). | `saldo_valorizado` = stock_actual × precio según parámetro **lista_precio** (0=Costo, 1=PNOficial, 2-6=Precio1V..Precio5V; mismo criterio que VB6). | **Sí** (incorporado en BO; filtro `lista_precio` en payload). |
| **En preparación (I)** | SUMAR.SI.CONJUNTO(Sheet1!F; artículo; estado=I1). Cantidad por artículo con estado “En preparación”. | `stock_reservado` incluye En preparación + Preparado (sin Parcial; alineado con Excel). | **Sí**: mismo concepto; BO ya no incluye “Parcial” en reservado. |
| **Preparado (J)** | Idem con criterio J1. | Parte de `stock_reservado`. | **Parcial**: BO no expone Preparado por separado; sigue agrupado en reservado. |
| **DISPONIBLE (K)** | D − I − J = Saldo − En preparación − Preparado. | `disponible` = stock_actual − stock_reservado. | **Sí**: misma lógica (stock menos lo reservado). |
| **Pendiente (L)** | SUMAR.SI.CONJUNTO(Sheet1!F; artículo; estado=L1). Cantidad pendiente por artículo. | `bo_qty` (PED Estado = 'Pendiente', SUM(Cantidad) o cantidad_pendiente por artículo). | **Sí**: mismo concepto (demanda pendiente). |
| **Pendiente Valorizado (M)** | SUMAR.SI.CONJUNTO(Sheet1!J; artículo; estado=L1). Importe pendiente. | `bo_importe` (SUM(PrecioNetoxR) por artículo, solo Pendiente). | **Sí**: mismo origen (importe de renglones pendientes). |
| **Unitario (N)** | SI(L=0;0;M/L) = Pendiente Valorizado / Pendiente. | bo_importe / bo_qty (implícito o calculado en front). | **Sí**: mismo cálculo. |

**Resumen de diferencias clave (con cálculos):**

1. **Alcance de filas:** Excel Hoja1 puede listar **todos** los artículos con stock (eje = existencias valorizado); BO solo filas con **backorder > 0**. Para un artículo con stock y sin pedidos pendientes, Excel puede tener fila con Pendiente=0; BO no la muestra.
2. **Estados de pedido:** Excel segmenta **En preparación**, **Preparado** y **Pendiente** por separado (I, J, L). BO solo distingue “Pendiente” (backorder) vs “reservado” (En preparación + Preparado + Parcial); no desglosa Preparado.
3. **Valorización de stock:** Excel tiene Saldo_Valorizado (y opcionalmente Costo) desde lista de precios; BO **no** calcula valor de inventario por lista de precios.
4. **DISPONIBLE vs disponible:** La fórmula es equivalente (stock − reservado). El reservado del BO considera solo **En preparación** y **Preparado** (sin Parcial), alineado con Excel (I+J).
5. **Detalle row-level:** Excel tiene una hoja de pedidos (Sheet1) con renglones por comprobante/artículo; BO tiene `backorder_detalle_rows` (solo Estado = 'Pendiente'). Para comparar “Pendiente” y “Pendiente Valorizado” por artículo, los totales por artículo deberían coincidir si los filtros (fecha, sucursal, PV, clientes) son equivalentes.

**Conclusión:** Para validar “Hoja1 vs BO” en los cálculos que comparten (Saldo, Costo, Saldo_Valorizado, DISPONIBLE, Pendiente, Pendiente Valorizado, Unitario), el BO incorpora costo y saldo_valorizado (Precio1V) y reservado sin Parcial. Queda alinear alcance de filas (o comparar solo artículos con backorder) y opcionalmente parámetro lista de precios (Precio1V..Precio5V). El reporte BO actual es una evolución centrada en backorder y cobertura; replicar Hoja1 al 100 % exigiría desglose Preparado por separado y opción de lista de precios.

---

## 5. Qué debería tener el reporte BO para replicar BBDDCALCULOCONSTOCK

Para que el BO genere un resultado equivalente al Excel BBDDCALCULOCONSTOCK haría falta:

1. **Bloque “Pedidos por cliente general” (equivalente id 208)**
  - Consulta sobre comp_ped + stockp con filtros: TipoComprobante = 'PED', Anulado = 'No', Fecha en rango, CodSucursal <> 0, sin filtro por id_pv ni por cliente ni por estado.  
  - Salida: por artículo (y opcionalmente por cliente/sucursal/PV): cantidades e importes de **todos** los renglones de esos PED (demanda en el período).
2. **Bloque “Lista de existencias valorizado” (equivalente id 27)**
  - Consulta sobre articulo + stock_deposito (+ deposito, rubro, subrubro, proveedor, marca, modelo), con tipo_art <> 'Gasto' y filtros opcionales (depósito, rubro, etc.).  
  - Salida: por artículo (y opcionalmente por depósito): saldo y **valorización** (saldo × precio según lista de precios y parámetro TipoPres).
3. **Cruce y cálculos en el BO (o en exportación tipo Excel)**
  - Cruce por artículo (IDArt / id_manual).  
  - Cálculos: demanda por artículo (desde bloque 1), stock por artículo (desde bloque 2), cobertura (ej. mínimo(stock, demanda) o indicador), faltante (demanda − stock si > 0), valorización de stock (desde bloque 2), y opcionalmente valorización de demanda o faltante.  
  - Totales o agrupaciones por rubro, cliente, depósito, etc., según requiera el negocio.
4. **Parámetros alineados con VB6**
  - Período (desde/hasta).  
  - Todas las sucursales / todos los PV (o filtros opcionales).  
  - Lista de precios y TipoPres para la valorización.  
  - Depósito (todos o uno) para existencias.

5. **Filtros de estado equivalentes al Excel**
  - Replicar en el BO la segmentación por estado (En preparación, Preparado, Pendiente) que en el Excel se aplica vía SUMAR.SI.CONJUNTO con I1, J1, L1, de modo que la validación “Hoja1 vs BO” compare datos y cálculos sobre el mismo criterio de estado.

El reporte actual **bo-stock-facturacion** no cumple este flujo: está centrado en backorder, facturación y remitos, con alcance y valorización distintos. Por tanto, replicar BBDDCALCULOCONSTOCK implica **un nuevo reporte BO** (o una variante/configuración específica) que combine los dos bloques anteriores y los cálculos descritos, y que pueda exportarse a Excel o mostrarse como tabla equivalente.

---

## 6. Referencias

- **SQL de vistas/consultas:** [SQL_VISTAS_REPORTES_VB6_Y_BO.md](SQL_VISTAS_REPORTES_VB6_Y_BO.md) (SQL equivalente reportes VB6 208 y 27, y SQL real del reporte BO bo-stock-facturacion).
- Pedidos por cliente general (id 208): [INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md](INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md).
- Lista de existencias valorizado (id 27) y comparativa con BO: [COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md](COMPARATIVA_VB6_LISTA_EXISTENCIAS_VALORIZADO_VS_BO_SYNAP.md).
- Ingeniería inversa existencias valorizado: `.cursor/plans/` (informe Lista existencias valorizado).
- Reporte BO: `reports/services/query_runner.py` → `_run_backorder_vs_stock_vs_facturacion`.
- Tablas: [docs/general/tablas/](../general/tablas/) (comp_ped, stockp, articulo, stock_deposito, cliente, etc.).
- Excel y .rpt en uso: sección 5 de [INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md](INFORME_VB6_PEDIDOS_POR_CLIENTE_GENERAL_Y_EXCEL_BBDDCALCULOCONSTOCK.md).

