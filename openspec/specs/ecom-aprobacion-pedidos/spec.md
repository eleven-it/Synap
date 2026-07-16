# Spec: Aprobación comercial de pedidos

**Capability:** `ecom-aprobacion-pedidos`  
**Origen:** change `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)  
**Subflag:** `ecom_aprobacion_pedidos_activa` (requiere master ON)

## Purpose

Workflow comercial opcional con reglas de aprobación, estados separados de autorización de crédito legacy y routing Supervisor→Gerente.

## Requirements

### REQ-APR-01 — Subflag y estados

Subflag `ecom_aprobacion_pedidos_activa` (solo si master ON) MUST activar workflow comercial. Estado comercial MUST almacenarse en `estado_aprobacion_comercial` separado de `autorizacion_sistema`.

#### Scenario: Regla dispara en checkout

- **GIVEN** subflag ON y pedido que cumple regla de aprobación
- **WHEN** se confirma checkout
- **THEN** MUST setear estado comercial `pendiente` sin modificar `autorizacion_sistema`

---

### REQ-APR-02 — Motor de reglas

El motor MUST evaluar: monto sobre umbral, descuento pie/renglón sobre umbral, `crédito_no_autorizado`, `cliente_nuevo`.

#### Scenario: Descuento renglón sobre umbral

- **GIVEN** descuento renglón sobre umbral configurado
- **WHEN** el vendedor confirma pedido
- **THEN** MUST quedar en estado comercial pendiente

---

### REQ-APR-03 — Routing y APIs

El sistema MUST enrutar aprobación Supervisor→Gerente cuando aplique. APIs `aprobar`/`rechazar` MUST exigir permiso `ecom.pedidos.aprobar` y validar alcance.

#### Scenario: Cola supervisor

- **GIVEN** pedido pendiente comercial asignado a supervisor
- **WHEN** el supervisor aprueba
- **THEN** MUST avanzar según jerarquía org (escalar a gerente si corresponde)

---

### REQ-APR-04 — Flags desactivados

Con master OFF o subflag OFF, el sistema MUST NOT aplicar reglas ni colas comerciales.

#### Scenario: Flags desactivados

- **GIVEN** master OFF o subflag OFF
- **WHEN** se confirma un pedido
- **THEN** MUST NOT setear estado comercial ni crear eventos de aprobación
