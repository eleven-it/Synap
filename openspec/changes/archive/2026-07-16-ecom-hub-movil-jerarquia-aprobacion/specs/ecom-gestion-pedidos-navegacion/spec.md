# Spec: Navegación y rutas canónicas de pedidos ecom

**Capability:** `ecom-gestion-pedidos-navegacion`  
**Origen:** changes `ecom-venta-pedido-unificada` (13/07/2026), `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)  
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

El hub de pedidos y el ítem de menú «Nuevo pedido» MUST usar la ruta canónica `ecom:mayoristapp_venta`. Las cards de PED del hub (incl. vista mobile `<lg`) MUST abrir `/mayoristapp/venta/?cod_mov=` (no el detalle HTML).

#### Scenario: Card PED del hub (desktop)

- **GIVEN** un PED en el pipeline del hub
- **WHEN** el usuario abre la card
- **THEN** la URL MUST contener `/mayoristapp/venta/` y `cod_mov=`

#### Scenario: Card PED del hub (mobile)

- **GIVEN** un PED visible en cards mobile del hub
- **WHEN** el usuario hace tap en la card
- **THEN** MUST navegar a `/mayoristapp/venta/?cod_mov=`

---

### REQ-NAV-04 — PWA mobile Nivel A

El menú PWA MUST incluir entradas hub y venta accesibles en Nivel A. Deep links de pedidos/venta MUST resolver correctamente en móvil.

#### Scenario: Menú PWA Nivel A

- **GIVEN** usuario en PWA con restricción Nivel A
- **WHEN** abre el menú mayoristapp
- **THEN** MUST ver entradas hub y venta accesibles
