# Spec: Aprobación comercial de pedidos

**Capability:** `ecom-aprobacion-pedidos`  
**Origen:** changes `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026), `ecom-pedido-masivo-consolidado-hub` (22/07/2026)  
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

El motor MUST evaluar: monto sobre umbral, descuento pie/renglón sobre umbral y `cliente_nuevo`. Cuando `ecom_credito_pedidos_activa` está ON, la regla `credito_no_autorizado` MUST NOT enrutar pedidos a cola comercial ni setear `estado_aprobacion_comercial` por motivo de crédito; la resolución de crédito MUST quedar exclusivamente en workflow Finanzas (`ecom-credito-pedidos`). Con flag crédito OFF, `credito_no_autorizado` MAY seguir comportamiento legacy de cola comercial si subflag comercial activo.

#### Scenario: Descuento renglón sobre umbral

- **GIVEN** descuento renglón sobre umbral configurado
- **WHEN** el vendedor confirma pedido
- **THEN** MUST quedar en estado comercial `pendiente`

#### Scenario: Crédito No Autorizado con flag crédito ON

- **GIVEN** `ecom_credito_pedidos_activa` ON y PED con `autorizacion_sistema='No Autorizado'` por exceso de crédito
- **WHEN** se ejecuta motor comercial post-checkout
- **THEN** MUST NOT setear `estado_aprobacion_comercial='pendiente'` por regla `credito_no_autorizado`
- **AND** MUST NOT crear evento de aprobación comercial por crédito

#### Scenario: Crédito No Autorizado con flag crédito OFF

- **GIVEN** flag crédito OFF, subflag comercial ON y PED `No Autorizado` por mora
- **WHEN** se ejecuta motor comercial
- **THEN** MAY aplicar regla `credito_no_autorizado` hacia cola comercial según comportamiento legacy

---

### REQ-APR-03 — Routing y APIs

El sistema MUST enrutar aprobación Supervisor→Gerente cuando aplique. APIs `aprobar`/`rechazar` por `cod_mov` MUST exigir permiso `ecom.pedidos.aprobar` y validar alcance. PED **sueltos** (sin `lote_draft_id` o con lote ya resuelto comercialmente) MUST seguir autorizables individualmente por API existente. PED hijo de lote con `estado_aprobacion_lote=pendiente` MUST rechazar aprobación individual con error operativo en español indicando usar autorización de lote.

#### Scenario: Cola supervisor PED suelto

- **GIVEN** pedido pendiente comercial asignado a supervisor sin lote
- **WHEN** el supervisor aprueba por API `cod_mov`
- **THEN** MUST avanzar según jerarquía org (escalar a gerente si corresponde)

#### Scenario: Bloqueo aprobación individual en lote pendiente

- **GIVEN** PED hijo de lote con `estado_aprobacion_lote=pendiente`
- **WHEN** invoca API aprobar por `cod_mov`
- **THEN** MUST responder error en español
- **AND** MUST NOT modificar estado comercial del PED

#### Scenario: Aprobación individual tras lote resuelto

- **GIVEN** PED que no pertenece a lote pendiente
- **WHEN** supervisor aprueba por API individual
- **THEN** MUST aplicar flujo comercial estándar sin requerir `draft_id`

---

### REQ-APR-04 — Flags desactivados

Con master OFF o subflag OFF, el sistema MUST NOT aplicar reglas ni colas comerciales.

#### Scenario: Flags desactivados

- **GIVEN** master OFF o subflag OFF
- **WHEN** se confirma un pedido
- **THEN** MUST NOT setear estado comercial ni crear eventos de aprobación

---

### REQ-APR-05 — Autorización de lote completo

Con subflag `ecom_aprobacion_pedidos_activa` ON, el sistema MUST permitir **autorizar** o **rechazar** un lote masivo confirmado aplicando la acción a **todos** los `cod_mov` activos del draft en una operación lógica todo-o-nada. MUST validar permiso `ecom.pedidos.aprobar` y alcance comercial sobre el draft y cada PED. MUST actualizar `estado_aprobacion_comercial` de cada PED según la misma semántica que aprobación individual (incluido routing Supervisor→Gerente cuando aplique por PED).

#### Scenario: Aprobar lote completo

- **GIVEN** lote confirmado con 3 PED pendientes comerciales y supervisor con alcance
- **WHEN** autoriza el lote desde resumen o hub
- **THEN** los 3 PED MUST quedar resueltos comercialmente según reglas vigentes
- **AND** `estado_aprobacion_lote` del draft MUST reflejar estado agregado aprobado

#### Scenario: Rechazar lote completo

- **GIVEN** lote pendiente con motivo de rechazo ingresado en modal Synap
- **WHEN** confirma rechazo de lote
- **THEN** MUST aplicar rechazo comercial a todos los PED activos del lote
- **AND** MUST persistir motivo según contrato de rechazo individual

#### Scenario: Subflag OFF

- **GIVEN** `ecom_aprobacion_pedidos_activa` OFF
- **WHEN** se invoca autorización de lote
- **THEN** MUST responder error operativo en español
- **AND** MUST NOT modificar estados comerciales

---

### REQ-APR-06 — APIs de lote por draft_id

El sistema MUST exponer APIs REST (rutas documentadas en diseño) para `aprobar` y `rechazar` lote identificado por `draft_id` de `EcomPedidoMasivoDraft` confirmado. MUST aceptar payload de rechazo con motivo cuando corresponda. Respuestas MUST incluir resumen de PED afectados y estado agregado final. Errores MUST devolverse en español.

#### Scenario: API aprobar lote exitosa

- **GIVEN** draft confirmado pendiente y token CSRF válido
- **WHEN** POST a API aprobar lote por `draft_id`
- **THEN** MUST devolver 200 con lista de `cod_mov` procesados
- **AND** estado agregado MUST ser coherente con pantalla resumen

#### Scenario: Draft inexistente

- **GIVEN** `draft_id` inválido o no confirmado
- **WHEN** invoca API de lote
- **THEN** MUST responder 404 con mensaje en español

---

### REQ-APR-07 — Estado comercial agregado del draft

El sistema MUST persistir o derivar `estado_aprobacion_lote` en `EcomPedidoMasivoDraft` con valores al menos: `pendiente`, `aprobado`, `rechazado`, `parcial` (solo transitorio durante compensación). El hub y resumen MUST consumir este estado para CTAs y badges. Campo MUST ser nullable; código previo MUST ignorarlo si ausente.

#### Scenario: Estado pendiente tras confirmación

- **GIVEN** checkout masivo con reglas comerciales activas
- **WHEN** confirma lote con PED pendientes
- **THEN** `estado_aprobacion_lote` MUST quedar `pendiente`

#### Scenario: Transición a aprobado

- **GIVEN** lote pendiente
- **WHEN** autorización de lote completa exitosamente
- **THEN** `estado_aprobacion_lote` MUST quedar `aprobado`

---

### REQ-APR-08 — Compensación ante fallo parcial

Si durante autorización/rechazo de lote falla el procesamiento de uno o más PED tras haber aplicado cambios a otros, el sistema MUST ejecutar compensación (revertir o completar según política documentada en diseño, patrón `batch_checkout_masivo`) y MUST NOT dejar estados comerciales inconsistentes silenciosos. MUST registrar error operativo en español y MAY dejar `estado_aprobacion_lote=parcial` solo durante recuperación; estado estable final MUST ser `pendiente` (reintento) o coherente todo-o-nada.

#### Scenario: Fallo en PED 2 de 3

- **GIVEN** lote con 3 PED pendientes
- **WHEN** falla aprobación del segundo PED tras aprobar el primero
- **THEN** MUST revertir o compensar el primero según diseño
- **AND** MUST exponer mensaje de error en español indicando PED fallido
- **AND** MUST NOT mostrar lote como aprobado en UI

#### Scenario: Reintento tras compensación

- **GIVEN** compensación completada y lote vuelve a `pendiente`
- **WHEN** supervisor reintenta autorizar lote
- **THEN** MUST procesar nuevamente todos los PED activos desde estado coherente
