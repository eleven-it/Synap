# Delta for ecom-pedido-masivo-sucursales

**Change:** `ecom-pedido-masivo-ux-contexto`

## ADDED Requirements

### REQ-MAS-12 — Barra de contexto compacta

Desde breakpoint `lg`, la pantalla MUST mostrar vendedor operativo y selector de cliente en **una sola fila** dentro de una barra de contexto. El campo vendedor MUST usar ancho semántico acotado (`w-56` o equivalente); el campo cliente MUST usar ancho semántico acotado (`w-72` o equivalente). Esos controles MUST NOT expandirse con `flex-1` ni ocupar el ancho completo del viewport. La barra MUST reutilizar el selector vendedor existente (`pedidos_selector_vendedor.html`) embebido en el layout compacto.

#### Scenario: Fila compacta en desktop

- **GIVEN** viewport ≥ `lg` en pedido masivo
- **WHEN** la pantalla renderiza la barra de contexto
- **THEN** vendedor y cliente MUST aparecer en la misma fila
- **AND** ninguno MUST ocupar el ancho total del viewport

#### Scenario: Anchos semánticos

- **GIVEN** barra de contexto visible
- **WHEN** el usuario inspecciona los campos vendedor y cliente
- **THEN** vendedor MUST respetar ancho ~`w-56` y cliente ~`w-72`
- **AND** MUST NOT aplicarse `flex-1` a esos campos

---

### REQ-MAS-13 — Auto-apertura de borrador al elegir cliente

La UI MUST NOT mostrar botón ni CTA «Abrir matriz». Al elegir un cliente válido (`elegirCliente`), el sistema MUST invocar automáticamente la apertura de borrador mediante el POST existente `…/abrir/` (misma semántica que `abrirCliente()`). MUST mostrar estado inline de carga (`abriendo`/spinner) en la barra de contexto durante la petición. MUST impedir doble POST concurrente (guard anti reentrada).

#### Scenario: Selección abre matriz sin clic extra

- **GIVEN** pantalla sin borrador activo (`!draftId`)
- **WHEN** el vendedor elige un cliente con sucursales activas
- **THEN** MUST ejecutarse POST `…/abrir/` automáticamente
- **AND** MUST NOT requerirse clic en «Abrir matriz»
- **AND** al completar MUST quedar `draftId` y columnas de sucursal disponibles

#### Scenario: Cliente sin sucursales

- **GIVEN** cliente elegido sin domicilios activos
- **WHEN** intenta auto-apertura
- **THEN** MUST mostrar alerta operativa en español (amber)
- **AND** MUST NOT bloquear el resto de la UI

#### Scenario: Anti doble POST

- **GIVEN** POST `…/abrir/` en curso (`abriendo=true`)
- **WHEN** llega otra selección o reintento de apertura
- **THEN** MUST ignorarse la segunda invocación hasta finalizar la primera

---

### REQ-MAS-14 — Matriz siempre visible con guía

El shell de la matriz (cabecera de columnas, contenedor scroll, zona de filas) MUST permanecer visible desde el primer render. MUST NOT existir card «Paso 1» ni bloque que oculte la matriz hasta tener borrador. Cuando `!draftId` o no hay filas de artículos, MUST mostrarse copy guía operativo en el área de filas indicando elegir cliente o agregar artículos según corresponda.

#### Scenario: Carga inicial sin borrador

- **GIVEN** usuario abre pedido masivo sin borrador previo
- **WHEN** la página termina de cargar
- **THEN** MUST ver el shell de matriz (no solo cards de pasos)
- **AND** MUST ver mensaje guía para elegir cliente

#### Scenario: Borrador sin artículos

- **GIVEN** borrador abierto (`draftId` presente) sin filas
- **WHEN** renderiza la matriz
- **THEN** MUST mantener visible cabecera de sucursales
- **AND** MUST mostrar copy guía para agregar artículos

---

### REQ-MAS-15 — Sticky columnas fijas en scroll horizontal

En scroll horizontal de la matriz, las columnas **Artículo**, **Precio** y **% Desc.** MUST permanecer fijas (sticky) visibles mediante tokens `.pm-matrix-*` y sincronización `syncPmStickyCols`. La columna Artículo MUST ajustar ancho al contenido (`fit-content`) con tope máximo configurable (cap) para evitar desbordes. Los offsets sticky MUST recalcularse tras auto-apertura de borrador y cambios de layout.

#### Scenario: Scroll horizontal mantiene columnas fijas

- **GIVEN** matriz con N sucursales que exceden el ancho del viewport
- **WHEN** el usuario hace scroll horizontal
- **THEN** columnas Artículo, Precio y % Desc. MUST permanecer visibles y alineadas

#### Scenario: Ancho artículo con cap

- **GIVEN** fila con descripción larga de artículo
- **WHEN** renderiza la columna Artículo
- **THEN** ancho MUST basarse en contenido hasta el cap máximo
- **AND** MUST NOT empujar columnas sticky fuera de alineación

---

### REQ-MAS-16 — Densidad de inputs cantidad y descuento

Los inputs de cantidad (packs por sucursal) y % descuento por fila MUST usar densidad desktop acotada (altura ~`h-8`, tipografía ~`text-xs` o tokens `.pedidos-*` equivalentes). MUST mantener accesibilidad de foco y legibilidad operativa en captura masiva.

#### Scenario: Inputs compactos en matriz

- **GIVEN** matriz con filas editables
- **WHEN** el usuario edita cantidad o % descuento
- **THEN** inputs MUST renderizarse con altura y tipografía densas (~`h-8` / `text-xs`)
- **AND** MUST permanecer usables con teclado y foco visible

---

### REQ-MAS-17 — Badge lista de precios en barra de contexto

La barra de contexto MUST mostrar badge de lista de precios del cliente (solo lectura, comportamiento existente del backend) **antes y después** de abrir borrador, no únicamente tras `draftId`. MUST NOT permitir override de lista desde esta pantalla.

#### Scenario: Badge visible sin borrador

- **GIVEN** cliente seleccionado en barra de contexto sin borrador aún
- **WHEN** la UI muestra la barra
- **THEN** MUST aparecer badge de lista de precios en solo lectura

#### Scenario: Badge persistente con borrador

- **GIVEN** borrador abierto para el cliente
- **WHEN** renderiza la barra de contexto
- **THEN** MUST mantener el mismo badge de lista en solo lectura

---

### REQ-MAS-18 — Acordeón por sucursal en viewport estrecho

En viewports por debajo de `lg`, la presentación MAY agrupar columnas de sucursal en bloques colapsables (acordeón) por `id_cliente_domicilio`, sin alterar el modelo de datos Alpine ni contratos backend. En desktop (`≥lg`) MUST conservarse la matriz tabular actual.

#### Scenario: Desktop sin acordeón

- **GIVEN** viewport ≥ `lg` con matriz cargada
- **WHEN** el usuario interactúa con la matriz
- **THEN** MUST ver tabla horizontal con columnas por sucursal (sin acordeón obligatorio)

#### Scenario: Móvil con acordeón opcional

- **GIVEN** viewport < `lg` y acordeón habilitado en la implementación
- **WHEN** el usuario expande una sucursal
- **THEN** MUST editar cantidades de esa sucursal con los mismos valores que en desktop
- **AND** colapsar MUST NOT perder datos en memoria ni borrador

---

### REQ-MAS-19 — Panel preview responsive

El panel de preview/totales MUST adaptarse a viewport estrecho (móvil/tablet): apilamiento legible, sin desbordes horizontales críticos, y acciones de preview/confirmar accesibles. MUST reutilizar endpoint preview existente (`REQ-MAS-10`); MUST NOT introducir cálculo de totales solo en cliente.

#### Scenario: Preview usable en tablet

- **GIVEN** matriz con cantidades y viewport tablet
- **WHEN** solicita preview de totales
- **THEN** panel MUST mostrar totales por sucursal y lote sin scroll horizontal obligatorio
- **AND** botón confirmar MUST permanecer alcanzable

#### Scenario: Preview en móvil

- **GIVEN** viewport móvil con borrador activo
- **WHEN** abre panel preview
- **THEN** contenido MUST apilarse verticalmente de forma legible
- **AND** MUST NOT ocultar totales críticos del lote
