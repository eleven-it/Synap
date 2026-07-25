# Delta for ecom-checkout-mayorista

## MODIFIED Requirements

### REQ-CHK-004: Validación de crédito y autorización

El sistema MUST calcular la **autorización** del comprobante mediante el evaluador unificado de `ecom-credito-pedidos` cuando `ecom_credito_pedidos_activa` está ON: MUST considerar política por cliente/canal, exposición Balance+All (capas ON/OFF), monto y mora en días; MUST persistir snapshot de evaluación (motivos, capas, totales) junto al alta. Si `cliente.Credito=0`, MUST NOT rechazar por tope monetario. Con flag OFF MUST mantener evaluación legacy solo-días. Un pedido originado por **cliente** (autogestión) MUST quedar siempre `'No Autorizado'`. El exceso de crédito MUST NOT bloquear el alta; MUST registrarse el estado correspondiente y, en fase B, activar hold de preparación cuando aplique.

(Previously: solo mora en días vía `cuentacliente` y `credito_limite_dias`, sin exposición $ ni snapshot.)

#### Scenario: Cliente al día autorizado

- **GIVEN** un cliente sin comprobantes vencidos más allá de su límite de días y exposición dentro de cupo
- **WHEN** el vendedor confirma el pedido
- **THEN** `comp_ped.autorizacion_sistema` MUST ser `'Autorizado'`
- **AND** MUST persistir snapshot de evaluación cuando flag crédito ON

#### Scenario: Cliente con atraso excede límite

- **GIVEN** un cliente con `credito_limite_dias=30` y comprobante impago de hace 45 días
- **WHEN** el vendedor confirma el pedido
- **THEN** el pedido MUST crearse con `autorizacion_sistema='No Autorizado'`
- **AND** MUST registrarse motivo por días en snapshot

#### Scenario: Exceso de exposición monetaria

- **GIVEN** flag crédito ON, cliente con cupo $ finito y exposición + total pedido superan límite
- **WHEN** el vendedor confirma PED
- **THEN** MUST crearse comprobante con `autorizacion_sistema='No Autorizado'`
- **AND** MUST NOT abortar la transacción de alta por crédito
- **AND** MUST incluir motivo por monto en snapshot

#### Scenario: Flag crédito OFF — solo días

- **GIVEN** `ecom_credito_pedidos_activa` desactivado
- **WHEN** se confirma pedido
- **THEN** MUST evaluarse únicamente mora en días según reglas legacy
- **AND** MUST NOT persistir snapshot de exposición $
