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
| Resumen general | 16 | `tablero_resumen_general` | 16 KPI, período anterior y dos gráficos integrados en rama de trabajo; faltan detalles y validación Django/web. |
| Comercial — Ventas | 16 | `tablero_comercial_ventas` | Implementación V45 en rama de trabajo: KPI, comparación, gráfico y detalles. Validación Django y revisión del PR pendientes. |
| Comercial — Preparación de pedidos | 16 | `tablero_comercial_prep_pedidos` | 16 KPI, comparación de períodos y gráficos por estado en rama de trabajo; faltan detalles, prueba Django/web y conciliación visual con ERP. |
| Abastecimiento — Compras | 14 | `tablero_abastecimiento_compras` | 14 KPI y evolución de compras/OC en rama de trabajo; faltan detalles, validación Django/web y alcance de sucursal para usuarios restringidos. |
| Abastecimiento — Stock | 14 | `tablero_abastecimiento_stock` | Resumen y detalle paginado de 14 KPI, tres presentaciones, comparación de movimientos y gráficos en rama de trabajo. Falta prueba Django, revisión visual móvil y revisión del PR. |
| Análisis financiero | 15 | `tablero_gestion_financiera` | 15 KPI, aging, flujo y comparación en rama de trabajo; faltan detalles, validación Django/web y contraste visual con ERP. |
| Gestión contable | 14 | `tablero_gestion_contable` | Pendiente de migrar; validar con Best Sox. |
| Impuestos — Posiciones fiscales | 14 | `tablero_impuesto_posicion_fiscal` | Pendiente de migrar. |
| Contabilidad — Libros y estados | 14 | `tablero_contabilidad_libros_estados` | Pendiente de migrar; validar con Best Sox. |
| Logística — Hojas de ruta | 14 | `tablero_logistica_hoja_ruta` | Pendiente de migrar. |
| Análisis de gastos | 15 | `tablero_gestion_financiera` en V45 | Pendiente de migrar; confirmar permiso y fuentes. |

**No presentar las siete áreas parciales de Synap como equivalentes a estos once tableros.** El código actual añade además `manufactura` y `cruzados` como áreas web propias; no corresponden directamente a tableros homónimos del ERP.

## Diferencias verificadas y controles pendientes

1. `CM_ResumenEjecutivo.frm` abre un selector sin consulta inicial. Synap consultaba varias áreas al cargar la página. La pantalla debe quedar vacía hasta elegir un tablero y cada API debe autorizarlo por separado.
2. Las banderas `tablero_*` existen tanto en `permiso_sistema` como en `synap_permiso` de Best Sox. La autorización web debe tomar la empresa, el puesto y el usuario actuales, y denegar por defecto cuando falte una regla aplicable.
3. `modCM_FiltroPuntoVenta.bas` usa `punto_venta_usr` y deriva sucursales por `punto_venta.id_sucursal`. La copia Best Sox tiene 58 asignaciones de PV distribuidas entre 34 usuarios. La rama aplica PV a los servicios de Ventas y depósitos de `deposito_usr` a Stock en el servidor. Las demás áreas actuales quedan ocultas para usuarios sin acceso total hasta auditar su alcance.
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

Se ejecutó `fetch_resumen_v45` contra la copia aislada Best Sox del 09/10/2026, período 01–12/10/2026. Los ocho indicadores documentales del período fueron ventas $171.207.874,10; compras netas $145.509.780,59; cobranzas $177.508.146,64; pagos $153.688.170,16; 0 presupuestos, 180 pedidos, 82 facturas y 95 remitos. La foto de vencimientos devolvió $33.410.146,54 a cobrar (3) y $41.087.933,52 a pagar (15); cheques $89.378.273,30 y bancos $1.289.836.286,82. Estas cuatro cifras coinciden con la captura del tablero V45. La venta de cuenta corriente calculada desde el backup fue $171.207.874,10, mientras la captura en vivo muestra $171.102.874,10: la diferencia de $105.000 requiere cotejar la misma fecha y base antes de declarar paridad. El backend evita consultar saldos globales cuando hay filtro de PV o sucursal, porque V45 no documenta una relación territorial para esos saldos. Faltan detalles por indicador, prueba web responsive y suite Django integrado; este tablero sigue en desarrollo.

## Conciliación inicial de Preparación de pedidos

Sobre el mismo backup y período 01–12/10/2026, el servicio V45 devolvió 180 pedidos válidos, 108 pendientes, 72 vinculados a remito y 50 vinculados a factura. Los últimos dos valores coinciden con el tablero Comercial/Ventas y se determinan por `stock.codmov_pedido`, sin confiar en el texto del estado. El monto de pedidos por `ImporteVenta` fue $621.786.442,25; Comercial/Ventas usa `SubtotalDesc` y por eso informa un neto distinto. Las unidades pendientes fueron 43.083. No existen pares válidos de horas de preparación en ese período, por lo que el tiempo promedio es `N/D`. Estos resultados se ejecutaron contra MySQL 5.7 aislado; falta contraste visual con AdministraNET y cierre de detalles. El filtro de PV/sucursal se aplica a la cabecera del pedido también al cruzar remitos y facturas.

## Conciliación inicial de Compras

Contra la misma copia Best Sox y período 01–12/10/2026: compras netas $145.509.780,59, 39 facturas, ticket medio $3.731.020,02 y 28 proveedores distintos. La cifra de compras coincide con Resumen gerencial. La copia no contiene OC ingresadas durante el período, ni OC abiertas; el importe de OC y pendiente es cero. El estado de remitos indica 8 sin factura, como foto actual. No hay recepciones válidas para plazo promedio, que se expone como `N/D`. Este tablero aplica sólo sucursal; el filtro de PV no interviene en sus SQL. Todavía se muestra únicamente a usuarios con acceso completo mientras se verifica la autorización de sucursales sin PV, que existen en V45. Faltan detalles y prueba web.

## Conciliación inicial de Análisis financiero

En Best Sox 01–12/10/2026, cobranzas $177.508.146,64 y pagos $153.688.170,16 producen un flujo neto de $23.819.976,48; los dos primeros importes coinciden con Resumen gerencial. Los saldos a corte se reconstruyen desde el último movimiento por entidad, como en V45: clientes $2.326.472.757,89 y proveedores $383.360.504,23. El aging de documentos abiertos entrega vencido a cobrar $1.198.315.625,60, vencido a pagar $146.503.148,58; +60 días $431.200.189,10 y $41.863.884,35 respectivamente. Bancos $1.289.836.286,82 coincide con la captura. Los saldos históricos y la cartera de documentos abiertos responden a universos distintos, por lo que no deben presentarse como una conciliación directa. Con PV/sucursal seleccionados, cajas, cheques y bancos devuelven no disponible para impedir exponer el saldo global. Faltan detalles, prueba web y contraste visual con el tablero financiero.
