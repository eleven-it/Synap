# Delta spec: tiendanube-customer-mapping

## ADDED Requirements

### Requirement: Validación de IDs en formulario de mapeo

Al crear o editar un `CustomerMapping`, si se informa `tiendanube_id` MUST verificarse contra la API Tienda Nube; si se informa `adminet_codigo` MUST verificarse contra AdministraNET.

#### Scenario: ID Tienda Nube inexistente
- **WHEN** el usuario guarda con un `tiendanube_id` que la API no reconoce
- **THEN** el formulario MUST rechazar con mensaje en español

#### Scenario: Código AdministraNET inexistente
- **WHEN** el usuario guarda con `adminet_codigo` que no existe en `cliente`
- **THEN** el formulario MUST rechazar con mensaje en español

### Requirement: Unicidad adminet_codigo en mapeos

`adminet_codigo` MUST ser único entre mapeos cuando no es nulo.

#### Scenario: Código AdministraNET ya mapeado
- **WHEN** otro `CustomerMapping` ya usa el mismo `adminet_codigo`
- **THEN** MUST rechazar el guardado

### Requirement: Anti-duplicado en alta AdministraNET

`create_customer` MUST NOT insertar si ya existe cliente con mismo email o CUIT (distinto de `-` / vacío).

#### Scenario: Email duplicado en MySQL
- **WHEN** sync intenta crear cliente y el email ya existe en `cliente`
- **THEN** MUST fallar con mensaje que incluya el código existente

### Requirement: Listado incluye mapeos incompletos

La lista `/customers/` MUST mostrar mapeos sin vínculo completo, con indicador visual y filtro opcional.

#### Scenario: Mapeo solo Tienda Nube
- **WHEN** existe mapeo con `tiendanube_id` sin `adminet_codigo`
- **THEN** MUST aparecer en lista como incompleto

### Requirement: Sync explícito desde UI

La lista y el detalle MUST ofrecer acción **Sincronizar ahora** que invoque sync inmediato y muestre resultado.

### Requirement: Defaults seguros al crear

Nuevo mapeo manual MUST tener `sync_enabled=False` y `sync_direction=tiendanube_to_adminet` por defecto.

#### Scenario: Creación sin activar sync
- **WHEN** el usuario guarda un mapeo nuevo sin marcar sync
- **THEN** MUST NOT encolar Celery automático
