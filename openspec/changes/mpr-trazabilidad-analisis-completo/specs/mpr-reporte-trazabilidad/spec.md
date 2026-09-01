# Delta — Trazabilidad línea de tiempo componente

**Capability:** `mpr-reporte-trazabilidad`  
**Change:** `mpr-trazabilidad-analisis-completo`

---

## ADDED Requirements

### REQ-TRAZ-06 — Fuente única con análisis kardex

El slug hub `timeline` (Línea de tiempo) MUST NOT mantener un servicio de recolección de datos independiente de `construir_analisis_trazabilidad_articulo`. MUST obtener eventos MPR/timeline desde el payload unificado o redirigir/deep-link a `kardex_articulo` con ancla `#timeline` preservando `id_articulo`, `desde` y `hasta`.

#### Scenario: Misma data que kardex

- GIVEN artículo con envío MPR y OPA MSTOCK en período
- WHEN el usuario abre Línea de tiempo y el análisis kardex del mismo artículo
- THEN los eventos MPR+OPP/OPA visibles son consistentes (misma fuente, sin duplicar consultas)

#### Scenario: Deep-link preserva filtros

- GIVEN URL `?grupo=trazabilidad&reporte=timeline&id_articulo=1398&desde=…&hasta=…`
- WHEN el usuario entra al informe
- THEN llega a la sección `#timeline` del análisis kardex con los mismos parámetros

---

## MODIFIED Requirements

### REQ-TRAZ-01 — Selección componente

El informe MUST requerir `id_articulo` vía autocomplete o query param. El período MUST heredar filtro global con estrechamiento opcional. Al resolver slug `timeline`, el sistema MUST navegar o renderizar dentro de `kardex_articulo` (ancla `#timeline`) en lugar de mantener pantalla autónoma con segunda fuente de datos.

(Previously: Línea de tiempo era reporte standalone con selección propia y servicio `reporte_mpr_trazabilidad_componente`.)

#### Scenario: Sin artículo

- GIVEN reporte trazabilidad sin `id_articulo`
- WHEN el usuario entra al informe
- THEN muestra prompt «Seleccione un componente» sin timeline vacío confuso

#### Scenario: Timeline dentro de análisis kardex

- GIVEN `id_articulo` válido
- WHEN el usuario abre Línea de tiempo desde hub
- THEN ve cabecera y bloques del análisis kardex y la timeline en sección `#timeline`

### REQ-TRAZ-02 — Eventos ordenados

El sistema MUST devolver eventos ordenados cronológicamente a partir del collector unificado del análisis (subset filtrado a eventos MPR + OPP/OPA ya normalizados), MUST NOT reconsultar tablas MPR/MSTOCK por separado solo para timeline.

| Tipo | Origen | Campos mínimos |
|------|--------|----------------|
| envio | `mpr_envio_produccion` | fecha, cantidad, usuario |
| parte | `mpr_parte` + líneas | fecha, cantidad, operario |
| clasificacion | `mpr_transicion_lote` | fecha, semi, segunda, scrap |
| armado | `mpr_armado_lote` (si existe) | fecha, cantidad |
| opp/opa | MSTOCK normalizado | fecha, cantidad, tipo |

(Previously: servicio timeline consultaba MPR y MSTOCK en paralelo al kardex sin unificación.)

#### Scenario: Cadena completa

- GIVEN componente con envío, parte y clasificación en período
- WHEN el usuario abre trazabilidad
- THEN timeline muestra 3+ nodos en orden cronológico con cantidades

### REQ-TRAZ-03 — Timeline visual

La UI MUST renderizar timeline vertical con línea conectora, nodos rellenos para eventos e íconos/etiquetas en español. MUST ubicarse en sección `#timeline` del partial de análisis kardex cuando se accede vía slug `timeline` o deep-link.

(Previously: timeline solo en `trazabilidad_timeline.html` aislado del análisis completo.)

#### Scenario: Ancla scroll

- GIVEN URL con `#timeline`
- WHEN carga el análisis kardex
- THEN el viewport MUST posicionar la sección timeline visible (scroll o foco equivalente)

### REQ-TRAZ-04 — Gaps informativos

Cuando exista envío sin parte subsiguiente en el período, la UI MAY mostrar nodo hueco «Sin parte registrada» tras último envío (informativo, no bloqueante). Comportamiento MUST preservarse tras delegación al servicio unificado.

(Previously: sin cambio funcional; solo cambia origen de datos.)

#### Scenario: Envío sin parte

- GIVEN envío MPR en período sin parte posterior
- WHEN se renderiza timeline
- THEN aparece nodo informativo «Sin parte registrada»

### REQ-TRAZ-05 — Enlaces operativos

Las filas de evento SHOULD enlazar a pantallas operativas cuando existan IDs (detalle parte, tablero). MUST NOT romperse al usar payload unificado.

(Previously: sin cambio funcional; solo cambia origen de datos.)

#### Scenario: Enlace a parte

- GIVEN evento parte con ID de parte disponible
- WHEN el usuario activa el enlace de la fila
- THEN navega al detalle operativo de parte existente
