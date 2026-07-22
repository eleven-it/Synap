# Delta for ecom-pedidos-hub-kanban

**Change:** `ecom-pedido-masivo-consolidado-hub`  
**Base:** `openspec/specs/ecom-pedidos-hub-kanban/spec.md`

## ADDED Requirements

### REQ-HUB-07 — Segmento Cargas masivas

El payload del hub MUST incluir segmento `cargas_masivas` separado de `columnas[]` Kanban. En desktop MUST renderizar lane **Cargas masivas** fuera de columnas de estado operativo. En viewports `<lg` MUST exponer chip/filtro equivalente accesible sin scroll horizontal obligatorio (REQ-HUB-06).

#### Scenario: Lote confirmado en lane

- **GIVEN** un `EcomPedidoMasivoDraft` confirmado con N PED generados
- **WHEN** el usuario abre el hub
- **THEN** MUST aparecer tarjeta padre en segmento Cargas masivas
- **AND** MUST NOT aparecer en columna Borrador

#### Scenario: Lane vacío

- **GIVEN** usuario sin lotes confirmados en alcance
- **WHEN** abre el hub
- **THEN** segmento Cargas masivas MUST ocultarse o mostrar estado vacío en español

---

### REQ-HUB-08 — Tarjeta tipo lote_masivo

Cada draft confirmado MUST publicarse como tarjeta `tipo=lote_masivo` con rollup: cliente, vendedor, fecha confirmación (`dd/MM/yyyy`), contador `k/n` PED activos, totales agregados y estado comercial del lote. MUST incluir CTA **Ver resumen** hacia `/ecom/mayoristapp/pedidos/lote/<draft_id>/`.

#### Scenario: Rollup en tarjeta padre

- **GIVEN** lote con 4 PED de los cuales 3 activos
- **WHEN** renderiza tarjeta `lote_masivo`
- **THEN** MUST mostrar chip/contador `3/4` (o equivalente documentado)
- **AND** CTA «Ver resumen» MUST enlazar al `draft_id` correcto

---

### REQ-HUB-09 — Mapa reverso y meta en PED hijos

El pipeline MUST construir mapa reverso `cod_mov → draft_id` para PED pertenecientes a lotes confirmados. Cada tarjeta/fila PED hijo MUST incluir meta `lote_draft_id` y chip visible `Lote · {Cliente} (k/n)`. PED hijos MUST permanecer en columnas operativas Kanban/Lista según su estado individual.

#### Scenario: Chip en tarjeta PED hijo

- **GIVEN** PED generado por lote confirmado del cliente «Mayorista SA»
- **WHEN** aparece en columna Por autorizar
- **THEN** MUST mostrar chip `Lote · Mayorista SA (k/n)`
- **AND** meta MUST incluir `lote_draft_id`

#### Scenario: Mapa reverso consistente

- **GIVEN** draft confirmado con `codigos_movimiento=[101,102]`
- **WHEN** el hub enriquece PED 101 y 102
- **THEN** ambos MUST resolver al mismo `lote_draft_id`

---

### REQ-HUB-10 — Filtro Lista «Ocultar PED de lotes»

En vista **Lista**, el hub SHOULD ofrecer filtro opcional **Ocultar PED de lotes** (persistido en sesión o query según diseño). Cuando activo, MUST ocultar filas PED con `lote_draft_id` definido; tarjetas `lote_masivo` en Cargas masivas MUST permanecer visibles.

#### Scenario: Filtro activo

- **GIVEN** lote confirmado con 3 PED visibles en Lista
- **WHEN** activa «Ocultar PED de lotes»
- **THEN** MUST ocultar las 3 filas PED hijas
- **AND** MUST mantener visible la tarjeta padre en Cargas masivas

#### Scenario: Filtro inactivo

- **GIVEN** mismo lote y filtro desactivado
- **WHEN** abre Lista
- **THEN** MUST mostrar PED hijos en sus columnas de estado habituales

---

## MODIFIED Requirements

### REQ-HUB-04 — Acciones

Desde una tarjeta/fila de PED confirmado, el usuario MUST poder abrir el detalle. El sistema SHOULD ofrecer Autorizar solo con permiso. Fechas en UI MUST ser `dd/MM/yyyy`. Para PED hijo de lote con autorización comercial pendiente a nivel lote, el hub MUST ocultar CTAs **Autorizar** y **Rechazar** individual (`meta.puede_aprobar=false`). CTAs de lote MUST ofrecerse en tarjeta `lote_masivo` y pantalla resumen, no duplicadas en hijos.

(Previously: Autorizar disponible por PED sin distinción de pertenencia a lote.)

#### Scenario: PED suelto autorizable

- **GIVEN** PED confirmado sin `lote_draft_id` y pendiente comercial
- **WHEN** usuario con permiso ve la tarjeta
- **THEN** MUST mostrar CTA Autorizar individual

#### Scenario: PED hijo de lote pendiente

- **GIVEN** PED con `lote_draft_id` y lote en estado comercial pendiente
- **WHEN** supervisor ve tarjeta en hub
- **THEN** MUST NOT mostrar CTAs Autorizar/Rechazar individual
- **AND** MUST mostrar chip de lote con enlace al resumen

#### Scenario: PED hijo tras resolución de lote

- **GIVEN** lote ya aprobado o rechazado comercialmente
- **WHEN** se renderiza PED hijo
- **THEN** MUST reflejar estado comercial resultante del lote
- **AND** MUST NOT reactivar CTA aprobar individual salvo reglas de escalamiento vigentes (REQ-APR-03)
