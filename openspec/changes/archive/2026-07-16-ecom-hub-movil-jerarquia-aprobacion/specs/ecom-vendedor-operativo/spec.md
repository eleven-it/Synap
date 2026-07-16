# Spec: Vendedor operativo (sesión mayoristapp)

**Capability:** `ecom-vendedor-operativo`  
**Origen:** changes `ecom-pedidos-usabilidad-supervisor` (13/07/2026), `ecom-hub-movil-jerarquia-aprobacion` (16/07/2026)

## Purpose

Sesión operativa mayoristapp: supervisor elige vendedor, opera en su nombre con cartera acotada y resolución única de `CodViajante` efectivo.

## Requirements

### REQ-VOP-01 — Viajante operativo en sesión

El sistema MUST persistir `mayoristapp.cod_viajante_operativo` en sesión. Por defecto MUST ser igual a `id_vendedor_usr` del usuario autenticado. MUST NOT quedar nulo si el usuario tiene viajante asignado.

#### Scenario: Vendedor sin selección explícita

- **GIVEN** un vendedor con `id_vendedor_usr=42` autenticado en mayoristapp
- **WHEN** inicia sesión o entra a flujos de pedido
- **THEN** `cod_viajante_operativo` MUST ser `42`

#### Scenario: Supervisor sin vendedor elegido aún

- **GIVEN** un supervisor con `id_vendedor_usr=10` y cartera cargada
- **WHEN** abre pedido simple sin haber elegido otro vendedor
- **THEN** `cod_viajante_operativo` MUST ser `10` hasta que seleccione otro

---

### REQ-VOP-02 — Hidratación de cartera supervisor

Con workflow OFF, el sistema MUST cargar `vendedor_a_cargo` desde JSON legacy (`ecom_vendedores_a_cargo_*`) al hidratar sesión mayoristapp cuando `supervisor_venta='Si'`. Con workflow ON MUST resolver la cartera desde el árbol org (`alcance_comercial`). MUST normalizar la lista a enteros (`CodViajante`) válidos.

#### Scenario: Supervisor con workflow ON

- **GIVEN** master ON y supervisor con subárbol org `[20, 21]`
- **WHEN** se hidrata la sesión mayoristapp
- **THEN** `vendedor_a_cargo` MUST contener el subárbol org

#### Scenario: Supervisor con cartera legacy (workflow OFF)

- **GIVEN** master OFF y usuario con `supervisor_venta='Si'` y vendedores `[20, 21]` en JSON legacy
- **WHEN** se hidrata la sesión mayoristapp
- **THEN** `vendedor_a_cargo` MUST contener `[20, 21]`

#### Scenario: Vendedor no supervisor

- **GIVEN** usuario con `supervisor_venta='No'`
- **WHEN** se hidrata la sesión
- **THEN** `vendedor_a_cargo` MUST estar vacío o ignorarse para alcance

---

### REQ-VOP-03 — Selector de vendedor para supervisor

Si `supervisor_venta='Si'` y `vendedor_a_cargo` no está vacío, el sistema MUST exponer selector de vendedor operativo en flujos de pedido (simple y masivo). Con workflow ON el selector MUST limitarse al alcance org; con workflow OFF MUST usar cartera JSON legacy. La opción MUST incluir al propio supervisor y cada `CodViajante` de su cartera.

#### Scenario: Selector con alcance org

- **GIVEN** master ON, supervisor con cartera org `[20, 21]`
- **WHEN** abre el selector de vendedor
- **THEN** MUST mostrar solo `20`, `21` y el propio supervisor

#### Scenario: Cambio de vendedor operativo

- **GIVEN** supervisor con cartera `[20, 21]`
- **WHEN** elige vendedor `21` en el selector
- **THEN** `cod_viajante_operativo` MUST pasar a `21`
- **AND** búsquedas de cliente/catálogo MUST usar `21` como viajante efectivo

#### Scenario: Vendedor sin permiso supervisor

- **GIVEN** vendedor con `supervisor_venta='No'`
- **WHEN** abre pedido simple
- **THEN** MUST NOT mostrar selector de vendedor

---

### REQ-VOP-04 — Banner operativo persistente

Cuando `cod_viajante_operativo` difiere de `id_vendedor_usr` del usuario logueado, la UI MUST mostrar banner persistente «Operando como: {nombre vendedor}» en pedido simple y masivo.

#### Scenario: Supervisor operando por otro

- **GIVEN** supervisor logueado como Juan (`id_vendedor_usr=10`) operando como Pedro (`cod_viajante_operativo=21`)
- **WHEN** navega pedido simple o masivo
- **THEN** MUST ver banner «Operando como: Pedro» visible durante toda la sesión de captura

---

### REQ-VOP-05 — Limpieza al logout o cambio de vendedor

El sistema MUST restablecer `cod_viajante_operativo` a `id_vendedor_usr` al cerrar sesión mayoristapp. Al cambiar vendedor en el selector, MUST invalidar carrito/borrador activo del contexto anterior o advertir al usuario antes de continuar.

#### Scenario: Logout limpia operativo

- **GIVEN** supervisor operando como vendedor `21`
- **WHEN** cierra sesión mayoristapp
- **THEN** en el próximo login `cod_viajante_operativo` MUST ser su `id_vendedor_usr`

---

### REQ-VOP-06 — Resolución única de viajante efectivo

El sistema MUST centralizar la resolución del viajante efectivo en un helper único consumido por checkout, pedido masivo, relay de clientes y catálogo. MUST leer `cod_viajante_operativo` con fallback a `id_vendedor_usr`. MUST NOT duplicar lógica en vistas sueltas.

#### Scenario: Checkout usa operativo

- **GIVEN** `cod_viajante_operativo=21`
- **WHEN** se confirma un PED
- **THEN** `comp_ped.CodViajante` MUST ser `21`
