# Spec delta: ecom-pedido-venta-shell

## ADDED Requirements

### REQ-VTA-01 — Pantalla canónica de pedido de venta
El sistema MUST exponer OrderShell en `/ecom/mayoristapp/venta/` para crear un PED (borrador `EcomCart`) y para abrir un PED existente con `?cod_mov=`.

#### Scenario: Alta sin cod_mov
- **GIVEN** usuario autenticado con permiso de pedidos
- **WHEN** abre `/ecom/mayoristapp/venta/`
- **THEN** MUST mostrar shell de carga (cliente, catálogo, carrito, confirmar)

#### Scenario: Abrir PED existente
- **GIVEN** un `CodigoMovimiento` PED válido
- **WHEN** abre `/ecom/mayoristapp/venta/?cod_mov={id}`
- **THEN** MUST cargar cabecera y líneas del PED en la misma shell

### REQ-VTA-02 — Modo según estado
Si el PED tiene `Estado='Pendiente'` y `Anulado≠Si`, el shell MUST permitir editar líneas. Si el PED ya entró en producción (`Estado` distinto de `Pendiente`) o está anulado, el shell MUST ser de solo lectura (sin confirmar checkout ni mutar cantidades).

#### Scenario: Pendiente editable
- **GIVEN** PED Pendiente no anulado
- **WHEN** se abre en `/venta/?cod_mov=`
- **THEN** el usuario MUST poder modificar cantidades / renglones en la UI

#### Scenario: En preparación solo lectura
- **GIVEN** PED con `Estado='En preparación'`
- **WHEN** se abre en `/venta/?cod_mov=`
- **THEN** MUST NOT permitir confirmar ni editar cantidades

### REQ-VTA-03 — Acciones de gestión en la shell
Con un PED cargado, la shell MUST ofrecer según corresponda: Repetir pedido, Anular (solo si `puede_anular`), Ver PDF, Enviar mail — reutilizando las APIs existentes del detalle.

#### Scenario: Anular visible solo si permitido
- **GIVEN** cabecera con `puede_anular=true`
- **WHEN** se muestra el hero de venta
- **THEN** MUST mostrar acción Anular

### REQ-VTA-04 — Confirmar edición de Pendiente
Al confirmar cambios sobre un PED Pendiente, el sistema MUST requerir modal Synap y MUST ejecutar anulación del origen + alta de un nuevo PED vía checkout (no UPDATE in-place del mismo `CodigoMovimiento` en esta entrega).

#### Scenario: Modal de confirmación
- **GIVEN** modo editar Pendiente con cambios en carrito
- **WHEN** el usuario confirma cambios
- **THEN** MUST mostrar modal de riesgos (anula origen, crea nuevo número) y solo entonces invocar anulación + checkout
