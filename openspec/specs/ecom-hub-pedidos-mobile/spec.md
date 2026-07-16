# Spec: Hub pedidos mobile-first

**Capability:** `ecom-hub-pedidos-mobile`  
**Origen:** change `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)  
**Ruta:** `/ecom/mayoristapp/pedidos/`

## Purpose

Experiencia mobile-first del hub mayorista con layout responsive, cola de aprobación comercial y acceso Nivel A.

## Requirements

### REQ-MOB-01 — Layout responsive

Hub `/ecom/mayoristapp/pedidos/` MUST ser mobile-first: viewports `<lg` chips+cards; `≥lg` kanban. MUST seguir canon visual reportes/MPR.

#### Scenario: Móvil Nivel A

- **GIVEN** viewport móvil en Nivel A
- **WHEN** el usuario abre el hub
- **THEN** MUST ver cards sin scroll horizontal

---

### REQ-MOB-02 — Cola de aprobación

Con aprobación ON, el hub MUST exponer filtro/columna de pendientes comerciales con CTA aprobar/rechazar scoped al alcance del aprobador.

#### Scenario: Pendiente visible para supervisor

- **GIVEN** pedido con estado comercial pendiente en alcance del supervisor
- **WHEN** el supervisor abre el hub
- **THEN** MUST ver el pedido en cola con acciones aprobar/rechazar

---

### REQ-MOB-03 — Middleware Nivel A

Hub, venta y APIs de aprobación/jerarquía MUST estar en allowlist de `mobile_level_a_middleware`.

#### Scenario: GET hub en Nivel A

- **GIVEN** sesión con restricción Nivel A
- **WHEN** GET `/ecom/mayoristapp/pedidos/`
- **THEN** MUST NOT retornar 403 por middleware
