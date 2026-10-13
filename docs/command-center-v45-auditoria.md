# Command Center: auditoría de la línea base V45

Estado: investigación y preparación en `codex/command-center-v45`. Ninguno de los once tableros de administraNET se considera entregado por esta auditoría.

## Fuentes y trazabilidad

| Fuente | Identificación | Uso |
|---|---|---|
| `SYNAP_TABLERO_ADMINISTRANET_CONTEXTO_CODEX_R1_20261012.md` | SHA-256 `0CD5946B7F09D91FB6AE8D2C47CA09DCF40667EC88BE4BF38837D08DE2621D61` | Requisitos P1–P19 y anexo histórico de 162 KPI. |
| `411 - V45.zip` | Archivo 7z, SHA-256 `8A26ED92C8B7373A89E14D82BEC008031E3C94C0F76BE42F0E705D021BADDCD8` | Formularios y módulos VB6 `CM_*` / `modCM_*`. |
| Backup Smartclean del 12/10/2026 | SHA-256 `E0DD755B8E97D42AF2448BEFA73E8296F59A699E30B983C8DEC` | Consultas con datos de circuitos operativos. |
| Backup Best Sox del 09/10/2026 | SHA-256 `C44E8E94AA19F4ECE14130326DDD3C3DB057BB1F170DBBD3002FF4A90CBE25DA` | Conciliación contable y financiera. |
| Synap `origin/Desarrollo` | `6059158643a66e34ba2c82ae96cc9c603bcf5df3` | Línea base web. |

Los backups se restauraron en esquemas separados de MySQL 5.7 aislado, sin puertos publicados. No se incorporaron al repositorio. Best Sox: 598 tablas, 2.319 filas en `cuentacliente` y 8.574 **renglones** en `cont_asiento` (3.101 combinaciones distintas de ejercicio y número de asiento); hay 1.813 facturas `FA`/`FB` y 224 notas de crédito `NCA`/`NCB` en `cuentacliente`. Smartclean: 543 tablas, 68.280 filas en `cuentacliente` y 0 en `cont_asiento`. Esas cifras identifican el material de prueba; no son resultados de KPI.

## Inventario por tablero

Los conteos son del anexo histórico R6.8.65; deben cotejarse con V45 antes de darlos por vigentes.

| Tablero administraNET | KPI históricos | Permiso heredado | Estado en Synap `Desarrollo` |
|---|---:|---|---|
| Resumen general | 16 | `tablero_resumen_general` | 16 KPI, comparación automática o personalizada, dos gráficos y dieciséis aperturas conciliadas; falta validación Django/web. |
| Comercial — Ventas | 16 | `tablero_comercial_ventas` | Implementación V45 en rama de trabajo: KPI, comparación, gráfico y detalles. Validación Django y revisión del PR pendientes. |
| Comercial — Preparación de pedidos | 16 | `tablero_comercial_prep_pedidos` | 16 KPI, comparación, gráficos y nueve aperturas de pedidos por estado/vínculo; faltan prueba Django/web y conciliación visual con ERP. |
| Abastecimiento — Compras | 14 | `tablero_abastecimiento_compras` | 14 KPI, evolución de compras/OC y cinco aperturas documentales en rama de trabajo; faltan validación Django/web y alcance de sucursal para usuarios restringidos. |
| Abastecimiento — Stock | 14 | `tablero_abastecimiento_stock` | Resumen y detalle paginado de 14 KPI, tres presentaciones, comparación de movimientos y gráficos en rama de trabajo. Falta prueba Django, revisión visual móvil y revisión del PR. |
| Análisis financiero | 15 | `tablero_gestion_financiera` | 15 KPI, aging, flujo, comparación y seis aperturas de movimientos/cartera; faltan validación Django/web y contraste visual con ERP. |
| Gestión contable | 14 | `tablero_gestion_contable` | 14 KPI, serie Debe/Haber, comparación de períodos y aperturas de asientos, impuestos, períodos y ejercicios; falta validación Django/web. |
| Impuestos — Posiciones fiscales | 14 | `tablero_impuesto_posicion_fiscal` | 14 KPI, composición, comparación, series mensuales de IVA/IIBB y siete aperturas documentales, incluida Posición IVA; falta prueba web. |
| Contabilidad — Libros y estados | 14 | `tablero_contabilidad_libros_estados` | 14 KPI, dos series con comparación, y Diario, Mayor, Balance y Resultados paginados en rama de trabajo; falta prueba web. |
| Logística — Hojas de ruta | 14 | `tablero_logistica_hoja_ruta` | 14 KPI, comparación de estados y aperturas de rutas, comprobantes, chofer, unidad y zona; falta contraste con rutas recientes. |
| Análisis de gastos | 15 | `tablero_gestion_financiera` en V45 | 15 KPI, selector de fuente, documentos, siete agrupaciones y serie comparativa; falta prueba web. |

**No presentar las siete áreas parciales de Synap como equivalentes a estos once tableros.** El código actual añade además `manufactura` y `cruzados` como áreas web propias; no corresponden directamente a tableros homónimos del ERP.

## Diferencias verificadas y controles pendientes

1. `CM_ResumenEjecutivo.frm` abre un selector sin consulta inicial. Synap consultaba varias áreas al cargar la página. La pantalla debe quedar vacía hasta elegir un tablero y cada API debe autorizarlo por separado.
2. Las banderas `tablero_*` existen tanto en `permiso_sistema` como en `synap_permiso` de Best Sox. La autorización web debe tomar la empresa, el puesto y el usuario actuales, y denegar por defecto cuando falte una regla aplicable.
3. `modCM_FiltroPuntoVenta.bas` usa `punto_venta_usr` y deriva sucursales por `punto_venta.id_sucursal`. La copia Best Sox tiene 58 asignaciones de PV distribuidas entre 34 usuarios. La rama aplica PV a Ventas, Preparación, Resumen, Finanzas, Impuestos y documentos de Logística; deriva sucursales para Compras, Contabilidad, Libros y Gastos; y usa depósitos de `deposito_usr` para Stock. En Contabilidad los indicadores y aperturas fiscales generales se muestran no disponibles con filtro territorial. En Logística se ocultan choferes, unidades, diferencias de rendición y agrupaciones por dimensión de rutas compartidas; los comprobantes se cruzan con el PV autorizado.
4. Varias consultas actuales usan `Fecha <= fecha_fin`. En ambos backups `comp_ped.Fecha`, `cuentacliente.Fecha` y `stockp.Fecha` son `DATE`, por lo que ese predicado incluye el último día para esas tres tablas. Antes de reutilizarlo en columnas `DATETIME`, deben verificarse sus tipos y emplearse un fin exclusivo al día siguiente.
5. El detalle, las comparaciones, los gráficos y las exportaciones de los once tableros requieren la misma autorización y el mismo contexto que el KPI padre. No deben inventarse valores cero ante consultas faltantes o fallidas.
6. El acceso a costos, rentabilidad, montos de caja, cuenta corriente, comprobantes y asientos necesita gates independientes antes de publicarse.

## Criterio de avance

Cada KPI se marcará `implementado` sólo con fórmula y fuente verificadas en V45, filtro territorial del servidor, permisos, respuesta explícita de no disponibilidad, detalle y comparación cuando correspondan, y conciliación numérica en la base adecuada. Los candidatos pasan por PR y pruebas en Desarrollo; Staging se considera después de esas verificaciones.

## Conciliación inicial de Comercial/Ventas (rama de trabajo)

Período 01–08/10/2026 en el backup Best Sox, importes sin impuestos, todos los PV: ventas netas $171.207.874,10; 82 facturas; 180 pedidos por $513.873.093,50; 108 pendientes por $368.254.613,61; 95 remitos; 72 pedidos con vínculo a remito; 50 vinculados a factura; rentabilidad $41.161.219,60 y margen 22,06 %. La prueba ejecutó las consultas del servicio contra MySQL 5.7 aislado, incluidos los 16 detalles, comparación y selección de PV 2. En Stock, depósito 6 «Terminado»: 724 artículos con stock, **295.864 unidades positivas**, 724 filas de detalle positivo y $847.696.733,54 valorizados con la conversión de costo por display de V45. La fórmula parcial anterior sin conversión arrojaba $1.799.767.896,86; esa cifra era incorrecta para esta empresa. La base restaurada es histórica y estas cifras son una conciliación técnica, no una prueba de la instalación web en Best Sox.

El resumen de Stock se contrastó en el mismo backup para unidad, display y bulto. En depósito 6, del 01 al 08/10/2026 se registraron 55.803 entradas y 38.467 salidas expresadas en unidades, con valores de costo de $259.911.163,90 y $210.232.913,90. La comparación usa el período inmediatamente anterior de igual duración. Los indicadores de existencias son una foto actual y no se presentan como si fueran históricos. La serie, la distribución por depósito y los catorce detalles se ejecutaron contra MySQL 5.7 aislado. Las sumas de cada detalle coincidieron con su indicador (tolerancia de centavo); los datos de costo requieren permiso en el endpoint de detalle. También se corrigió el mapeo del enlace de detalle de Ventas, que antes no llegaba al frontend.

El PR continúa en borrador: aún falta ejecutar el suite Django integrado, revisar la experiencia móvil y completar los nueve tableros restantes antes de cualquier promoción. No se ha instalado este código en Best Sox.

## Conciliación inicial de Resumen general

Se ejecutó `fetch_resumen_v45` contra la copia aislada Best Sox del 09/10/2026, período 01–12/10/2026. Los ocho indicadores documentales del período fueron ventas $171.207.874,10; compras netas $145.509.780,59; cobranzas $177.508.146,64; pagos $153.688.170,16; 0 presupuestos, 180 pedidos, 82 facturas y 95 remitos. La foto de vencimientos devolvió $33.410.146,54 a cobrar (3) y $41.087.933,52 a pagar (15); cheques $89.378.273,30 y bancos $1.289.836.286,82. Estas cuatro cifras coinciden con la captura del tablero V45. Las dieciséis aperturas de documentos, cuenta corriente, vencimientos y saldos conciliaron exactamente conteos e importes con sus KPI en la base aislada; cuenta corriente de ventas sumó $171.207.874,10 en 91 movimientos y la de compras $131.491.804,10 en 18 movimientos. La captura en vivo muestra venta de cuenta corriente $171.102.874,10: la diferencia de $105.000 requiere cotejar la misma fecha y base antes de declarar paridad. El backend evita consultar saldos globales cuando hay filtro de PV o sucursal, porque V45 no documenta una relación territorial para esos saldos. Faltan prueba web responsive y suite Django integrado; este tablero sigue en desarrollo.

## Conciliación inicial de Preparación de pedidos

Sobre el mismo backup y período 01–12/10/2026, el servicio V45 devolvió 180 pedidos válidos, 108 pendientes, 72 vinculados a remito y 50 vinculados a factura. Los últimos dos valores coinciden con el tablero Comercial/Ventas y se determinan por `stock.codmov_pedido`, sin confiar en el texto del estado. El monto de pedidos por `ImporteVenta` fue $621.786.442,25; Comercial/Ventas usa `SubtotalDesc` y por eso informa un neto distinto. Las unidades pendientes fueron 43.083. No existen pares válidos de horas de preparación en ese período, por lo que el tiempo promedio es `N/D`. Las nueve aperturas paginadas concilian los conteos de pedidos, pendientes, vinculados a remito, vinculados a factura y anulados con los KPI; las dos vistas vinculadas no presentan como total el importe del pedido, porque el KPI suma comprobantes únicos. Se probaron búsqueda y paginación en MySQL 5.7 aislado. Falta contraste visual con AdministraNET y prueba web. El filtro de PV/sucursal se aplica a la cabecera del pedido también al cruzar remitos y facturas.

## Conciliación inicial de Compras

Contra la misma copia Best Sox y período 01–12/10/2026: compras netas $145.509.780,59, 39 facturas, ticket medio $3.731.020,02 y 28 proveedores distintos. La cifra de compras coincide con Resumen gerencial. La copia no contiene OC ingresadas durante el período, ni OC abiertas; el importe de OC y pendiente es cero. El estado de remitos indica 8 sin factura, como foto actual. No hay recepciones válidas para plazo promedio, que se expone como `N/D`. Las aperturas de comprobantes y proveedores suman $145.509.780,59; la búsqueda, segunda página y ocho remitos del intervalo julio–agosto fueron verificados. Este tablero aplica sólo sucursal; el servidor deriva las sucursales de los PV asignados al usuario y conserva ese filtro en resumen y detalle. Falta prueba web con usuario restringido.

## Conciliación inicial de Análisis financiero

En Best Sox 01–12/10/2026, cobranzas $177.508.146,64 y pagos $153.688.170,16 producen un flujo neto de $23.819.976,48; los dos primeros importes coinciden con Resumen gerencial. Los saldos a corte se reconstruyen desde el último movimiento por entidad, como en V45: clientes $2.326.472.757,89 y proveedores $383.360.504,23. El aging de documentos abiertos entrega vencido a cobrar $1.198.315.625,60, vencido a pagar $146.503.148,58; +60 días $431.200.189,10 y $41.863.884,35 respectivamente. Bancos $1.289.836.286,82 coincide con la captura. Las aperturas de 21 cobranzas, 25 pagos, 479 vencimientos de clientes y 62 de proveedores concilian exactamente esos cuatro importes con los KPI. La cartera abierta actual tiene 740 cuotas por cobrar y 173 por pagar; sus sumas no equivalen al saldo histórico por entidad y se etiquetan como universos distintos. Con PV/sucursal seleccionados, cajas, cheques y bancos devuelven no disponible para impedir exponer el saldo global. Faltan prueba web y contraste visual con el tablero financiero.

## Conciliación inicial de Gestión contable

En Best Sox 01–12/10/2026, `cont_asiento` devuelve 253 asientos, Debe y Haber de $1.008.193.355,56 cada uno, diferencia cero, 253 de proceso y resultado contable de -$796.354,24. Los importes y resultado coinciden con la captura V45 de Contabilidad. Hay un ejercicio abierto y ningún período abierto en el rango. La serie diaria se ejecutó en MySQL 5.7 aislado. La selección de grupo y sucursal se aplica a los asientos; los impuestos y períodos son datos generales y se identifican así en la respuesta y la vista sólo sin filtro territorial. Las aperturas de asientos (684 renglones), impuestos (0), períodos (0) y ejercicios (1) se ejecutaron contra la misma copia. La comparación con un período elegido se ejecutó contra MySQL 5.7. La prueba de sucursal/PV verificó que impuestos y períodos generales quedan sin consulta y sin detalle. Faltan contraste visual del tablero específico y prueba web.

## Conciliación inicial de Impuestos y posiciones fiscales

En Best Sox 01–12/10/2026, el débito IVA fue $35.953.653,57, el crédito fiscal $30.531.853,91 y la posición $5.421.799,66. Se contaron 91 comprobantes de Libro IVA ventas y 38 de compras; las notas de crédito tienen signo negativo y compras usa `FechaRegistro`, `IVA1+IVA2+IVA3+sobretasa_iva` y excluye proveedores profesionales, como V45. El test con PV 2 y sucursal 1 devolvió una posición de $5.226.799,41 y no expuso las determinaciones fiscales generales. Las series mensuales IVA/IIBB se conciliaron con los componentes KPI y sus fuentes V45 en MySQL 5.7 aislado. Falta prueba integrada web.

Las aperturas fiscales de ventas y compras suman respectivamente $35.953.653,57 de débito y $30.531.853,91 de crédito, iguales a sus KPI. En el rango hay 17 retenciones de distintos impuestos; su total bruto no equivale a los subtotales de IVA o IIBB, que requieren filtrar por impuesto. También se verificaron percepciones, determinaciones y pagos, todos sin registros en este rango. Los documentos generales de determinación se ocultan cuando se aplica filtro territorial. La apertura unificada de Posición IVA concilia 129 movimientos firmados por $5.421.799,66 con el KPI. Sigue pendiente el contraste visual de los libros.

La comparación personalizada 01–12/09/2026 se ejecutó sobre las mismas consultas: Posición IVA de -$16.676.783,76 frente a $5.421.799,66 en octubre. Se informa el rango elegido y la variación de cada KPI. La vista de composición presenta ambas series fiscales mensuales y su tabla de valores.

## Conciliación inicial de Libros y estados

En Best Sox 01–12/10/2026, los 253 asientos suman $1.008.193.355,56 tanto en Debe como en Haber; 37 cuentas tienen movimiento. El Mayor tiene saldos deudor y acreedor de $448.845.652,63; ingresos $182.597.266,77, egresos $183.393.621,01, resultado -$796.354,24, activo $167.906.532,47 y pasivo $168.702.886,71. Estas cifras coinciden con la captura V45 de Libros y estados. Se validaron las series diarias de Diario y Resultados, la comparación con un período elegido y una selección de sucursal sobre el asiento en MySQL 5.7 aislado. Falta la prueba de interfaz.

Las cuatro vistas documentales ya ejecutan consultas paginadas de solo lectura: Diario y Mayor 684 renglones cada uno, Balance 37 cuentas y Resultados 16. La búsqueda por cuenta y la segunda página del Mayor se probaron en la misma copia; el detalle hereda el permiso del tablero y el filtro histórico de sucursal/grupo.

Gestión contable y Libros admiten comparación personalizada. En 01–12/09/2026, el Debe de Gestión contable fue $1.769.334.883,22 y el de Libros $1.778.919.172,23. La diferencia entre ambos tableros reproduce sus fuentes V45: Gestión contable filtra `a.anulado='No'` y Libros no aplica ese predicado en `CMAC_CargarResumen`. No deben presentarse como el mismo universo sin esa aclaración.

## Conciliación inicial de Logística

La copia Best Sox sólo tiene una hoja de ruta, con `fecha_salida` 23/07/**2911** y fecha de creación 23/07/2026. V45 prioriza `fecha_salida`, por lo que para octubre 2026 el tablero informa correctamente cero rutas; la consulta para julio 2911 devuelve una ruta abierta. Los 888 documentos vinculados a esa ruta producen 769 facturas, 119 notas de crédito y $2.708.695.918,94 de facturación neta. La fecha de salida aparentemente errónea es dato de origen y debe revisarse en AdministraNET antes de usar este caso para una prueba de negocio. Se verificaron consultas de rango y filtro territorial en MySQL 5.7 aislado; faltan gráfico y prueba web.

Las aperturas devuelven la hoja, los 888 documentos y un ranking por ruta, con la misma suma de $2.708.695.918,94. El detalle de documentos intersecta el PV/sucursal autorizado incluso si una ruta contiene comprobantes de otros puntos de venta. Con PV 2, el resumen devuelve sólo 684 documentos; choferes, unidades y diferencia de rendición de la ruta compartida quedan no disponibles, al igual que sus agrupaciones por dimensión. Las agrupaciones sin filtro de la ruta histórica devuelven un chofer, una unidad y cinco zonas asignadas. El catálogo `logi_zona` está vacío en este backup: se muestra «Zona N» sin atribuir el texto compuesto de la hoja a cada ID. Una ruta con varias zonas puede aparecer en varios grupos. Falta prueba web.

## Conciliación inicial de Análisis de gastos

En Best Sox 01–12/10/2026, Fuente Todos excluyendo impuestos devuelve $207.803.715,61 de gasto operativo en 44 documentos, gasto bancario cero e impuestos pagados cero. El promedio documental es $4.722.811,72 y la variación frente al período anterior equivalente es -$74.680.875,57 (-26,44 %). El grupo de mayor importe es «Grupo 7 (mercaderías terminadas)», $73.794.608,80. Se ejecutaron las cuatro fuentes y el filtro de sucursal/PV contra MySQL 5.7 aislado. El cociente gastos/ventas usa la fórmula fiscal de ventas de `CMGas_CargarVentasNetas` y no suma pagos a proveedores como gasto. La serie de evolución actual y la del período de comparación elegido suman los mismos importes que sus KPI. Faltan comparación de dimensiones y prueba web.

El detalle de gastos se validó con 44 documentos; las agrupaciones por grupo, gasto, fuente, sucursal, día y mes suman exactamente el mismo total de $207.803.715,61. Se paginan con el mismo filtro de fuente y alcance que el resumen. Sigue pendiente el contraste visual.
