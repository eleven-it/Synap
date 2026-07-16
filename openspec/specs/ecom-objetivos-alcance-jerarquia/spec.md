# Spec: Objetivos de venta con alcance por jerarquía

**Capability:** `ecom-objetivos-alcance-jerarquia`  
**Origen:** change `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)

## Purpose

Unificar alcance org en CRUD de objetivos e informe ventas-objetivos-vs-bo cuando workflow comercial está activo.

## Requirements

### REQ-OBJ-01 — CRUD objetivos scoped

Con master ON, CRUD de objetivos MUST limitarse a vendedores en alcance org del usuario. Con master OFF MUST mantener comportamiento actual (solo vendedor propio).

#### Scenario: Gerente con workflow ON

- **GIVEN** master ON y usuario gerente con subárbol org
- **WHEN** realiza CRUD de objetivos
- **THEN** MUST operar solo sobre vendedores del subárbol

---

### REQ-OBJ-02 — Informe scoped

`ventas_objetivos_bo_runner` MUST filtrar vendedores por `alcance_viajantes_comercial` si master ON. Con master OFF MUST preservar scope actual.

#### Scenario: Informe con workflow OFF

- **GIVEN** master OFF
- **WHEN** se ejecuta informe ventas-objetivos-vs-bo
- **THEN** MUST usar el mismo scope de vendedor propio que antes del change
