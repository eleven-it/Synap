# Delta for ecom-pedido-masivo-sucursales

**Change:** `ecom-pedidos-usabilidad-supervisor`

## MODIFIED Requirements

### REQ-MAS-03 — Un PED por sucursal con viajante operativo

Al confirmar, cada sucursal con suma de packs > 0 MUST generar un PED AdministraNET con `cliente_datos_adicionales.id_cliente_domicilio` correspondiente y `CodViajante` del **viajante efectivo** (operativo o `id_vendedor_usr`), no necesariamente el usuario logueado.

(Previously: CodViajante del vendedor logueado vía `id_vendedor_usr` directo.)

#### Scenario: Supervisor confirma lote

- **GIVEN** supervisor operando como vendedor 21 con matriz cargada
- **WHEN** confirma pedido masivo
- **THEN** cada PED creado MUST tener `CodViajante=21`

---

### REQ-MAS-06 — UI canon slate/sky y modal Synap

La pantalla MUST seguir patrón MPR (header slate, matriz sticky, densidad desktop) con tokens `.pedidos-*` y paleta slate/sky. MUST NOT usar purple en CTAs, focos ni selección. La confirmación MUST usar modal canon Synap (`pedidos_modal.html`); MUST NOT usar `confirm()` nativo.

(Previously: UI MPR con purple en CTAs; confirmación con `confirm()`.)

#### Scenario: Confirmación con modal

- **GIVEN** matriz con cantidades > 0
- **WHEN** el usuario pulsa confirmar lote
- **THEN** MUST abrir modal Synap con resumen
- **AND** MUST NOT invocar `window.confirm()`

## ADDED Requirements

### REQ-MAS-07 — Precio real por fila

La columna de precio MUST mostrar el precio calculado por `price_rules_engine` para la lista del cliente y MUST NOT limitarse a `Precio1V` referencial. MUST recalcular al cambiar descuentos de fila o pie.

#### Scenario: Precio distinto a Precio1V

- **GIVEN** artículo con Precio1V=100 y precio motor 85 para lista del cliente
- **WHEN** aparece en matriz masiva
- **THEN** columna precio MUST mostrar 85

---

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

---

### REQ-MAS-09 — descRenglon real del cliente

Al agregar artículo a la matriz, el % descuento fila MUST inicializarse con `cliente.descRenglon` (o equivalente legacy) cuando el usuario no lo override.

#### Scenario: Precarga descRenglon

- **GIVEN** cliente con `descRenglon=8`
- **WHEN** agrega artículo a la matriz
- **THEN** columna % desc MUST iniciar en 8

---

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

---

### REQ-MAS-11 — Selector y banner supervisor

Pedido masivo MUST integrar selector vendedor operativo y banner «Operando como» cuando aplica `REQ-VOP-03/04`.

#### Scenario: Banner en masivo

- **GIVEN** supervisor operando como vendedor 21
- **WHEN** abre pedido masivo
- **THEN** MUST ver banner operativo persistente
