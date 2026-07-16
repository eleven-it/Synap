# Spec: Ajustes workflow comercial ecom

**Capability:** `ecom-ajustes-workflow-comercial`  
**Origen:** change `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)

## Purpose

Persistencia de flags master/sub, umbrales de aprobación y atajos de navegación desde Ajustes ventas.

## Requirements

### REQ-GLOB-01 — Paridad con flag OFF

Cuando `ecom_workflow_jerarquia_comercial`=No, el sistema MUST preservar comportamiento actual (JSON carteras, alcance propio, sin aprobación comercial, hub sin cambios funcionales de org).

#### Scenario: Master OFF

- **GIVEN** master flag No
- **WHEN** cualquier flujo ecom (hub, checkout, objetivos)
- **THEN** MUST NOT usar tablas org ni estados comerciales

---

### REQ-AJU-01 — Flags y atajos

Ajustes MUST persistir master `ecom_workflow_jerarquia_comercial` y subflag `ecom_aprobacion_pedidos_activa` en `configuracion_ecom`. Subflag MUST ignorarse si master No. MUST ofrecer atajos a hub, objetivos y backorder.

#### Scenario: Subflag ignorado sin master

- **GIVEN** master No y subflag Sí en base de datos
- **WHEN** se evalúa workflow comercial
- **THEN** efecto del subflag MUST NOT aplicarse
