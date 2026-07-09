# Spec — Parte móvil por operario

**Capability:** `mpr-parte-movil-operario`
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto

> Dominio Best Sox: `1 docena = 12 pares`. Captura en docenas/pares, persistencia en pares.

---

## ADDED Requirements

### Requirement: Asignación operario→línea (habitual + override)

El sistema MUST determinar la línea del operario para una fecha/turno combinando: (a) la **línea habitual** del operario (`mpr_operario_linea`) y (b) un **override** opcional por día/turno en el roster (`mpr_roster_dia.id_linea`). El override MUST prevalecer sobre la línea habitual.

#### Scenario: Sin override usa habitual

- **GIVEN** operario con línea habitual `Línea 1` y sin override para hoy
- **WHEN** abre la carga móvil
- **THEN** ve las máquinas de `Línea 1`

#### Scenario: Override por día

- **GIVEN** operario con línea habitual `Línea 1` y override a `Línea 3` para hoy/turno Noche
- **WHEN** abre la carga móvil en ese turno
- **THEN** ve las máquinas de `Línea 3`

---

### Requirement: Grilla de captura por máquina y artículo

La pantalla móvil MUST mostrar las máquinas de la línea del operario y, por cada máquina, sus artículos con habilitación **vigente**. Por cada par (máquina, artículo) MUST ofrecer captura en **docenas** y **pares sueltos**.

#### Scenario: Ver solo su línea/turno

- **WHEN** el operario abre la carga
- **THEN** ve únicamente las máquinas de su línea (según asignación) y los artículos habilitados de cada máquina

#### Scenario: Captura docenas + pares

- **WHEN** el operario ingresa `3 docenas` y `5 pares` para (M-001, A)
- **THEN** el sistema registra `41 pares` (3×12 + 5)

---

### Requirement: Carga libre sin tope de cupo

La carga del operario MUST ser libre (producción real): el sistema MUST NOT rechazar por exceder el cupo Fabricando ni el techo de envíos. El control de cupo se realiza en la aprobación del supervisor.

#### Scenario: Cargar más que lo enviado

- **GIVEN** un artículo con cupo Fabricando menor a lo producido
- **WHEN** el operario declara la producción real
- **THEN** el sistema la acepta sin bloquear

---

### Requirement: Estado del parte y no impacto de stock

Al guardar, el parte móvil MUST quedar en estado `pendiente` con `origen=movil_operario` y MUST NOT ejecutar el asiento físico ni mover stock del depósito "Producción". Cada línea guardada MUST registrar `cantidad_declarada` con el operario logueado y la máquina (`id_maquina` + snapshot de nombre).

#### Scenario: Guardar deja pendiente sin stock

- **WHEN** el operario guarda su parte
- **THEN** se crea `mpr_parte` con `estado=pendiente`, `origen=movil_operario`
- **AND** `stock_deposito` de "Producción" no cambia
- **AND** cada `mpr_parte_linea` guarda `id_maquina`, `cantidad_declarada` y el operario

#### Scenario: Reeditar borrador antes de enviar

- **GIVEN** un parte del operario en `borrador`
- **WHEN** el operario ajusta cantidades y lo envía
- **THEN** pasa a `pendiente` para revisión, sin mover stock

---

### Requirement: UI móvil canónica

La captura móvil MUST usar `get_template_for_device` con templates bajo `mpr/templates/mpr/mobile/`, simple (lista de máquinas → artículos → campos docenas/pares), sin mostrar el tablero de producción.

#### Scenario: Render móvil

- **WHEN** el operario abre la carga desde un dispositivo móvil
- **THEN** se renderiza la variante móvil simplificada

---

### Requirement: Contexto automático sin configuración

La pantalla MUST resolver automáticamente operario, línea, turno y fecha (hoy) sin que el operario los seleccione, y mostrarlos en un header de contexto. La fecha MAY editarse solo para carga diferida.

#### Scenario: Entrada sin selección

- **WHEN** el operario abre la carga
- **THEN** ve su línea, turno y fecha ya resueltos, y la grilla lista para cargar

---

### Requirement: Lista de máquinas con estado y total en vivo

La pantalla MUST listar las máquinas de la línea como elementos escaneables con un indicador de estado (sin cargar / cargada / sin producción) y un buscador o salto por identificador de máquina. MUST mostrar un total en vivo (docenas) y progreso (máquinas cargadas / total).

#### Scenario: Progreso y total

- **GIVEN** una línea de 25 máquinas
- **WHEN** el operario carga 6 máquinas
- **THEN** ve "6/25" y el total de docenas acumuladas actualizado

---

### Requirement: Autosave, confirmación y estado posterior

La captura SHOULD autosalvarse como borrador para tolerar cortes de conexión. Antes de enviar, el sistema MUST mostrar un resumen para confirmar. Tras enviar, el parte MUST mostrarse como "Pendiente de aprobación" y MUST permitir edición mientras siga `pendiente`.

#### Scenario: Confirmar y enviar

- **WHEN** el operario pulsa "Revisar y enviar"
- **THEN** ve un resumen (máquinas/artículos/total) y, al confirmar, el parte queda `pendiente`

#### Scenario: Editar antes de aprobación

- **GIVEN** un parte enviado en `pendiente`
- **WHEN** el operario lo reabre
- **THEN** puede editarlo y reenviarlo (sigue sin mover stock)

---

### Requirement: Estados de borde

La pantalla MUST manejar con mensajes claros: sin línea asignada, sin turno en el roster, máquina sin artículos habilitados vigentes, y parte del turno ya enviado (modo lectura con opción de editar).

#### Scenario: Sin línea asignada

- **WHEN** un operario sin línea (habitual ni override) abre la carga
- **THEN** ve un mensaje indicando que contacte al supervisor, no una pantalla vacía
