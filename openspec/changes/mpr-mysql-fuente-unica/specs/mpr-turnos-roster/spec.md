# Delta for mpr-turnos-roster

## MODIFIED Requirements

### Requirement: Modelo MprTurno — Turnos Globales por Empresa

El sistema MUST persistir turnos en MySQL **`mpr_turno`**: `id_mpr_turno` PK AI, `nombre` UNIQUE, `hora_inicio`, `hora_fin`, `activo`, `creado_en`. MUST NOT existir columna `base_empresa`. Acceso vía repositorio con `get_connection(base_empresa)`.

(Previously: modelo Django Postgres `MprTurno` con UniqueConstraint `(base_empresa, nombre)`.)

#### Scenario: Crear turno estándar

- DADO conexión a BD empresa
- CUANDO se crea turno "Mañana" 06:00–14:00
- ENTONCES MUST persistir en `mpr_turno` con `activo=1`

#### Scenario: Rechazar nombre duplicado

- DADO turno "Mañana" existente en la BD
- CUANDO se intenta otro "Mañana"
- ENTONCES MUST rechazarse por UNIQUE en `nombre`

---

### Requirement: Modelo MprRosterDia — Planificación Diaria

El sistema MUST persistir roster en MySQL **`mpr_roster_dia`**: `id_mpr_roster_dia` PK AI, `fecha`, `id_operario`, FK `id_mpr_turno` RESTRICT, UNIQUE `(fecha, id_operario)`, índice `(fecha)`. MUST NOT existir `base_empresa`.

(Previously: modelo Django Postgres con UniqueConstraint `(base_empresa, fecha, id_operario)`.)

#### Scenario: Asignar turno a operario en fecha

- DADO operario 123 y turno id_mpr_turno=1
- CUANDO se asigna fecha 15/07/2026
- ENTONCES MUST crearse fila en `mpr_roster_dia`

#### Scenario: Reasignar turno

- DADO asignación existente operario 123 fecha 15/07/2026
- CUANDO se cambia a otro `id_mpr_turno`
- ENTONCES MUST actualizarse la misma fila sin duplicar

---

### Requirement: Scoping por base_empresa y Autenticación

Scoping MUST lograrse conectando a la BD MySQL de la sesión. MUST NOT filtrar por columna `base_empresa` en SQL. Views MUST usar `MprLoginRequiredMixin`.

(Previously: filtro ORM `base_empresa=request...`.)

#### Scenario: Usuario solo ve turnos de su BD

- DADO turnos en BD A y BD B distintas
- CUANDO usuario con sesión BD A lista turnos
- ENTONCES MUST ver solo turnos de BD A
