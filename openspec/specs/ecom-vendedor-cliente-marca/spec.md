# Spec: Vendedor → Cliente → Sucursal → Marca (territorio comercial)

**Capability:** `ecom-vendedor-cliente-marca`  
**Origen:** change `ecom-pedidos-hub-kanban-masivo-sucursales` (archivado 13/07/2026)  
**Tabla MySQL:** `ecom_vendedor_cliente_marca` (+ opcional `ecom_usuario_viajante`)

## Requirements

### REQ-VCM-01 — Cuaterna comercial
El sistema MUST permitir configurar cuaternas `(CodViajante, id_cliente, id_cliente_domicilio, CodMarca)` por empresa. Un mismo `(id_cliente, id_cliente_domicilio, CodMarca)` MUST pertenecer a lo sumo a un viajante activo.

#### Scenario: Solape rechazado en misma sucursal
- **GIVEN** Vendedor 1 tiene Cliente 1 → Sucursal A → Marca X
- **WHEN** Vendedor 2 intenta asignar Marca X al Cliente 1 en Sucursal A
- **THEN** el sistema MUST rechazar e informar el vendedor dueño

#### Scenario: Misma marca en otra sucursal permitida
- **GIVEN** Vendedor 1 tiene Cliente 1 → Sucursal A → Marca X
- **WHEN** Vendedor 2 asigna Marca X al Cliente 1 en Sucursal B
- **THEN** el sistema MUST aceptar la cuaterna

### REQ-VCM-02 — Pantalla config
MUST existir pantalla desktop de configuración accesible solo con permiso `ecom.config_vendedor_cliente_marca`. MUST listar, filtrar y CRUD cuaternas con combobox Sucursal dependiente de Cliente.

### REQ-VCM-03 — Mapeo usuario↔viajante
Si el login no resuelve `cod_viajante`, el sistema SHOULD permitir mapeo explícito usuario→viajante (1:1) administrable por supervisor, análogo a operario MPR.

### REQ-VCM-04 — Alcance clientes y catálogo por viajante efectivo

En flujos de pedido simple (`/venta/`) y masivo, la búsqueda de clientes y el catálogo de artículos MUST limitarse a cuaternas activas del **viajante efectivo** (`cod_viajante_operativo` o `id_vendedor_usr`). Un supervisor operando por otro vendedor MUST ver solo clientes/marcas de la cartera de ese vendedor elegido.

#### Scenario: VCM en pedido simple con operativo

- **GIVEN** supervisor operando como vendedor 21 con cuaterna Cliente A → Sucursal S → Marca X
- **WHEN** busca clientes en pedido simple
- **THEN** Cliente A MUST aparecer
- **AND** clientes sin cuaterna para vendedor 21 MUST NOT aparecer

#### Scenario: Catálogo filtrado por marcas de cuaterna en simple

- **GIVEN** cuaternas vendedor 21 + Cliente A solo Marca X (todas sucursales)
- **WHEN** busca artículos de Marca Y en pedido simple con Cliente A seleccionado
- **THEN** artículos Marca Y MUST NOT aparecer

#### Scenario: Catálogo con domicilio en sesión

- **GIVEN** cuaternas vendedor 21 + Cliente A con Marca X solo en Sucursal S1
- **WHEN** busca artículos con `id_cliente_domicilio=S1` en sesión o request
- **THEN** solo artículos Marca X MUST aparecer para esa sucursal

### REQ-VCM-05 — Paridad simple ↔ masivo en filtros cuaternas

El filtro de clientes en pedido simple MUST usar la misma semántica que `listar_clientes_con_ternas` del masivo (cliente con ≥1 cuaterna activa). El filtro de marcas/artículos MUST usar `marcas_asignadas_viajante_cliente` con viajante efectivo, cliente y opcionalmente sucursal.

#### Scenario: Cliente visible en masivo también en simple

- **GIVEN** cliente visible en pedido masivo para par (vendedor 21, Cliente A)
- **WHEN** mismo supervisor opera como 21 en pedido simple
- **THEN** Cliente A MUST ser seleccionable en predictive

### REQ-VCM-06 — Sucursales en pedido masivo

Cuando VCM está activo, `listar_sucursales_cliente` MUST devolver solo domicilios con ≥1 cuaterna activa para el par (viajante efectivo, cliente).

### REQ-VCM-07 — Migración ternas existentes

Al aplicar el proveedor de esquema en una base con ternas activas sin `id_cliente_domicilio`, el sistema MUST expandir cada fila a una cuaterna por domicilio activo del cliente y anular la fila sin sucursal. Si el cliente no tiene domicilios, MUST conservar `id_cliente_domicilio=0`.

### REQ-VCM-08 — Validación carrito simple

Con VCM activo, `agregar_item` MUST rechazar artículos cuya marca no esté en las cuaternas del viajante de sesión, cliente del carrito y domicilio del carrito/sesión si existe; sin domicilio MUST usar unión de marcas del cliente.
