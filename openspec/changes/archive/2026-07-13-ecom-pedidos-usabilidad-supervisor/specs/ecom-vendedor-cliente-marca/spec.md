# Delta for ecom-vendedor-cliente-marca

**Change:** `ecom-pedidos-usabilidad-supervisor`

## MODIFIED Requirements

### REQ-VCM-04 — Alcance clientes y catálogo por viajante efectivo

En flujos de pedido simple (`/venta/`) y masivo, la búsqueda de clientes y el catálogo de artículos MUST limitarse a ternas activas del **viajante efectivo** (`cod_viajante_operativo` o `id_vendedor_usr`). Un supervisor operando por otro vendedor MUST ver solo clientes/marcas de la cartera de ese vendedor elegido, no la unión de toda su cartera supervisor salvo que el propio supervisor sea el operativo. MUST NOT depender solo de `cliente.CodViajante` cuando existen ternas VCM para la empresa.

(Previously: limitaba clientes por terna del viajante logueado; no consideraba viajante operativo ni catálogo simple.)

#### Scenario: VCM en pedido simple con operativo

- **GIVEN** supervisor operando como vendedor 21 con terna Cliente A → Marca X
- **WHEN** busca clientes en pedido simple
- **THEN** Cliente A MUST aparecer
- **AND** clientes sin terna para vendedor 21 MUST NOT aparecer

#### Scenario: Catálogo filtrado por marcas de terna en simple

- **GIVEN** terna vendedor 21 + Cliente A solo Marca X
- **WHEN** busca artículos de Marca Y en pedido simple con Cliente A seleccionado
- **THEN** artículos Marca Y MUST NOT aparecer

#### Scenario: Supervisor sin vendedor elegido usa propio viajante

- **GIVEN** supervisor con `id_vendedor_usr=10` y `cod_viajante_operativo=10`
- **WHEN** busca clientes
- **THEN** MUST aplicar ternas del viajante 10

## ADDED Requirements

### REQ-VCM-05 — Paridad simple ↔ masivo en filtros ternas

El filtro de clientes en pedido simple MUST usar la misma semántica que `listar_clientes_con_ternas` del masivo. El filtro de marcas/artículos MUST usar equivalente a `buscar_articulos_filtrados_ternas` con viajante efectivo y cliente seleccionado.

#### Scenario: Cliente visible en masivo también en simple

- **GIVEN** cliente visible en pedido masivo para par (vendedor 21, Cliente A)
- **WHEN** mismo supervisor opera como 21 en pedido simple
- **THEN** Cliente A MUST ser seleccionable en predictive
