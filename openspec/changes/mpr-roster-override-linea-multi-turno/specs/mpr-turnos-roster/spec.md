# Delta — mpr-turnos-roster

**Change:** `mpr-roster-override-linea-multi-turno`  
**Fuente de diseño:** `docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md`

---

## MODIFIED Requirements

### Requirement: Modelo MprRosterDia — Planificación Diaria

El sistema MUST persistir roster en MySQL **`mpr_roster_dia`** con campos `fecha`, `id_operario`, FK `id_mpr_turno`, `id_mpr_linea` (NULL = habitual), `creado_en`.

El sistema MUST garantizar **unicidad por turno**:

- **Constraint único:** `(fecha, id_operario, id_mpr_turno)` → índice `uk_mpr_roster_fecha_operario_turno`.
- **MUST NOT** mantener la UK `(fecha, id_operario)` como restricción activa tras la migración.

Un operario MUST poder tener **varios turnos el mismo día** (filas distintas por `id_mpr_turno`).

Al agregar un segundo turno MUST usarse **INSERT** de fila nueva; MUST NOT actualizar la fila del primer turno.

(Previously: UniqueConstraint `(fecha, id_operario)` — un solo turno por operario y fecha; segundo turno rechazado o pisa al primero vía upsert.)

#### Scenario: Asignar primer turno a operario en fecha

- **GIVEN** operario 123 sin roster el 15/07/2026
- **WHEN** se asigna turno Mañana (`id_mpr_turno=1`)
- **THEN** MUST crearse una fila en `mpr_roster_dia` con `(fecha=2026-07-15, id_operario=123, id_mpr_turno=1)`

#### Scenario: Agregar segundo turno el mismo día

- **GIVEN** operario 123 con turno Mañana el 15/07/2026
- **WHEN** se asigna turno Tarde (`id_mpr_turno=2`) el mismo día
- **THEN** MUST crearse una **segunda** fila con `id_mpr_turno=2`
- **AND** MUST persistir la fila de Mañana sin modificación

#### Scenario: Rechazar turno duplicado mismo operario/fecha/turno

- **GIVEN** operario 123 con turno Mañana el 15/07/2026
- **WHEN** se intenta insertar otra fila Mañana el mismo día sin actualizar la existente
- **THEN** MUST rechazarse por violación de `uk_mpr_roster_fecha_operario_turno`

#### Scenario: Reasignar turno T → T' en fila existente

- **GIVEN** operario 123 con turno Mañana el 15/07/2026 sin ledger bloqueante
- **WHEN** se reasigna a Tarde en esa fila
- **THEN** MUST actualizarse `id_mpr_turno` de esa fila
- **AND** MUST NOT crear fila duplicada

---

### Requirement: Override de línea por día en el roster

La columna `id_mpr_linea` en `mpr_roster_dia` MUST permitir **sobrescribir** la línea habitual del operario para la combinación **`(fecha, id_operario, id_mpr_turno)`**. `NULL` significa usar la línea habitual vigente a esa fecha.

La resolución de línea (`resolver_linea_operario`) MUST consultar override filtrando por **`id_turno`** cuando se provee.

La UI de planificación MUST permitir setear override en **fechas pasadas** si no hay ledger bloqueante de **ese turno**.

El override MUST NOT alterar la línea efectiva de **otro turno** del mismo operario el mismo día.

(Previously: override conceptual por día; lookup con `LIMIT 1` sin `id_turno`; sin UI de override en planificación.)

#### Scenario: Override de línea por turno

- **GIVEN** operario con línea habitual Línea 1
- **AND** roster Mañana y Tarde el mismo día
- **WHEN** se setea override Línea 3 solo en Mañana
- **THEN** `resolver_linea_operario(..., id_turno=Mañana)` MUST devolver Línea 3
- **AND** `resolver_linea_operario(..., id_turno=Tarde)` MUST devolver Línea 1 (habitual)

#### Scenario: Override en fecha pasada sin parte

- **GIVEN** fecha pasada sin parte ni CC del operario en turno Mañana
- **WHEN** el supervisor setea override Línea 2 vía UI
- **THEN** MUST persistirse `id_mpr_linea` en la fila `(fecha, operario, Mañana)`

#### Scenario: Sin override usa habitual

- **WHEN** la fila roster tiene `id_mpr_linea=NULL`
- **THEN** la resolución MUST usar `mpr_operario_linea` vigente a esa fecha

#### Scenario: Compatibilidad filas pre-migración

- **GIVEN** filas roster con un turno/día e `id_mpr_linea` NULL o seteado
- **WHEN** se aplica migración UK multi-turno
- **THEN** MUST interpretarse igual que antes para ese único turno
- **AND** MUST NOT perderse valores de `id_mpr_linea` existentes

---

### Requirement: Pantalla de Planificación (Roster) — Grilla Semanal

La grilla semanal MUST mostrar por celda operario×día **0..N turnos asignados** (p. ej. chips Mañana / Tarde / Noche).

Por cada turno asignado la UI MUST ofrecer:

- **Override de línea:** selector `Habitual` | líneas activas (solo ese `fecha+operario+turno`).
- **Quitar turno:** con confirmación modal Synap; mismos bloqueos que hoy por `(fecha, operario, turno)`.

La celda MUST ofrecer acción **Agregar turno** para elegir un turno aún no asignado ese día.

Cada turno MUST mostrar línea **efectiva** (override o habitual) además del valor override explícito.

(Previously: un selector de turno único por celda; sin selector de línea; sin agregar segundo turno.)

#### Scenario: Celda con dos turnos visibles

- **GIVEN** operario con Mañana y Tarde el lunes
- **WHEN** se carga la grilla de esa semana
- **THEN** la celda MUST mostrar dos chips/entradas distintas (Mañana, Tarde)

#### Scenario: Override desde planificación

- **GIVEN** celda editable (sin candado) con turno Mañana
- **WHEN** el usuario elige Línea 2 en el selector de línea de Mañana
- **THEN** MUST persistirse override solo para Mañana
- **AND** MUST mostrarse feedback en español vía toast/modal Synap

#### Scenario: Agregar turno disponible

- **GIVEN** operario con solo Mañana un día
- **WHEN** el usuario usa "Agregar turno" y elige Tarde
- **THEN** MUST aparecer chip Tarde tras recargar
- **AND** Mañana MUST permanecer intacto

---

### Requirement: Guardrail y migración de roster con ledger no físico (operario+fecha+turno)

Los bloqueos MUST evaluarse por **`(fecha, id_operario, id_mpr_turno)`**, no por operario+día completo.

Si un turno T tiene parte aprobado / movimiento físico / CC confirmado:

- MUST **bloquear** override de línea, quitar turno T y reasignar T → T' en T.
- MUST **permitir** agregar u operar **otro turno distinto** T2 el mismo día si T2 no tiene ledger bloqueante.

La asignación idempotente T → T (solo cambio de override de línea) MUST seguir permitida aunque exista parte/CC bloqueante de **otro** turno del mismo día (no aplica si el bloqueo es del mismo T).

(Previously: reglas ya por turno en servicio; UK y UI asumían un turno/celda; escenario multi-turno con un turno bloqueado no explícito.)

#### Scenario: Agregar segundo turno con primero bloqueado

- **GIVEN** operario con Mañana bloqueado por parte aprobado
- **WHEN** se agrega Tarde el mismo día
- **THEN** MUST crearse asignación Tarde
- **AND** celda Mañana MUST seguir con candado

#### Scenario: Override bloqueado con parte aprobado del turno

- **GIVEN** turno Mañana con parte aprobado para ese operario y fecha
- **WHEN** se intenta cambiar override de línea de Mañana
- **THEN** MUST rechazarse
- **AND** UI MUST mostrar candado en Mañana sin selector editable

#### Scenario: Override idempotente permitido con parte en otro turno

- **GIVEN** operario con Tarde bloqueado y Mañana editable
- **WHEN** se cambia solo override de línea en Mañana (M → M)
- **THEN** MUST permitirse sin error

---

### Requirement: Persistencia del override vía catálogo central

La migración de UK multi-turno MUST implementarse en `core/services/legacy_mysql_schema/catalog.py` (proveedor dedicado, p. ej. `mpr_roster_multi_turno`) con SQL de referencia en `mpr/sql/`.

El proveedor MUST ser **idempotente** y MUST NOT ejecutar DELETE/TRUNCATE/UPDATE masivo de datos de roster.

(Previously: columna `id_mpr_linea` vía `mpr_maquina_linea_trazabilidad`; UK sigue `(fecha, id_operario)`.)

#### Scenario: Idempotencia DDL UK

- **WHEN** se ejecuta dos veces el proveedor de UK multi-turno
- **THEN** MUST NOT fallar
- **AND** MUST existir solo `uk_mpr_roster_fecha_operario_turno`

#### Scenario: Migración preserva conteos

- **GIVEN** N filas en `mpr_roster_dia` y M overrides (`id_mpr_linea IS NOT NULL`) antes del DDL
- **WHEN** se aplica el proveedor
- **THEN** MUST mantenerse N filas y M overrides

---

## ADDED Requirements

### Requirement: Servicio set_linea_override_roster

El sistema MUST exponer `set_linea_override_roster(base_empresa, fecha, id_operario, id_mpr_turno, id_mpr_linea=None)` que:

- Valida bloqueo por `(fecha, operario, turno)`.
- Actualiza **solo** `id_mpr_linea` de la fila existente `(fecha, operario, turno)`.
- Acepta `id_mpr_linea=None` para volver a habitual (NULL en BD).
- MUST NOT modificar `id_mpr_turno` ni otras filas del mismo operario/día.

#### Scenario: Set override en fila existente

- **GIVEN** roster Mañana sin override
- **WHEN** se invoca `set_linea_override_roster(..., id_mpr_turno=Mañana, id_mpr_linea=3)`
- **THEN** MUST quedar `id_mpr_linea=3` solo en fila Mañana

#### Scenario: Clear override a habitual

- **GIVEN** override Línea 3 en Mañana
- **WHEN** se invoca con `id_mpr_linea=None`
- **THEN** MUST quedar `id_mpr_linea=NULL` en esa fila

---

### Requirement: Upsert de roster que preserva override

Al cambiar **solo turno** en flujos que aún usen upsert/reasignación, el sistema MUST NOT sobrescribir `id_mpr_linea` existente con NULL implícito. Updates parciales MUST usar semántica `COALESCE` o campos explícitos.

Al insertar **nuevo** turno el mismo día, MUST NOT alterar `id_mpr_linea` de filas hermanas.

#### Scenario: Reasignar turno conserva override

- **GIVEN** fila Mañana con `id_mpr_linea=5`
- **WHEN** se reasigna Mañana → Tarde (permitido por guardrails)
- **THEN** la fila resultante MUST conservar `id_mpr_linea=5` salvo cambio explícito de override

#### Scenario: Upsert nuevo turno no borra override del otro

- **GIVEN** Mañana con override Línea 2
- **WHEN** se inserta Tarde el mismo día
- **THEN** Mañana MUST seguir con `id_mpr_linea=2`

---

### Requirement: Lecturas multi-turno del roster

El sistema MUST reemplazar lecturas de un solo turno por día:

- `turnos_del_operario_dia(base, id_operario, fecha)` → lista de `{id_mpr_turno, id_mpr_linea, ...}`.
- `listar_roster_semana` MUST agrupar **N turnos** por `(operario, fecha)` con línea efectiva y flags de bloqueo por turno.

Consumidores (planilla QC, parte analista, trazabilidad) MUST usar `resolver_linea_operario` con `id_turno`.

#### Scenario: turnos_del_operario_dia devuelve N turnos

- **GIVEN** operario con Mañana y Tarde un día
- **WHEN** se llama `turnos_del_operario_dia`
- **THEN** MUST devolver dos entradas con distintos `id_mpr_turno`

#### Scenario: listar_roster_semana multi-turno

- **GIVEN** roster semanal con dos turnos un día para operario X
- **WHEN** se construye payload de planificación
- **THEN** MUST incluir ambos turnos bajo `(X, fecha)` con línea efectiva por turno

---

### Requirement: Carga móvil multi-turno

La PWA `/mpr/mi-parte/` MUST permitir al operario cargar parte en **todos los turnos** asignados el día actual (o fecha operativa), resolviendo línea por `id_turno` en cada uno.

#### Scenario: Operario con dos turnos hoy

- **GIVEN** operario con Mañana y Tarde hoy
- **WHEN** abre `/mpr/mi-parte/`
- **THEN** MUST poder cargar (o navegar) producción por cada turno
- **AND** línea resuelta MUST ser independiente por turno

#### Scenario: Un turno bloqueado no impide el otro

- **GIVEN** Mañana con parte aprobado y Tarde editable hoy
- **WHEN** el operario accede al móvil
- **THEN** Tarde MUST permanecer editable según reglas del móvil
- **AND** Mañana MUST mostrarse acorde a estado bloqueado

---

### Requirement: Deploy seguro sin pérdida de datos de roster

Antes y después del DDL MUST verificarse (manual o script):

- `COUNT(*)` total en `mpr_roster_dia`.
- `COUNT(*)` con `id_mpr_linea IS NOT NULL`.
- `SHOW INDEX` confirma UK nueva y ausencia de UK vieja.

El release MUST desplegar DDL **antes o junto** con código que inserta multi-turno; MUST NOT activar UI multi-turno contra UK `(fecha, id_operario)`.

Ningún paso de migración MUST modificar `mpr_parte*`, stock ni MSTOCK.

#### Scenario: Conteos iguales post-DDL

- **WHEN** se aplica migración UK en Staging
- **THEN** conteos pre/post MUST ser idénticos
- **AND** MUST NOT haber DELETE masivo en roster

#### Scenario: UI multi-turno rechazada sin UK nueva

- **GIVEN** BD con UK vieja `(fecha, id_operario)`
- **WHEN** se intenta agregar segundo turno vía UI nueva
- **THEN** MUST fallar de forma controlada o estar deshabilitado hasta DDL aplicado

---

### Requirement: Alcance excluido del change

El change MUST NOT:

- Usar línea habitual retroactiva como corrección diaria normal.
- Migrar automáticamente líneas de `mpr_parte_linea` al cambiar override.
- Permitir override después de parte aprobado / movimiento físico / CC del **mismo turno**.

#### Scenario: Habitual sigue desde hoy

- **WHEN** se cambia línea habitual en `/mpr/operarios-lineas/`
- **THEN** MUST NOT aplicarse retroactivamente a días pasados del roster

#### Scenario: Parte no se reescribe al override

- **GIVEN** parte borrador con líneas en turno Mañana
- **WHEN** se cambia override de línea en Mañana
- **THEN** MUST NOT migrar automáticamente líneas del parte
- **AND** UI MAY advertir que cantidades no se mueven

---

## Fuera de Alcance (delta)

Sin cambio respecto al spec base para: plantillas rotación automática, historial auditoría roster, validación solape horario turnos.

Este delta **cierra** multi-turno mismo día y override UI como fuera de alcance en iteraciones anteriores.
