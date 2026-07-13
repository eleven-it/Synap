# Spec: Vendedor → Cliente → Marca (territorio comercial)

**Capability:** `ecom-vendedor-cliente-marca`  
**Origen:** change `ecom-pedidos-hub-kanban-masivo-sucursales` (archivado 13/07/2026)  
**Tabla MySQL:** `ecom_vendedor_cliente_marca` (+ opcional `ecom_usuario_viajante`)

## Requirements

### REQ-VCM-01 — Terna comercial
El sistema MUST permitir configurar ternas `(CodViajante, id_cliente, CodMarca)` por empresa. Un mismo `(id_cliente, CodMarca)` MUST pertenecer a lo sumo a un viajante activo.

#### Scenario: Solape rechazado
- **GIVEN** Vendedor 1 tiene Cliente 1 → Marca A
- **WHEN** Vendedor 2 intenta asignar Marca A al Cliente 1
- **THEN** el sistema MUST rechazar e informar el vendedor dueño

### REQ-VCM-02 — Pantalla config
MUST existir pantalla desktop de configuración accesible solo con permiso `ecom.config_vendedor_cliente_marca` (o key final en seed). MUST listar, filtrar y CRUD ternas.

### REQ-VCM-03 — Mapeo usuario↔viajante
Si el login no resuelve `cod_viajante`, el sistema SHOULD permitir mapeo explícito usuario→viajante (1:1) administrable por supervisor, análogo a operario MPR.

### REQ-VCM-04 — Alcance clientes del vendedor
En flujos de pedido del vendedor, la búsqueda de clientes MUST limitarse a clientes con al menos una terna activa para su viajante (salvo supervisor con override).
