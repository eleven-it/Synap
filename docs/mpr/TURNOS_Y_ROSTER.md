# Turnos y Roster (MPR Etapa 3)

**Capability:** `mpr-turnos-roster`
**Fecha:** 2026-07-02
**Estado:** Implementado

> **Persistencia MySQL:** turnos y roster en `mpr_turno` y `mpr_roster_dia` (MySQL, una BD = una empresa).

---

## Propósito

Permite configurar **turnos de producción** (CRUD) por empresa y planificar la **asignación semanal de turnos a operarios** (roster rotativo). Es la base para que etapas posteriores (consumo OPP, etapa 4) puedan registrar producción trazada a un turno específico.

---

## Modelos Django (DB default — PostgreSQL)

### `MprTurno`

Turno de producción global por empresa.

| Campo | Tipo | Descripción |
|---|---|---|
| `base_empresa` | CharField(64, db_index) | Scope por empresa |
| `nombre` | CharField(100) | Nombre del turno |
| `hora_inicio` | TimeField | Hora de inicio (HH:MM) |
| `hora_fin` | TimeField | Hora de fin. Si < hora_inicio, cruza medianoche |
| `activo` | BooleanField (default True) | Toggle activo/inactivo |
| `creado_en` | DateTimeField (auto_now_add) | Auditoría |

**Constraints e índices:**
- `UniqueConstraint(base_empresa, nombre)` → nombre único por empresa.
- `Index(base_empresa, activo)` → consultas de turnos activos.
- ordering: `[base_empresa, nombre]`.

**Turnos nocturnos:** `hora_fin < hora_inicio` es válido (cruza medianoche). No se valida solapamiento entre turnos.

### `MprRosterDia`

Asignación de turno a un operario en una fecha específica.

| Campo | Tipo | Descripción |
|---|---|---|
| `base_empresa` | CharField(64, db_index) | Scope por empresa |
| `fecha` | DateField | Fecha de la asignación |
| `id_operario` | IntegerField | FK lógico a `sue_abm_empleado.id_sue_abm_empleado` |
| `turno` | ForeignKey(MprTurno, PROTECT) | Turno asignado |
| `creado_en` | DateTimeField (auto_now_add) | Auditoría |

**Constraints e índices:**
- `UniqueConstraint(base_empresa, fecha, id_operario)` → un operario solo tiene un turno por fecha.
- `Index(base_empresa, fecha)` → consultas de roster por empresa y semana.

**on_delete=PROTECT:** No se puede eliminar un turno si tiene asignaciones de roster. Primero reasignar o eliminar asignaciones.

---

## Override de línea por día {#override-de-línea-por-día}

**Change:** `mpr-trazabilidad-maquina-linea-operario`.

El roster permite fijar, para un día puntual (rotación, refuerzo), una **línea distinta** a la
habitual del operario. Se implementa con una columna nueva en `mpr_roster_dia` (MySQL):

| Columna | Tipo | Descripción |
|---|---|---|
| `id_mpr_linea` | `BIGINT` NULL | Override de línea del día; **NULL = usar la línea habitual** |

La línea habitual del operario vive versionada en `mpr_operario_linea`
(`vigencia_desde`/`vigencia_hasta`, NULL = vigente).

**Resolución override > habitual** (`resolver_linea_operario`):

```
resolver_linea_operario(id_operario, fecha, id_turno):
    override = mpr_roster_dia(fecha, id_operario).id_mpr_linea
    return override or mpr_operario_linea.vigente(id_operario, fecha).id_mpr_linea
```

- Si el roster del día trae `id_mpr_linea`, **manda** (override).
- Si es NULL, se usa la **línea habitual** vigente a esa fecha.

Con la línea resuelta, la carga móvil del operario lista las máquinas vigentes de esa línea y
sus artículos habilitados. Detalle del circuito:
[TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md#línea-habitual--override-de-roster).

> DDL aplicado por el proveedor `mpr_maquina_linea_trazabilidad`
> (`core/services/legacy_mysql_schema/catalog.py`), idempotente. Ver
> [../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md](../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md).

---

## Servicios (`mpr/services.py`)

### Helpers de fecha

```python
_parse_fecha_ddmmaaaa(fecha_str: str) -> Tuple[Optional[date], Optional[str]]
# Parsea "dd/MM/yyyy" → (date_obj, None) o (None, error)

_fmt_fecha_ddmmaaaa(fecha) -> str
# date/datetime → "dd/MM/yyyy" para UI
```

### CRUD Turnos

```python
listar_turnos(base_empresa, solo_activos=True) -> List[dict]
# Retorna [{id, nombre, hora_inicio, hora_fin, activo}]

obtener_turno(base_empresa, id_turno) -> Optional[MprTurno]
# Retorna instancia o None

crear_turno(base_empresa, nombre, hora_inicio, hora_fin) -> Tuple[bool, Optional[int], Optional[str]]
# (ok, id_turno, error) — valida hora_inicio != hora_fin

actualizar_turno(base_empresa, id_turno, nombre, hora_inicio, hora_fin) -> Tuple[bool, Optional[str]]
# (ok, error)

toggle_turno_activo(base_empresa, id_turno, activo: bool) -> Tuple[bool, Optional[str]]
# (ok, error)
```

### Servicios Roster

```python
listar_roster_semana(base_empresa, fecha_lunes: date) -> dict
# Retorna:
#   {
#     operarios: [{id, nombre}],
#     dias: [{fecha, fecha_str (dd/MM/yyyy), dia_nombre}],  # 7 días
#     asignaciones: {id_operario: {"YYYY-MM-DD": {id_turno, nombre_turno}}},
#     celdas_bloqueadas: {id_operario: {"YYYY-MM-DD": {bloqueada, motivo}}}
#   }

asignar_turno_roster(base_empresa, fecha_str, id_operario, id_turno) -> Tuple[bool, Optional[str]]
# Usa update_or_create (reasignación segura, no duplica). Al cambiar turno migra
# el ledger borrador/pendiente; bloquea parte aprobada/física o CC confirmado.

eliminar_asignacion_roster(base_empresa, fecha_str, id_operario) -> Tuple[bool, Optional[str]]
# Bloquea parte aprobada/física o CC. Si solo hay borrador/pendiente, exige
# reasignar hacia otro turno para conservar los datos.
```

### Asignación masiva (rango)

**Fecha de implementación:** 17/07/2026

```python
asignar_turno_roster_rango(
    base_empresa,
    ids_operario: List[Any],
    id_turno: int,
    fecha_desde: Any,
    fecha_hasta: Any,
    id_linea: Optional[int] = None,
) -> Tuple[bool, Optional[str], Dict[str, Any]]
```

- **URL:** `planificacion-turnos/asignar-masivo/` (`roster_asignar_masivo`), vista `AsignarTurnoRosterMasivoView` (POST).
- **Campos del formulario:** `ids_operario` (lista), `id_turno`, `fecha_desde`, `fecha_hasta` (ISO `YYYY-MM-DD` desde inputs HTML), `semana` (redirect).
- **Reglas:** valida empresa, operarios y turno; recorre el rango con `_iter_dias_rango`; **omite celdas con parte aprobada/física o CC confirmado** (`omitidos_bloqueados`); al reasignar celdas con borrador/pendiente migra sus líneas antes del `upsert_roster`. Retorna resumen `{aplicados, omitidos_pasados (siempre 0), omitidos_bloqueados, errores}`; éxito parcial si `aplicados > 0`.
- **Helper UI:** `mensaje_flash_asignacion_masiva(resumen)` construye el mensaje de éxito en español.

---

## Vistas y URLs (`mpr/`)

| URL | Nombre | Vista | Método |
|---|---|---|---|
| `turnos/` | `turnos_list` | TurnosListView | GET (lista) / POST (toggle) |
| `turnos/nuevo/` | `turno_create` | TurnoCreateView | GET / POST |
| `turnos/<id>/editar/` | `turno_edit` | TurnoUpdateView | GET / POST |
| `planificacion-turnos/` | `planificacion_turnos` | PlanificacionTurnosView | GET |
| `planificacion-turnos/asignar/` | `roster_asignar` | AsignarTurnoRosterView | POST |
| `planificacion-turnos/asignar-masivo/` | `roster_asignar_masivo` | AsignarTurnoRosterMasivoView | POST |
| `planificacion-turnos/eliminar/` | `roster_eliminar` | EliminarAsignacionRosterView | POST |

Todas las vistas usan `MprLoginRequiredMixin`. La `base_empresa` se obtiene de la sesión con `_get_base_empresa(request)`.

---

## Patrones UI

### Toggle Activo/Inactivo (turnos_list.html)

Sigue el mismo patrón que `operarios_list.html`:
- `<form hidden>` con `{% csrf_token %}` + `<input hidden name="activo" value="True|False">`.
- `<input type="checkbox" role="switch" class="peer sr-only turno-estado-switch" data-id="{{ turno.id }}">`.
- JS: `addEventListener('change', form.submit)`.
- Toggle verde (activo) / rojo (inactivo), clases Tailwind peer.

### Grilla Semanal (planificacion_turnos.html)

> **UI:** la pantalla usa el **chrome denso MPR** (barra `slate-800`, sin migas de pan) descrito en
> [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md) §3.1: navegación de semana,
> **Asignación masiva**, **Gestionar turnos**, atajos `chrome_nav_flujo` (`current=roster`) y ayuda al manual.
> El chrome permanece en el flujo del contenedor: la grilla es el único scrollport, evitando que la barra
> cubra su cabecera o sus primeras filas.

- Tabla con sticky-left en columna Operario; `thead` compacto (`text-[10px]`) con fondo opaco.
- 7 columnas de días (lunes a domingo).
- Celdas **bloqueadas** (parte aprobada/con movimiento físico o CC confirmado en operario+fecha+turno asignado): badge + ícono candado + `title` con motivo; sin select ni quitar.
- Celdas con solo **borrador/pendiente** permanecen editables: una reasignación migra su ledger no físico al turno destino; quitar el turno se rechaza para no perder la relación con el turno.
- Celdas **editables** (sin bloqueo duro): badge + botón "Quitar" si hay asignación; `<select>` + confirmar si está vacía. Aplica a pasado, hoy y futuro por igual.
- Columna **hoy** resaltada en púrpura (solo visual; no define editabilidad).
- `<select>` con JS `onchange` dispara el form automáticamente.
- Fechas en cabecera: `"Lu dd/MM/yyyy"`.
- **Quitar turno** abre un **modal Synap** de confirmación (Alpine `confirmOpen`); no se usan
  `confirm()` / `alert()` nativos (ver `.cursor/rules/modales-sin-dialogos-nativos.mdc`).

#### Color por turno (diferenciación visual) {#color-por-turno}

Los badges de turno asignado (hoy/futuro) se **colorean por turno** para mejor UX
(antes todos eran verdes). El color se resuelve con el filtro `turno_color` y clases
CSS scoped en `planificacion_turnos.html` (`.mpr-turno-badge--<slug>`), sin campo nuevo
en `MprTurno` ni migración de DB. Dark mode vía clase `.dark` (igual que el resto de la UI).

Paleta (canon Synap slate/sky, índigo semántico para noche):

| Turno (heurística por nombre) | Slug | Color claro |
|---|---|---|
| Mañana | `manana` | cielo (sky) |
| Tarde | `tarde` | ámbar |
| Noche / Nocturno | `noche` | índigo suave |
| Otros (rota por `id % 4`) | `p0..p3` | teal / slate / cyan / rose |

El link «Quitar» permanece en rojo/rose (acción destructiva) y no compite con el badge.

### Template filters (mpr_filters.py)

```python
{{ valor|dict_get:clave }}   # acceso a dict con clave dinámica
{{ fecha|isoformat }}        # date → "YYYY-MM-DD" para query params
{{ fecha|fecha_dd_mm_yyyy }} # ya existía: date → "dd-MM-yyyy"
{{ asig|turno_color }}       # slug de color por turno: manana/tarde/noche/p0..p3
```

---

## Validaciones

| Regla | Donde |
|---|---|
| `hora_inicio != hora_fin` | Service `crear_turno` / `actualizar_turno` |
| Nombre único por empresa | DB `UniqueConstraint` + captura `IntegrityError` en service |
| Bloqueo duro por parte aprobada/física o CC confirmado | Repos `operario_estado_produccion_roster`, `set_operarios_bloqueados_roster_en_rango`, `operario_tiene_control_calidad_fecha_turno`; services de roster |
| Migración T→T' de borrador/pendiente | `migrar_lineas_operario_entre_turnos`: transacción MySQL que mueve/combina líneas, ajustes no físicos y borrador CC; no toca `mpr_transicion_lote`, MSTOCK ni stock físico |
| Unicidad (empresa, fecha, operario) | DB `UniqueConstraint` + `update_or_create` en service |
| Turno no eliminable con asignaciones | DB `on_delete=PROTECT` |
| Misma asignación T→T permitida con parte/CC | Service `_motivo_bloqueo_cambio_roster` (idempotente) |

---

## Tipos AdministraNET en operarios

Los helpers `listar_empleados_operarios` y `obtener_operario` (ya implementados) usan `to_int_or_none` y `str_or_default` de `core.utils.administranet_types` para normalizar datos de `sue_abm_empleado`.

---

## Migración

- Archivo: `mpr/migrations/0010_mprrosterdia_mprturno_and_more.py`
- Comando aplicar: `docker exec -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 Synap_app python manage.py migrate --noinput`
- Rollback: `docker exec -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 Synap_app python manage.py migrate mpr 0009_armado_unificado_lote_imputacion`

---

## Tests

Archivo: `mpr/tests/test_turnos_roster.py`

| Clase | Test | Cubre |
|---|---|---|
| TestModeloMprTurno | test_turno_nombre_unico_por_empresa | Constraint unicidad |
| TestModeloMprTurno | test_turno_nombre_unico_permite_mismo_nombre_otra_empresa | Scope por empresa |
| TestModeloMprTurno | test_turno_nocturno_valido | Turno nocturno hora_fin < hora_inicio |
| TestModeloMprTurno | test_str_turno | __str__ |
| TestModeloMprRosterDia | test_roster_constraint_unico_operario_fecha | Constraint unicidad roster |
| TestModeloMprRosterDia | test_roster_on_delete_protect | PROTECT delete turno con asignaciones |
| TestServiciosTurnos | test_crear_turno_valido | Crear turno OK |
| TestServiciosTurnos | test_crear_turno_hora_inicio_igual_fin | Validación horas |
| TestServiciosTurnos | test_crear_turno_nombre_duplicado | Nombre duplicado |
| TestServiciosTurnos | test_crear_turno_nocturno_valido | Turno nocturno via service |
| TestServiciosTurnos | test_actualizar_turno | Actualización |
| TestServiciosTurnos | test_toggle_turno_activo | Toggle activo/inactivo |
| TestServiciosTurnos | test_listar_turnos_solo_activos | Filtro solo_activos |
| TestServiciosRoster | test_asignar_turno_fecha_pasada_ok_sin_produccion | Pasado editable sin parte/CC |
| TestServiciosRoster | test_eliminar_asignacion_fecha_pasada_ok_sin_produccion | Eliminar pasado sin parte/CC |
| TestServiciosRoster | test_asignar_turno_bloqueado_por_parte | Bloqueo por parte |
| TestServiciosRoster | test_asignar_turno_bloqueado_por_cc | Bloqueo por CC |
| TestServiciosRoster | test_eliminar_asignacion_bloqueada_por_parte | Eliminar bloqueado |
| TestServiciosRoster | test_reasignar_bloqueado_turno_destino_con_cc | Reasignar bloqueado en T' |
| TestServiciosRoster | test_asignar_mismo_turno_idempotente_con_parte | T→T permitido con parte |
| TestServiciosRoster | test_asignar_turno_reasignacion_no_duplica | update_or_create |
| TestServiciosRoster | test_asignar_turno_fecha_futura_ok | Asignar OK |
| TestServiciosRoster | test_eliminar_asignacion_existente | Eliminar OK |
| TestAsignarTurnoRosterRango | test_rango_incluye_ayer_aplica_tambien_pasado | Rango incluye fechas pasadas |
| TestAsignarTurnoRosterRango | test_rango_omite_celdas_bloqueadas | Omite celdas con parte/CC |
| TestAsignarTurnoRosterRango | test_rango_solo_bloqueos_retorna_mensaje | Mensaje si todo bloqueado |

Ejecutar: `docker exec Synap_app python manage.py test mpr.tests.test_turnos_roster --keepdb --noinput`

---

## Integración con Etapas Futuras

- **Etapa 4 (consumo OPP):** Cada OPP podrá registrar el `id_roster_dia` al que pertenece, trazando producción por turno.
- **Etapa 5 (transiciones lote):** Podrá usar el turno del roster para calcular tiempos de ciclo por turno.
- **Etapa 6 (traza OPT):** Vista de traza completa OPT → Turnos → Producción por operario.

---

## Ejemplo de Uso

```python
from mpr.services import crear_turno, asignar_turno_roster

# Crear turno Mañana
ok, id_turno, error = crear_turno("Empresa1", "Mañana", "06:00", "14:00")

# Crear turno Noche (cruza medianoche)
ok, id_turno_noche, _ = crear_turno("Empresa1", "Noche", "22:00", "06:00")

# Asignar turno Mañana al operario 123 para el 10/07/2026
ok, error = asignar_turno_roster("Empresa1", "10/07/2026", 123, id_turno)

# Reasignar a Noche (update, no duplica)
ok, error = asignar_turno_roster("Empresa1", "10/07/2026", 123, id_turno_noche)
```
