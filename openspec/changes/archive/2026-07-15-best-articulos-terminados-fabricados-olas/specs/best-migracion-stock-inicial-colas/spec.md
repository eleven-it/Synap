# Spec — Colas stock inicial por olas (migración BEST)

**Capability:** `best-migracion-stock-inicial-colas`  
**Change:** `best-articulos-terminados-fabricados-olas`  
**Estado:** Propuesto

---

## Purpose

Visualizar y operar el stock inicial de migración BEST→MPR en **olas anti-duplicado**, con colas explícitas por estado y copy que prioriza **Artículos terminados** en el cutover. El backend de olas (sync previo, delta live, preservación de `CARGADO`) ya existe; esta spec define el contrato de UI y mensajes.

---

## ADDED Requirements

### Requirement: Tres colas de visualización en stock inicial

La pantalla de stock inicial (`/mpr/migracion-best/stock-inicial/`) MUST exponer tres colas o pestañas distinguibles:

| Cola | Estados incluidos | Propósito |
|------|-------------------|-----------|
| Pendiente de mapeo | `SIN_MAPEO_ARTICULO`, `SIN_MAPEO_DEPOSITO` | Maestros faltantes antes de cargar |
| Listos para carga | `LISTO`, `CONCILIADO` | Ola actual — candidatas a confirmar carga |
| Ya cargados | `CARGADO` | Olas previas — solo consulta |

Cada cola MUST mostrar contadores coherentes con las métricas de `cargar_stock_inicial_best`.

#### Scenario: Usuario filtra pendientes de mapeo

- **GIVEN** existen líneas en `SIN_MAPEO_ARTICULO` y otras en `LISTO`
- **WHEN** el usuario abre la cola «Pendiente de mapeo»
- **THEN** solo ve líneas con estado `SIN_MAPEO_*`
- **AND** no ve líneas `LISTO`, `CONCILIADO` ni `CARGADO`

#### Scenario: Usuario identifica ola actual

- **GIVEN** hay 30 líneas `LISTO`/`CONCILIADO` y 70 `CARGADO`
- **WHEN** el usuario abre «Listos para carga»
- **THEN** ve exactamente las 30 candidatas
- **AND** la cola «Ya cargados» muestra las 70 sin opción de reprocesar

---

### Requirement: Confirmación de carga solo sobre pendientes

Al confirmar carga, el sistema MUST procesar únicamente líneas en `LISTO` o `CONCILIADO`. Las líneas `CARGADO` MUST NOT re-sincronizarse, re-moverse ni cambiar de estado en olas sucesivas.

#### Scenario: Ola posterior no toca cargados

- **GIVEN** una línea ya está en `CARGADO` de una ola previa
- **WHEN** el usuario confirma una nueva carga de stock inicial
- **THEN** esa línea permanece `CARGADO` sin delta aplicado
- **AND** el mensaje de resultado indica cuántas líneas `CARGADO` se preservaron

#### Scenario: Solo listos entran en la ola

- **GIVEN** hay líneas `LISTO`, `CONCILIADO` y `SIN_MAPEO_ARTICULO`
- **WHEN** el usuario confirma carga
- **THEN** solo `LISTO`/`CONCILIADO` elegibles son procesadas
- **AND** las `SIN_MAPEO_*` quedan sin cambio

---

### Requirement: Copy de prioridad cutover — Terminados

La UI MUST comunicar que el stock inicial **crítico al cutover** corresponde a artículos **Terminados** (depósito Terminado BEST ↔ Terminado Admin). El stock de fabricados / Semi-Embalado MUST NOT presentarse como requisito del camino crítico.

#### Scenario: Banner o texto orientador visible

- **GIVEN** el usuario abre stock inicial durante preparación de cutover
- **WHEN** visualiza la pantalla
- **THEN** ve copy explícito de que Terminados es prioritario en ola 1
- **AND** fabricados/Semi-elaborado se describe como opcional post-cutover

---

### Requirement: Métricas de ola visibles

La pantalla MUST mostrar métricas de la última operación de ola (sync previo, delta live, preservados, procesados) reutilizando los datos expuestos por el servicio de carga, sin duplicar lógica de negocio en la vista.

#### Scenario: Resultado post-confirmación

- **GIVEN** el usuario acaba de confirmar una carga
- **WHEN** la página se recarga o muestra feedback
- **THEN** ve contadores de líneas procesadas, preservadas (`CARGADO`) y delta aplicado
- **AND** las colas reflejan el nuevo reparto de estados
