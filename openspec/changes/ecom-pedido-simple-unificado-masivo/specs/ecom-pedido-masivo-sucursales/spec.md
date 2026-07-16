# Delta for ecom-pedido-masivo-sucursales

**Change:** `ecom-pedido-simple-unificado-masivo`  
**Base:** `openspec/specs/ecom-pedido-masivo-sucursales/spec.md`

## ADDED Requirements

### REQ-MAS-12 — Modo simple (1 sucursal)

La pantalla de pedido masivo MUST soportar `?modo=simple` como variante de una sola columna. En ese modo MUST mostrar etiquetas «Pedido simple» y MUST delegar requisitos de captura simple a `ecom-pedido-simple-unificado`.

#### Scenario: Param modo simple

- **GIVEN** cliente con al menos un domicilio activo
- **WHEN** abre pedido masivo con `?modo=simple`
- **THEN** MUST renderizar matriz de 1 columna
- **AND** MUST NOT requerir selección multi-sucursal

---

### REQ-MAS-13 — Campos draft para pedido simple

`EcomPedidoMasivoDraft` MUST incluir `cod_mov_origen` (nullable) e `id_domicilio_fijo` (nullable en esquema, obligatorio en runtime para `modo=simple` tras contexto definido). MUST persistirse en autoguardado junto con descuentos fila/pie existentes.

#### Scenario: Persistencia cod_mov_origen

- **GIVEN** draft abierto desde PED 999
- **WHEN** autoguarda tras editar celdas
- **THEN** `cod_mov_origen` MUST permanecer 999

---

### REQ-MAS-14 — Servicio carga PED → celdas

El backend MUST exponer `cargar_pedido_en_draft_masivo` (variante de `pedido_plantilla_service`) que copie renglones PED a celdas del draft para un único `id_cliente_domicilio`, con conversión a packs Bulto>Display.

#### Scenario: Carga exitosa

- **GIVEN** PED pendiente con 5 renglones
- **WHEN** invoca carga en draft simple
- **THEN** MUST crear/actualizar celdas con cantidades equivalentes
- **AND** MUST fijar `id_domicilio_fijo` del PED

---

### REQ-MAS-15 — Hero acciones en matriz

La UI masiva MUST integrar barra/hero de acciones para PED cargado o consultado: crédito, mail, repetir, PDF y anular cuando aplique, con paridad funcional del antiguo OrderShell.

#### Scenario: Acciones visibles en consulta cod_mov

- **GIVEN** pedido simple abierto en consulta con `cod_mov`
- **WHEN** renderiza la pantalla
- **THEN** MUST mostrar acciones PDF y Repetir
- **AND** MUST mostrar Enviar mail si el cliente tiene email

---

## MODIFIED Requirements

### REQ-MAS-01 — Matriz

El sistema MUST proveer pantalla desktop de carga masiva: filas = artículos; columnas = sucursales (`cliente_domicilio` no anulados del cliente), **excepto en `modo=simple` donde MUST mostrar exactamente una columna**. Cantidades MUST ser packs (misma semántica UOM que compra mayorista).

(Previously: siempre N columnas por todos los domicilios activos del cliente.)

#### Scenario: Columnas por domicilio

- **GIVEN** cliente con 3 domicilios activos
- **WHEN** el vendedor abre pedido masivo para ese cliente sin `modo=simple`
- **THEN** MUST ver 3 columnas de sucursal editables

#### Scenario: Modo simple una columna

- **GIVEN** cliente con 3 domicilios activos
- **WHEN** abre con `?modo=simple` y domicilio D1 fijado
- **THEN** MUST ver 1 columna para D1 únicamente

---

### REQ-MAS-02 — Catálogo filtrado

Los artículos del buscador MUST restringirse a marcas asignadas en ternas del par (viajante, cliente). En `modo=simple`, el buscador MUST NOT filtrar artículos por stock disponible en captura.

(Previously: solo restricción por ternas, sin mención explícita de stock en simple.)

#### Scenario: Ternas en masivo multi-sucursal

- **GIVEN** par viajante-cliente con marcas M1 y M2 en ternas
- **WHEN** busca artículos en pedido masivo estándar
- **THEN** MUST listar solo artículos de M1 y M2

#### Scenario: Sin filtro stock en simple

- **GIVEN** artículo de marca permitida sin stock
- **WHEN** busca en `modo=simple`
- **THEN** MUST poder agregarlo a la matriz

---

### REQ-MAS-03 — Un PED por sucursal con viajante operativo

Al confirmar, cada sucursal con suma de packs > 0 MUST generar un PED AdministraNET con `cliente_datos_adicionales.id_cliente_domicilio` correspondiente y `CodViajante` del **viajante efectivo** (operativo o `id_vendedor_usr`), no necesariamente el usuario logueado. En `modo=simple`, MUST generar como máximo **un** PED para `id_domicilio_fijo`.

(Previously: no distinguía límite de un PED en modo simple.)

#### Scenario: Supervisor confirma lote

- **GIVEN** supervisor operando como vendedor 21 con matriz cargada
- **WHEN** confirma pedido masivo multi-sucursal
- **THEN** cada PED creado MUST tener `CodViajante=21`

#### Scenario: Confirmación simple un PED

- **GIVEN** matriz simple con cantidades > 0 en una columna
- **WHEN** confirma
- **THEN** MUST crear exactamente 1 PED para el domicilio fijo

---

### REQ-MAS-04 — Borrador persistente

El sistema MUST autoguardar la matriz en borrador Postgres (`EcomPedidoMasivoDraft`). Tras cierre accidental o F5, el usuario MUST poder recuperar la carga desde el hub. Pedido simple MUST usar el **mismo** tipo de borrador masivo, no `EcomCart`.

(Previously: no explicitaba exclusión de EcomCart para simple.)

#### Scenario: Recuperación

- **GIVEN** borrador con celdas cargadas
- **WHEN** el usuario cierra el navegador y vuelve al hub
- **THEN** MUST poder Continuar y ver las mismas cantidades

#### Scenario: Hub sin borrador carrito para simple

- **GIVEN** captura iniciada en pedido simple
- **WHEN** el hub lista borradores
- **THEN** MUST aparecer como borrador masivo, no como carrito
