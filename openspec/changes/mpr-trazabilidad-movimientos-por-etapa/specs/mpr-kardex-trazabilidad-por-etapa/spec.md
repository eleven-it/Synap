# Especificación: mpr-kardex-trazabilidad-por-etapa

## Propósito

Extender el análisis de trazabilidad por artículo (`kardex_articulo`) para componentes con eje `pipeline_fabricados`, de modo que el historial de movimientos reconstruya saldos por etapa del pipeline MPR (Producción, Semi elaborado, 2.ª selección) y consolidado, con paridad de cierre frente al inventario Fabricados, sin alterar otros ejes ni la semántica de `inventario_tabla`.

**Alcance:** hub MPR `grupo=trazabilidad`, reporte `kardex_articulo`. **Fuera de alcance:** timeline OPT, inventario físico, cambio de reglas MSTOCK, oleada 1 para packs `tipo_eje: terminado`.

## Requisitos

### Requirement: Explosión de movimientos por depósito (pipeline fabricados)

Para artículos componente con `tipo_eje: pipeline_fabricados`, el sistema MUST emitir **una fila de impacto por par** `(codigo_movimiento, CodDeposito)` del pipeline, con entrada y salida atribuidas **solo** a ese depósito. MUST NOT agregar en SQL entradas y salidas de distintos depósitos del mismo movimiento en una única fila neteada.

#### Scenario: Movimiento en un solo depósito del pipeline

- DADO un componente con eje `pipeline_fabricados` y un movimiento que afecta únicamente el depósito Semi elaborado
- CUANDO el usuario consulta el análisis de trazabilidad en el rango que incluye ese movimiento
- ENTONCES la grilla incluye **exactamente una** fila de impacto para ese movimiento con la etapa Semi elaborado y las cantidades de entrada/salida de ese depósito

#### Scenario: Artículo sin eje pipeline fabricados

- DADO un pack con `tipo_eje: terminado` o un componente con `tipo_eje: semi` (un solo depósito pipeline)
- CUANDO el usuario consulta el mismo reporte `kardex_articulo`
- ENTONCES el sistema MUST conservar el modelo de filas y corrido **actual** (sin explosión multi-etapa de oleada 1)

### Requirement: Transferencias internas del pipeline como dos renglones

Cuando un comprobante (p. ej. OPP) impacta **dos** depósitos distintos del pipeline en el mismo `codigo_movimiento`, el sistema MUST presentar **dos renglones**: salida en depósito origen e entrada en depósito destino, compartiendo identificadores de movimiento/comprobante pero con etapa distinta por fila.

#### Scenario: OPP Producción → Semi elaborado

- DADO un OPP que transfiere stock de Producción a Semi elaborado dentro del pipeline
- CUANDO el análisis lista movimientos del período
- ENTONCES aparecen **dos** filas con el mismo comprobante/movimiento
- Y la fila de Producción refleja **salida** en Producción
- Y la fila de Semi elaborado refleja **entrada** en Semi elaborado
- Y el consolidado tras ambos impactos MUST coincidir con la regla de suma de etapas (transferencia pura: consolidado invariante si no hay pérdida/ganancia fuera del pipeline)

### Requirement: Corrido multi-etapa calculado en backend

Para `tipo_eje: pipeline_fabricados`, el backend MUST calcular tras cada fila de impacto (y en saldo inicial) un objeto `saldos_por_etapa` keyed por `tipo_mpr` del catálogo `TIPOS_MPR_PIPELINE_FABRICADOS`, en el **mismo orden** que las columnas del ámbito Fabricados de inventario. MUST NOT delegar el cálculo del corrido multi-etapa al cliente.

#### Scenario: Saldos post-movimiento por etapa

- DADO un historial con al menos dos impactos en etapas distintas
- CUANDO el servicio devuelve el payload del análisis
- ENTONCES cada fila relevante incluye `saldos_por_etapa` con valores numéricos para Producción, Semi elaborado y 2.ª selección **después** de aplicar ese impacto
- Y el saldo inicial del período incluye el mismo desglose por etapa

#### Scenario: Consolidado derivado de etapas

- DADO cualquier punto del corrido (inicial o post-fila)
- CUANDO se expone el consolidado del pipeline
- ENTONCES MUST ser la **suma aritmética** de las tres etapas del ámbito fabricados (misma regla que inventario Fabricados)

### Requirement: Saldo corrido consolidado visible en UI

La interfaz del reporte MUST seguir mostrando un **saldo corrido consolidado** legible fila a fila (columna Saldo o equivalente canónico MPR), además de la dimensión etapa y los saldos por etapa provistos por backend.

#### Scenario: Usuario sigue el total pipeline en la grilla

- DADO un componente `pipeline_fabricados` con movimientos en el rango
- CUANDO el usuario recorre la tabla de movimientos
- ENTONCES puede leer el saldo consolidado corrido en cada fila coherente con `saldos_por_etapa.consolidado` (o campo equivalente documentado en diseño)

### Requirement: Columna Etapa y KPIs de cabecera (MVP oleada 1)

La UI del partial `kardex_articulo` MUST incluir una columna **Etapa** (etiqueta humana alineada a inventario: Producción, Semi elaborado, 2.ª selección) en cada fila de impacto del pipeline. La cabecera MUST mostrar KPIs con desglose Producción / Semi elaborado / 2.ª selección / Consolidado para el cierre del rango (o stock de referencia cuando aplique), siguiendo el canon de reportes MPR.

#### Scenario: Identificación de etapa por fila

- DADO un análisis pipeline con varias filas
- CUANDO el usuario visualiza la grilla sin exportar
- ENTONCES cada fila de impacto muestra la etapa correspondiente al depósito de esa fila

#### Scenario: KPIs de cabecera con desglose

- DADO un rango cuyo cierre incluye saldos por etapa calculados
- CUANDO se renderiza la cabecera del reporte
- ENTONCES el usuario ve valores separados para las tres etapas y el consolidado, además del indicador consolidado pipeline ya existente donde corresponda

### Requirement: Export CSV con dimensión etapa y saldos auditables

El export CSV del reporte `kardex_articulo` MUST incluir columnas para depósito o etapa (`tipo_mpr` / etiqueta) y columnas numéricas suficientes para auditar saldos por etapa y consolidado alineadas a la grilla oleada 1. Las presentaciones Pares/Docenas MUST aplicarse a los nuevos campos numéricos de forma consistente con el resto del reporte.

#### Scenario: Columnas CSV pipeline

- DADO un artículo `pipeline_fabricados` y export CSV desde el hub
- CUANDO se genera el archivo
- ENTONCES contiene columnas de etapa/depósito y saldos por etapa (y consolidado) definidas en el contrato del change
- Y un consumidor puede reconstruir la auditoría por etapa sin la UI

### Requirement: Conciliación estricta por etapa solo si Hasta ≥ hoy

Si la fecha **Hasta** del filtro es **mayor o igual** a la fecha calendario de hoy (zona/configuración del producto), el sistema MUST comparar el cierre del corrido **por cada** `tipo_mpr` del pipeline y el consolidado contra el **stock actual por etapa** obtenido con la **misma regla** que el ámbito Fabricados de inventario (`stock_deposito` + depósitos `tipo_mpr` del pipeline con `anulado='No'` y `suma_stock='Si'`), para el mismo `id_articulo` y presentación. MUST NOT invocar `consultar_inventario_tabla` en el camino de request de runtime (filtra `tipo_art_fab` y puede devolver 0 filas para componentes válidos). En tests de paridad, `consultar_inventario_tabla(ambito=fabricados)` MAY usarse solo como **oráculo independiente**. Si hay desvío fuera de tolerancia documentada (p. ej. redondeo Pares/Docenas), MUST emitir advertencia de conciliación **por etapa** (una advertencia que reemplace o extienda la consolidada, según diseño). Si **Hasta** es anterior a hoy, MUST NOT exigir paridad estricta instantánea con inventario (no hay snapshot histórico de etapas); el payload MAY exponer `conciliacion_estricta=false`.

#### Scenario: Cierre cuadra con inventario (Hasta hoy)

- DADO stock actual Fabricados con Producción 79, Semi 28, 2.ª 0, Consolidado 107 para el artículo (misma regla de depósitos que inventario)
- Y un rango con `Hasta >= hoy` que reproduce ese cierre en trazabilidad
- CUANDO finaliza el análisis
- ENTONCES no se emite advertencia de conciliación por etapa
- Y los saldos de cierre por etapa coinciden con ese stock de referencia dentro de la tolerancia de presentación

#### Scenario: Rango histórico sin conciliación estricta

- DADO `Hasta` estrictamente anterior a la fecha de hoy
- CUANDO el usuario ejecuta el análisis pipeline
- ENTONCES el sistema MUST NOT fallar ni advertir por desvío vs inventario instantáneo por etapa

### Requirement: Eje pipeline con filtros de paridad inventario

Para el corrido y la conciliación de `pipeline_fabricados`, el sistema MUST considerar solo depósitos del pipeline con `anulado='No'` y `suma_stock='Si'` (paridad con inventario Fabricados). MUST proveer un helper de etapas (id, `tipo_mpr`, etiqueta, orden) con esos filtros sin romper consumidores existentes de `get_depositos_pipeline_fabricados_mpr` salvo los tests/contrato de componente que el diseño indique actualizar.

#### Scenario: Depósito pipeline sin suma_stock excluido

- DADO un depósito con `tipo_mpr` de pipeline pero `suma_stock='No'`
- CUANDO se construye el kardex `pipeline_fabricados`
- ENTONCES ese depósito MUST NOT contribuir al corrido ni a la conciliación por etapa
- Y el sistema MAY advertir la exclusión si el diseño lo define

### Requirement: Deduplicación por movimiento y depósito

Tras la explosión por depósito, la deduplicación de filas del kardex MUST indexar por `(codigo_movimiento, CodDeposito)` (con `CodDeposito` nulo equivalente al comportamiento legacy en ejes no-pipeline). MUST NOT colapsar los dos renglones de una transferencia OPP entre depósitos distintos del pipeline.

#### Scenario: OPP sobrevive al dedupe

- DADO un OPP Producción → Semi con dos impactos ya explotados
- CUANDO corre la deduplicación del collector
- ENTONCES ambas filas permanecen en el resultado ordenado (salida origen antes que entrada destino según diseño)

### Requirement: No regresión packs Terminado y otros ejes

El camino de análisis para `tipo_eje: terminado` (pack) y para cualquier `tipo_eje` distinto de `pipeline_fabricados` MUST permanecer funcionalmente equivalente al comportamiento previo a este change: misma forma de filas, saldo corrido escalar, columnas CSV legacy y golden tests existentes (p. ej. pack Terminado) MUST seguir pasando sin relajación de aserciones. La explosión por depósito MUST quedar detrás de un flag / rama que no altere el SQL ni el dedupe de esos ejes.

#### Scenario: Golden pack Terminado

- DADO el fixture/golden de kardex pack Terminado existente en la suite
- CUANDO se ejecutan los tests de regresión tras el change
- ENTONCES UI, saldos y CSV del pack MUST coincidir con el golden previo

### Requirement: Semántica de inventario_tabla intacta (MUST NOT)

Este change MUST NOT modificar columnas, fórmulas, filtros ni significado de `consultar_inventario_tabla` ni de las columnas del ámbito Fabricados. Solo se permite **lectura** como oráculo de tests de paridad; la conciliación de runtime usa consulta propia en MPR con la misma regla de agregación.

#### Scenario: Contrato inventario sin cambios

- DADO cualquier despliegue que incluya solo este change
- CUANDO se invoca inventario Fabricados con los mismos parámetros que antes
- ENTONCES los valores y nombres de columnas MUST ser idénticos en semántica al baseline pre-change

### Requirement: Movimientos que no afectan depósito (FA)

Los movimientos marcados como no afectantes de depósito en el corrido actual (p. ej. FA con `afecta_deposito=False`) MUST NOT alterar `saldos_por_etapa` ni el saldo corrido consolidado. MAY listarse en la grilla; la columna Etapa MUST reflejar que no hubo impacto de stock por etapa según reglas definidas en diseño.

#### Scenario: FA no mueve saldos por etapa

- DADO un movimiento FA excluido del corrido de depósito en el comportamiento actual
- CUANDO se procesa en modo `pipeline_fabricados`
- ENTONCES `saldos_por_etapa` y saldo consolidado corrido permanecen iguales a la fila anterior
