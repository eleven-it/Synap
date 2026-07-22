# Spec: Pedido masivo por sucursales

**Capability:** `ecom-pedido-masivo-sucursales`  
**Origen:** changes `ecom-pedidos-hub-kanban-masivo-sucursales` (archivado 13/07/2026), `ecom-pedidos-usabilidad-supervisor` (REQ-MAS-03/06 MOD, MAS-07–11, archivado 13/07/2026), `ecom-pedido-masivo-consolidado-hub` (22/07/2026)  
**Ruta:** `/ecom/mayoristapp/pedido-masivo-sucursales/`

## Requirements

### REQ-MAS-01 — Matriz
El sistema MUST proveer pantalla desktop de carga masiva: filas = artículos; columnas = sucursales (`cliente_domicilio` no anulados del cliente). Cantidades MUST ser packs (misma semántica UOM que compra mayorista).

#### Scenario: Columnas por domicilio
- **GIVEN** cliente con 3 domicilios activos
- **WHEN** el vendedor abre pedido masivo para ese cliente
- **THEN** MUST ver 3 columnas de sucursal editables

### REQ-MAS-02 — Catálogo filtrado
Los artículos del buscador MUST restringirse a marcas asignadas en ternas del par (viajante, cliente).

### REQ-MAS-03 — Un PED por sucursal con viajante operativo

Al confirmar, cada sucursal con suma de packs > 0 MUST generar un PED AdministraNET con `cliente_datos_adicionales.id_cliente_domicilio` correspondiente y `CodViajante` del **viajante efectivo** (operativo o `id_vendedor_usr`), no necesariamente el usuario logueado.

#### Scenario: Supervisor confirma lote

- **GIVEN** supervisor operando como vendedor 21 con matriz cargada
- **WHEN** confirma pedido masivo
- **THEN** cada PED creado MUST tener `CodViajante=21`

### REQ-MAS-04 — Borrador persistente
El sistema MUST autoguardar la matriz en borrador Postgres. Tras cierre accidental o F5, el usuario MUST poder recuperar la carga desde el hub.

#### Scenario: Recuperación
- **GIVEN** borrador con celdas cargadas
- **WHEN** el usuario cierra el navegador y vuelve al hub
- **THEN** MUST poder Continuar y ver las mismas cantidades

### REQ-MAS-05 — Rollback sin pérdida
Si falla la creación de cualquier PED del lote, el sistema MUST NO dejar el lote a medias (compensar/anular creados en la corrida), MUST devolver el draft a BORRADOR con los datos de celdas intactos, y MUST mostrar errores por sucursal/artículo para corregir.

#### Scenario: Fallo a mitad de lote
- **GIVEN** 3 sucursales con cantidad y la 2.ª falla al grabar
- **WHEN** termina el intento de confirmación
- **THEN** MUST quedar 0 PED netos del lote, draft en BORRADOR, y mensaje de error de la sucursal 2

### REQ-MAS-06 — UI canon slate/sky y modal Synap

La pantalla MUST seguir patrón MPR (header slate, matriz sticky, densidad desktop) con tokens `.pedidos-*` y paleta slate/sky. MUST NOT usar purple en CTAs, focos ni selección. La confirmación MUST usar modal canon Synap (`pedidos_modal.html`); MUST NOT usar `confirm()` nativo.

#### Scenario: Confirmación con modal

- **GIVEN** matriz con cantidades > 0
- **WHEN** el usuario pulsa confirmar lote
- **THEN** MUST abrir modal Synap con resumen
- **AND** MUST NOT invocar `window.confirm()`

### REQ-MAS-07 — Precio real por fila

La columna de precio MUST mostrar el precio calculado por `price_rules_engine` para la lista del cliente y MUST NOT limitarse a `Precio1V` referencial. MUST recalcular al cambiar descuentos de fila o pie.

#### Scenario: Precio distinto a Precio1V

- **GIVEN** artículo con Precio1V=100 y precio motor 85 para lista del cliente
- **WHEN** aparece en matriz masiva
- **THEN** columna precio MUST mostrar 85

### REQ-MAS-08 — Descuentos por fila y pie de lote

La matriz MUST permitir % descuento por fila (0–100) y descuento pie de lote aplicable al total del lote. MUST persistir en borrador y enviar a preview/confirmación.

#### Scenario: Descuento fila en matriz

- **GIVEN** fila artículo con precio neto 1000
- **WHEN** ingresa 10% descuento en la fila
- **THEN** preview MUST reflejar neto 900 para esa fila

#### Scenario: Descuento pie de lote

- **GIVEN** lote con neto gravado 5000
- **WHEN** aplica 5% descuento pie
- **THEN** preview MUST mostrar neto 4750 antes de IVA

### REQ-MAS-09 — descRenglon real del cliente

Al agregar artículo a la matriz, el % descuento fila MUST inicializarse con `cliente.descRenglon` (o equivalente legacy) cuando el usuario no lo override.

#### Scenario: Precarga descRenglon

- **GIVEN** cliente con `descRenglon=8`
- **WHEN** agrega artículo a la matriz
- **THEN** columna % desc MUST iniciar en 8

### REQ-MAS-10 — Preview de totales antes de confirmar

El sistema MUST exponer endpoint de preview agregado (netos, IVA, total) para el lote con descuentos fila/pie aplicados, invocable desde UI antes del modal de confirmación. MUST usar motor de precios backend; MUST NOT calcular totales solo en Alpine/JS.

#### Scenario: Preview previo a confirmar

- **GIVEN** matriz con 2 sucursales y descuentos cargados
- **WHEN** solicita preview
- **THEN** MUST devolver totales por sucursal y total lote coherentes con checkout

#### Scenario: Lote grande con límites

- **GIVEN** matriz que supera límite configurado de filas para preview
- **WHEN** solicita preview
- **THEN** MUST responder error en español o preview parcial documentado sin bloquear UI

### REQ-MAS-11 — Selector y banner supervisor

Pedido masivo MUST integrar selector vendedor operativo y banner «Operando como» cuando aplica `REQ-VOP-03/04`.

#### Scenario: Banner en masivo

- **GIVEN** supervisor operando como vendedor 21
- **WHEN** abre pedido masivo
- **THEN** MUST ver banner operativo persistente

---

### REQ-MAS-20 — Post-confirmación hacia resumen y hub

Tras confirmación exitosa de pedido masivo (`batch_checkout_masivo`), el sistema MUST redirigir o presentar descubrimiento claro del lote consolidado: enlace/CTA hacia resumen `/ecom/mayoristapp/pedidos/lote/<draft_id>/` y referencia al lane **Cargas masivas** del hub. MUST NOT dejar al usuario solo con N PED sueltos sin contexto de lote. Mensajes MUST estar en español.

#### Scenario: Redirección tras confirmar

- **GIVEN** matriz confirmada exitosamente con 3 sucursales
- **WHEN** finaliza checkout masivo
- **THEN** MUST navegar al resumen del lote o mostrar pantalla de éxito con CTA «Ver resumen del lote»
- **AND** MUST incluir `draft_id` del draft confirmado

#### Scenario: Descubrimiento desde hub

- **GIVEN** usuario que confirma y vuelve manualmente al hub
- **WHEN** abre `/ecom/mayoristapp/pedidos/`
- **THEN** MUST encontrar tarjeta `lote_masivo` en Cargas masivas (REQ-HUB-07)
- **AND** PED hijos MUST mostrar chip de lote (REQ-HUB-09)

#### Scenario: Confirmación con workflow comercial

- **GIVEN** subflag aprobación ON y PED pendientes tras confirmar
- **WHEN** muestra post-confirmación
- **THEN** MUST indicar que la autorización es a nivel lote
- **AND** MUST NOT sugerir aprobar PED uno a uno

---

### REQ-MAS-21 — Matriz read-only reutilizable

El componente de matriz masiva MUST soportar modo `readonly=1` reutilizable desde pestaña «Qué se cargó» del resumen de lote (REQ-LOT-03). En readonly MUST renderizar cantidades, precios y descuentos persistidos sin inputs editables, autoguardado ni CTAs de confirmación. MUST conservar semántica UOM packs y columnas por sucursal (REQ-MAS-01).

#### Scenario: Query readonly en resumen

- **GIVEN** draft confirmado con matriz persistida
- **WHEN** resumen embebe matriz con `readonly=1`
- **THEN** MUST mostrar mismas filas/columnas que captura original
- **AND** MUST NOT disparar POST de autoguardado ni abrir modal confirmar

#### Scenario: Readonly no habilita re-edición

- **GIVEN** matriz embebida en pestaña «Qué se cargó»
- **WHEN** usuario intenta modificar cantidades vía teclado o DOM
- **THEN** MUST NOT persistir cambios
- **AND** MUST NOT ofrecer CTA «Confirmar lote»

#### Scenario: Coherencia con captura activa

- **GIVEN** mismo draft en captura activa (BORRADOR) vs resumen confirmado
- **WHEN** compara estructura de matriz
- **THEN** columnas sucursal MUST coincidir con domicilios del draft al confirmar
- **AND** readonly MUST NOT requerir selector cliente/vendedor editable
