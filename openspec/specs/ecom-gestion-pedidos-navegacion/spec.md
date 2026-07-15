# Spec: Navegación y rutas canónicas de pedidos ecom

**Capability:** `ecom-gestion-pedidos-navegacion`  
**Origen:** change `ecom-venta-pedido-unificada` (REQ-NAV-01–03, archivado 13/07/2026)  
**Ruta canónica:** `/ecom/mayoristapp/venta/`

## Requirements

### REQ-NAV-01 — Alias `/compra/` deprecado

`GET /ecom/mayoristapp/compra/` MUST redirigir a `/ecom/mayoristapp/venta/` preservando query string.

#### Scenario: Bookmark compra

- **GIVEN** URL `/ecom/mayoristapp/compra/`
- **WHEN** se navega
- **THEN** la respuesta MUST ser redirect a `/ecom/mayoristapp/venta/`

---

### REQ-NAV-02 — Detalle PED deprecado

`GET /ecom/mayoristapp/pedidos/<cod_mov>/` MUST redirigir a `/ecom/mayoristapp/venta/?cod_mov=<cod_mov>`.

#### Scenario: Legacy detalle

- **GIVEN** `/ecom/mayoristapp/pedidos/7/`
- **WHEN** se navega
- **THEN** MUST redirigir a `/ecom/mayoristapp/venta/?cod_mov=7`

---

### REQ-NAV-03 — Hub y menú apuntan a venta

El hub de pedidos y el ítem de menú «Nuevo pedido» MUST usar la ruta canónica `ecom:mayoristapp_venta`. Las cards de PED del hub MUST abrir `/venta/?cod_mov=` (no el detalle HTML).

#### Scenario: Card PED del hub

- **GIVEN** un PED en el pipeline del hub
- **WHEN** el usuario abre la card
- **THEN** la URL MUST contener `/mayoristapp/venta/` y `cod_mov=`
