# Spec — Aprobación de parte por supervisor (gap + asiento a Producción)

**Capability:** `mpr-aprobacion-parte-supervisor`
**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Estado:** Propuesto

---

## ADDED Requirements

### Requirement: Bandeja de partes pendientes

El supervisor MUST disponer de una bandeja que liste los partes en estado `pendiente` (y opcionalmente `borrador`), filtrable por fecha, turno y línea, para su revisión.

#### Scenario: Ver pendientes

- **GIVEN** partes cargados por operarios en `pendiente`
- **WHEN** el supervisor abre la bandeja
- **THEN** ve los partes pendientes con su origen, operario, línea, fecha y turno

---

### Requirement: Revisión y corrección con registro de gap

Al revisar, el supervisor MUST poder ajustar la cantidad de cada línea. El sistema MUST guardar por línea: `cantidad_declarada` (operario), `cantidad_aprobada` (supervisor), `gap = cantidad_aprobada − cantidad_declarada` y un `motivo` cuando exista gap.

#### Scenario: Corregir una línea

- **GIVEN** una línea con `cantidad_declarada=41` pares
- **WHEN** el supervisor la corrige a `39` pares con motivo "recuento físico"
- **THEN** la línea guarda `cantidad_aprobada=39`, `gap=-2` y `motivo="recuento físico"`

#### Scenario: Sin corrección, gap cero

- **WHEN** el supervisor aprueba una línea sin cambiarla
- **THEN** `cantidad_aprobada = cantidad_declarada` y `gap=0`

#### Scenario: Gap requiere motivo

- **WHEN** el supervisor deja un `gap != 0` sin motivo
- **THEN** el sistema exige el motivo antes de aprobar

---

### Requirement: Aprobación del parte completo

La aprobación MUST realizarse sobre el **parte completo** (una acción), aunque la información se persista línea por línea. Al aprobar, el estado del parte MUST pasar a `aprobado` con auditoría (`id_usuario_supervisor`, `aprobado_en`).

#### Scenario: Aprobar

- **WHEN** el supervisor confirma la aprobación del parte
- **THEN** el parte queda `aprobado` con el supervisor y timestamp registrados

---

### Requirement: La aprobación mueve stock a "Producción"

Solo al aprobar, el sistema MUST ejecutar el asiento físico que ingresa la `cantidad_aprobada` de cada línea al depósito con `tipo_mpr='Produccion'` (reutilizando el asiento OPP existente), de forma idempotente (`movimiento_fisico_ok`).

#### Scenario: Stock sube al aprobar

- **GIVEN** un parte `pendiente` con `stock_deposito` de Producción sin cambios
- **WHEN** el supervisor lo aprueba
- **THEN** `stock_deposito` de Producción sube por la suma de `cantidad_aprobada`
- **AND** se registran los movimientos de stock correspondientes

#### Scenario: Idempotencia de aprobación

- **WHEN** se reintenta aprobar un parte ya aprobado (`movimiento_fisico_ok=true`)
- **THEN** el asiento no se re-ejecuta ni duplica stock

---

### Requirement: Control de cupo en la aprobación

El control de cupo/validación que hoy corre al guardar el parte MUST ejecutarse en la aprobación (sobre `cantidad_aprobada`). El supervisor MUST poder ver el cupo Fabricando de referencia por artículo.

#### Scenario: Aviso de exceso

- **GIVEN** una línea cuya `cantidad_aprobada` supera el cupo Fabricando
- **WHEN** el supervisor revisa
- **THEN** el sistema advierte el exceso para su decisión (según regla definida en diseño)

---

### Requirement: Parte directo del supervisor (coexistencia)

El parte directo del supervisor (flujo actual) MUST seguir disponible: puede crearse ya `aprobado` con `origen=directo_supervisor`, moviendo stock en el acto, para cubrir fallas de la carga móvil.

#### Scenario: Carga directa

- **WHEN** el supervisor registra un parte directo
- **THEN** el parte queda `aprobado`, `origen=directo_supervisor` y el stock sube inmediatamente (como hoy)
