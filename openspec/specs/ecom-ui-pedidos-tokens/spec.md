# Spec: Tokens UI pedidos mayorista (slate/sky)

**Capability:** `ecom-ui-pedidos-tokens`  
**Origen:** change `ecom-pedidos-usabilidad-supervisor` (archivado 13/07/2026)

## Purpose

Design system slate/sky y tokens `.pedidos-*` en flujos de pedido mayorista (simple, masivo, hub acotado). Eliminar acentos purple y artefactos visuales PHP legacy.

## Requirements

### REQ-UI-01 — Paleta slate/sky canónica

En pantallas de pedido mayorista (`/venta/`, `/pedido-masivo-sucursales/`, hub pedidos acotado), la UI MUST usar tokens `.pedidos-*` y paleta slate/sky definida en `docs/order-ui-redesign/05-design-system-pedidos.md` y canon `ui-fuente-verdad-reportes-mpr`.

#### Scenario: CTA primario en pedido simple

- **GIVEN** usuario en `/ecom/mayoristapp/venta/`
- **WHEN** observa botón confirmar pedido
- **THEN** MUST usar clase/token `.pedidos-btn-primary` (sky/slate)
- **AND** MUST NOT usar `purple-*` de Tailwind

#### Scenario: Header pedido masivo

- **GIVEN** usuario en pedido masivo sucursales
- **WHEN** carga la pantalla
- **THEN** header y CTAs MUST seguir patrón MPR slate
- **AND** focos y selección MUST NOT usar purple

---

### REQ-UI-02 — Prohibición de purple en flujos pedido

Las plantillas e includes de pedido (`compra_mayorista.html`, `pedidos_*`, `pedido_masivo_sucursales.html`) MUST NOT contener clases `purple-*`, `bg-purple`, `text-purple`, `ring-purple` ni equivalentes hardcodeados tras este change.

#### Scenario: Barrido post-implementación

- **GIVEN** el change aplicado en pedido simple y masivo
- **WHEN** se inspecciona HTML renderizado de confirmar, breadcrumb y toggle PED activo
- **THEN** MUST NOT aparecer tokens purple en clases CSS

---

### REQ-UI-03 — Sin artefactos visuales PHP legacy

La UI de pedidos MUST NOT reproducir estilos heredados del portal PHP (`mayoristapp` legacy): tablas con bordes grises PHP, botones degradados legacy ni tipografías fuera del stack Synap. MUST reutilizar includes canónicos (`pedidos_page_styles.html`, modales Synap).

#### Scenario: Modal de confirmación masivo

- **GIVEN** usuario confirma lote masivo
- **WHEN** se muestra confirmación
- **THEN** MUST usar `pedidos_modal.html` o equivalente canon Synap
- **AND** MUST NOT usar `confirm()` nativo del navegador

---

### REQ-UI-04 — Coherencia de tokens entre simple y masivo

Controles equivalentes (botón primario, input foco, badge informativo, link PDF) en pedido simple y masivo MUST compartir las mismas clases `.pedidos-*`.

#### Scenario: Badge lista de precios

- **GIVEN** badge solo lectura de lista de precios en header simple
- **WHEN** se muestra en pedido masivo el mismo dato
- **THEN** ambos MUST usar el mismo token `.pedidos-badge-lista` (o equivalente documentado)
