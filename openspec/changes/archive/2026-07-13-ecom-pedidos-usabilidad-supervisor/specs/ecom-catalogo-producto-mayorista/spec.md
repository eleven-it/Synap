# Delta for ecom-catalogo-producto-mayorista

**Change:** `ecom-pedidos-usabilidad-supervisor`

## ADDED Requirements

### REQ-CAT-004 — Filtro ternas en pedido simple

En el flujo `/ecom/mayoristapp/venta/`, el listado y búsqueda de artículos MUST aplicar filtro `CodigoMarca IN marcas_asignadas(viajante_efectivo, cliente_seleccionado)` cuando hay cliente y viajante efectivo. MUST reutilizar la misma lógica que pedido masivo (`REQ-CAT-MAS-01`).

#### Scenario: Marca no asignada oculta en simple

- **GIVEN** terna solo Marca A para (vendedor 21, Cliente 1)
- **WHEN** busca artículo de Marca B en pedido simple
- **THEN** MUST NOT aparecer en resultados

#### Scenario: Sin cliente seleccionado

- **GIVEN** pedido simple sin cliente en sesión
- **WHEN** busca artículos
- **THEN** MUST responder 400 o mensaje en español pidiendo seleccionar cliente antes del catálogo VCM

---

### REQ-CAT-005 — Lista de precios solo lectura

La lista de precios del cliente MUST resolverse en backend desde `cliente.ListaPrecio` / `codListaPrecio` en sesión. MUST NOT exponer API ni UI para override de lista en pedido simple o masivo.

#### Scenario: Lista fijada por cliente

- **GIVEN** cliente con `ListaPrecio=3`
- **WHEN** consulta catálogo o agrega ítem
- **THEN** precios MUST calcularse con lista 3
- **AND** MUST NOT existir parámetro de override en request del vendedor

---

### REQ-CAT-006 — Contexto lista para badge y PDF

El relay de selección de cliente MUST incluir en respuesta `listaPrecio` (código y nombre legible) para renderizar badge RO y enlace PDF en header de captura.

#### Scenario: Payload cliente con lista

- **GIVEN** cliente con lista 2 «Distribuidor»
- **WHEN** `cliente_seleccion_relay` confirma selección
- **THEN** respuesta MUST incluir código 2 y etiqueta «Distribuidor» para la UI
