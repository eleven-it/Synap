# Delta for ecom-pedidos-hub-kanban

## MODIFIED Requirements

### REQ-HUB-02 — Columnas de estado

El Kanban/Lista MUST incluir al menos: Borrador, Enviado, Por autorizar (comercial), **Pendiente crédito Finanzas**, Aprobado, Anulado. Borrador MUST incluir carritos `EcomCart` con ítems y borradores de pedido masivo del usuario. Cuando `ecom_credito_pedidos_activa` ON, PED con `autorizacion_sistema='No Autorizado'` pendiente de Finanzas MUST aparecer en columna **Pendiente crédito Finanzas** y MUST NOT mezclarse con **Por autorizar** comercial.

(Previously: columna única «Por autorizar» mezclaba crédito y comercial.)

#### Scenario: Borrador visible

- **GIVEN** un borrador masivo en estado BORRADOR del usuario
- **WHEN** abre el hub
- **THEN** MUST aparecer en Borrador con CTA Continuar

#### Scenario: PED pendiente Finanzas separado de comercial

- **GIVEN** PED `No Autorizado` en cola Finanzas sin pendiente comercial
- **WHEN** supervisor abre hub con flag crédito ON
- **THEN** MUST mostrarse en columna «Pendiente crédito Finanzas»
- **AND** MUST NOT aparecer en «Por autorizar» comercial

#### Scenario: PED con ambos pendientes

- **GIVEN** PED con crédito Finanzas pendiente y descuento comercial pendiente
- **WHEN** se renderiza hub
- **THEN** MUST reflejar ambos estados en columnas distintas sin duplicar tarjeta

## ADDED Requirements

### REQ-HUB-11 — Cola Finanzas y permisos

Con `ecom_credito_pedidos_activa` ON, el hub MUST exponer CTAs Aprobar/Rechazar crédito solo a usuarios con `finance.credito.aprobar`. CTAs comerciales MUST NOT sustituir acciones Finanzas.

#### Scenario: CTA Finanzas visible

- **GIVEN** usuario con `finance.credito.aprobar` y PED en columna Finanzas
- **WHEN** renderiza tarjeta
- **THEN** MUST mostrar CTA de aprobación crédito
- **AND** MUST NOT mostrar CTA comercial de autorización por crédito

#### Scenario: Flag crédito OFF oculta columna Finanzas

- **GIVEN** `ecom_credito_pedidos_activa` OFF
- **WHEN** abre hub
- **THEN** MUST NOT mostrar columna «Pendiente crédito Finanzas»
- **AND** MUST conservar columnas legacy existentes
