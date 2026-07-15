# Spec: Catálogo de producto mayorista (ficha + listado paginado)

**Change:** `catalogo-carrito-checkout-mayorista`
**Artifact Type:** delta spec
**Fase:** P0 (lectura, sin escritura legacy)
**Target:** `ecom/` (portal mayorista). Reutiliza `price_rules_engine`, `catalogo_*`, `mayoristapp_session`.
**Legacy:** `administraNET-ecom/mayoristapp/ajax-articulos.php`, `relay-art.php`, `inventario/includes/mas-vendidos.php`.

---

## ADDED Requirements

### REQ-CAT-001: Listado paginado de artículos por filtros

El sistema **MUST** exponer un endpoint que devuelva un listado **paginado** de artículos activos aplicando los filtros del catálogo (rubro, subrubro, marca, laboratorio, proveedor, TACC, promo, texto/código) y con el **precio calculado** para la lista de precios del cliente en sesión mediante el motor existente (`price_rules_engine`).

**Acceptance Scenarios:**

```gherkin
Escenario: Listado por rubro con precio del cliente
  DADO un cliente seleccionado en sesión con lista de precio 2
  Y un rubro con 40 artículos activos
  CUANDO se solicita el listado del rubro con página 1 y tamaño 20
  ENTONCES el sistema devuelve 20 artículos con: código, nombre, imagen, stock disponible y precio calculado para la lista 2
  Y devuelve metadatos de paginación (total, página, tamaño, total_páginas)
```

```gherkin
Escenario: Búsqueda por texto o código
  DADO un término de búsqueda "amoxi"
  CUANDO se solicita el listado con ese término
  ENTONCES el sistema devuelve solo artículos cuyo código, nombre o id_manual coincidan
  Y respeta los demás filtros activos y la paginación
```

```gherkin
Escenario: Sin cliente seleccionado
  DADO que no hay cliente ni lista de precio en sesión
  CUANDO se solicita el listado
  ENTONCES el sistema usa la lista de precio por defecto de sesión/empresa
  Y si tampoco existe, responde 400 con mensaje en español indicando seleccionar cliente
```

---

### REQ-CAT-002: Ficha de detalle de artículo

El sistema **MUST** exponer un endpoint de **detalle** de un artículo (por `IDArt` o código) que devuelva la información necesaria para la ficha de producto: identificación (código, id_manual, nombre, descripción), imagen, **stock disponible por depósito**, **precio calculado** (neto y con IVA según `iva_incluido` de sesión), **promociones vigentes** y datos de presentación/bulto (unidad/display/bulto/pallet y multiplicadores).

**Acceptance Scenarios:**

```gherkin
Escenario: Detalle con promoción vigente
  DADO un artículo con promoción vigente para la lista del cliente
  CUANDO se solicita su detalle
  ENTONCES el sistema devuelve el precio con la promoción aplicada
  Y expone la promoción (tipo, porcentaje/cantidad) para mostrarla en la ficha
```

```gherkin
Escenario: Detalle de artículo inexistente o inactivo
  DADO un IDArt que no existe o está inactivo
  CUANDO se solicita su detalle
  ENTONCES el sistema responde 404 con mensaje en español
```

```gherkin
Escenario: Stock por depósito
  DADO un artículo con stock en 2 depósitos
  CUANDO se solicita su detalle
  ENTONCES el sistema devuelve el stock disponible por depósito
  Y el disponible del depósito activo de la sesión
```

---

### REQ-CAT-003: Consistencia de precios con el motor existente

El precio devuelto por el listado (REQ-CAT-001) y por la ficha (REQ-CAT-002) **MUST** calcularse con el mismo motor (`price_rules_engine.calcular_precio_con_motor`) que usan los relays de precio actuales, garantizando idéntica precedencia de reglas y promociones. **MUST NOT** duplicarse la lógica de cálculo.

**Acceptance Scenarios:**

```gherkin
Escenario: Paridad de precio listado vs relay de precio
  DADO un artículo, una lista y un cliente
  CUANDO se obtiene su precio desde el listado del catálogo
  Y se obtiene su precio desde el relay de precio existente
  ENTONCES ambos precios coinciden exactamente
```

---

## Implementation Constraints

- **Solo lectura:** ninguna escritura a MySQL legacy en esta fase.
- **Parametrización SQL** obligatoria (`%s`) y normalización con `core.utils.administranet_types`.
- **Permiso:** `EcomMayoristappSessionPermission` (requiere `base_empresa` en sesión).
- **Paginación** en servidor (LIMIT/OFFSET) con tope máximo de tamaño de página.
- **Imágenes:** resolver ruta/URL de imagen del artículo (paridad `foto.php`) sin bloquear el listado (lazy/URL).
- **Reutilizar** `price_rules_engine` y los servicios `catalogo_*` existentes; extender, no reimplementar.

---

## Size Budget

**Escenarios:** 8 · **Estado:** draft

## Metadata

- **Author role:** SDD (agente principal)
- **Created:** 2026-07-02
- **Status:** draft (pendiente validación de alcance con el usuario)

---

## Extensions — pedido masivo (2026-07-13)

### REQ-CAT-MAS-01 — Filtro por ternas
En el flujo de pedido masivo por sucursales, el listado/búsqueda de artículos MUST aplicar filtro `CodigoMarca IN marcas_asignadas(viajante, cliente)`. MUST NOT permitir override del vendedor para ver marcas no asignadas.

#### Scenario: Marca no asignada oculta
- **GIVEN** terna solo Marca A para el cliente
- **WHEN** busca un artículo de Marca B
- **THEN** MUST NOT aparecer en resultados del masivo

---

## Extensions — pedido simple y lista RO (2026-07-13)

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
