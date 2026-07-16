# Spec: Jerarquía comercial Gerente→Supervisor→Vendedor

**Capability:** `ecom-jerarquia-comercial`  
**Origen:** change `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)  
**Master flag:** `ecom_workflow_jerarquia_comercial` (default No)

## Purpose

Reemplazar carteras ad-hoc JSON (`ecom_vendedores_a_cargo_*`) por organigrama formal con árbol 1-padre y servicio unificado de alcance comercial.

## Requirements

### REQ-JER-01 — DDL organigrama

El sistema MUST crear `ecom_org_gerente_supervisor` y `ecom_org_supervisor_vendedor` vía `catalog.py` (provider `ecom_jerarquia_aprobacion`); un padre por nodo (G→S→V).

#### Scenario: DDL aplicado

- **GIVEN** provider ejecutado en base empresa
- **WHEN** se consultan las tablas org
- **THEN** MUST existir relaciones indexadas con unique por nodo activo

---

### REQ-JER-02 — ABM organigrama

Con master ON, Ajustes MUST permitir ABM del organigrama. MUST exigir permiso `ecom.jerarquia.editar`.

#### Scenario: Sin permiso de edición

- **GIVEN** usuario sin `ecom.jerarquia.editar`
- **WHEN** intenta editar org vía API o UI
- **THEN** MUST denegar (403)

---

### REQ-JER-03 — Migración JSON

El sistema MUST ofrecer comando backfill idempotente desde `ecom_vendedores_a_cargo_*` JSON a tablas org. MUST NOT borrar claves JSON legacy.

#### Scenario: Backfill desde JSON legacy

- **GIVEN** claves JSON con listas de vendedores por supervisor
- **WHEN** se ejecuta `migrar_carteras_a_jerarquia`
- **THEN** MUST crear equivalencia relacional en tablas org

---

### REQ-JER-04 — Helper de alcance

`alcance_viajantes_comercial(base, ctx)` MUST: con workflow OFF delegar a JSON/`[cv]` actual; con workflow ON retornar subárbol según rol + `ecom.pedidos.ver_todos`.

#### Scenario: Workflow OFF vendedor 42

- **GIVEN** master OFF y vendedor `42`
- **WHEN** se consulta alcance
- **THEN** MUST retornar `[42]`
