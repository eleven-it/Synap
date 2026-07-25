# Delta for ecom-aprobacion-pedidos

## MODIFIED Requirements

### REQ-APR-02 — Motor de reglas

El motor MUST evaluar: monto sobre umbral, descuento pie/renglón sobre umbral y `cliente_nuevo`. Cuando `ecom_credito_pedidos_activa` está ON, la regla `credito_no_autorizado` MUST NOT enrutar pedidos a cola comercial ni setear `estado_aprobacion_comercial` por motivo de crédito; la resolución de crédito MUST quedar exclusivamente en workflow Finanzas (`ecom-credito-pedidos`). Con flag crédito OFF, `credito_no_autorizado` MAY seguir comportamiento legacy de cola comercial si subflag comercial activo.

(Previously: motor incluía `credito_no_autorizado` mezclando crédito con aprobación comercial.)

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
