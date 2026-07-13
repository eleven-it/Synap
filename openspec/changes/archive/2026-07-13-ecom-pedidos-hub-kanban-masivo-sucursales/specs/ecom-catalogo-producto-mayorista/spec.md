# Spec delta: ecom-catalogo-producto-mayorista

## ADDED Requirements

### REQ-CAT-MAS-01 — Filtro por ternas
En el flujo de pedido masivo por sucursales, el listado/búsqueda de artículos MUST aplicar filtro `CodigoMarca IN marcas_asignadas(viajante, cliente)`. MUST NOT permitir override del vendedor para ver marcas no asignadas.

#### Scenario: Marca no asignada oculta
- **GIVEN** terna solo Marca A para el cliente
- **WHEN** busca un artículo de Marca B
- **THEN** MUST NOT aparecer en resultados del masivo
