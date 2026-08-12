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
- `UniqueConstraint(base_empresa, fecha, id_operario, id_mpr_turno)` → un operario puede tener **varios turnos el mismo día** (Mañana + Tarde, etc.).
- `Index(base_empresa, fecha)` → consultas de roster por empresa y semana.

> **MySQL empresa (`mpr_roster_dia`):** la UK operativa es
> `uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)`, aplicada por el
> proveedor `mpr_roster_multi_turno` (`core/services/legacy_mysql_schema/catalog.py`).
> Ver checklist pre/post deploy en
> [DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md](DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md) §5.4.

**on_delete=PROTECT:** No se puede eliminar un turno si tiene asignaciones de roster. Primero reasignar o eliminar asignaciones.

---

## Override de línea por día y turno {#override-de-línea-por-día}

> **Implementado (12/08/2026):** UI de override + **multi-turno el mismo día**
> (UK `(fecha, id_operario, id_mpr_turno)`) — change openspec
> `mpr-roster-override-linea-multi-turno`.
> Diseño y checklist deploy:
> [DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md](DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md).

**Change:** `mpr-trazabilidad-maquina-linea-operario` + `mpr-roster-override-linea-multi-turno`.

El roster permite fijar, para un día puntual (rotación, refuerzo), una **línea distinta** a la
habitual del operario. Se implementa con una columna nueva en `mpr_roster_dia` (MySQL):

| Columna | Tipo | Descripción |
|---|---|---|
| `id_mpr_linea` | `BIGINT` NULL | Override de línea del día; **NULL = usar la línea habitual** |

La línea habitual del operario vive versionada en `mpr_operario_linea`
(`vigencia_desde`/`vigencia_hasta`, NULL = vigente).

**Resolución override > habitual** (`resolver_linea_operario` en `mpr/services_operario.py`):

```
resolver_linea_operario(id_operario, fecha, id_turno):
    override = mpr_roster_dia(fecha, id_operario, id_turno).id_mpr_linea
    return override or mpr_operario_linea.vigente(id_operario, fecha).id_mpr_linea
```

- **MUST** filtrar por `id_turno` al leer el override (Mañana y Tarde son independientes).
- Si el roster del turno trae `id_mpr_linea`, **manda** (override).
- Si es NULL, se usa la **línea habitual** vigente a esa fecha.

**UI planificación** (`/mpr/planificacion-turnos/`):

- **Grilla compacta (P0):** cada celda muestra solo chips de turno (color por franja), texto corto de línea override si aplica, candado si bloqueada, o «Asignar» si vacía. Clic en celda abre **modal editor** (no formularios inline en la grilla).
- **Editor de celda:** lista turnos del día con quitar (modal Synap), selector de línea por turno (POST `roster_linea_override`) y «Agregar turno» si quedan franjas libres.
- **Filtro excepciones (P1):** query `?filtro=excepciones` muestra operarios con override de línea o 2+ turnos algún día de la semana.
- **Filtros de grilla (P2):** barra en el chrome con búsqueda por nombre (`q`), turno activo (`turno=<id>`) y vista (`filtro=todos|sin_asignar|excepciones`). Contador «Mostrando N de M operarios»; botón **Limpiar filtros** si hay alguno activo. Los params se preservan en navegación de semana, POST de asignar/eliminar/línea/masivo y hidden fields del editor. La asignación masiva sigue listando todos los operarios (`operarios_todos`); el modal incluye filtro client-side por nombre.
- **Asignación masiva:** modos `agregar` (default), `solo_vacio`, `reemplazar` (con confirmación Synap); línea override opcional (`id_linea`); plantilla de días (`alcance_dias`: todos | lun_vie | personalizado con checkboxes Lu–Do); atajo **Semana visible Lun–Vie**.

**Carga móvil** (`/mpr/mi-parte/`): si el operario tiene varios turnos el día, selector de turno
(`?turno=<id>`); resolución de línea y parte editable por turno; un turno bloqueado (aprobado/CC)
no impide cargar el otro.

Con la línea resuelta, la carga móvil del operario lista las máquinas vigentes de esa línea y
sus artículos habilitados. Detalle del circuito:
[TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md#línea-habitual--override-de-roster).

> DDL override inicial: proveedor `mpr_maquina_linea_trazabilidad`
> (`core/services/legacy_mysql_schema/catalog.py`), idempotente.
> UK multi-turno: proveedor `mpr_roster_multi_turno` + `mpr/sql/005_mpr_roster_multi_turno_uk.sql`.
> Ver [../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md](../general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md).

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
#     asignaciones: {id_operario: {"YYYY-MM-DD": [{id_turno, nombre_turno, id_linea_override, id_linea_efectiva, ...}]}},
#     celdas_bloqueadas: {id_operario: {"YYYY-MM-DD": {id_turno: {bloqueada, motivo}}}}
#   }

set_linea_override_roster(base_empresa, fecha_str, id_operario, id_turno, id_linea|None) -> (ok, error)
# Override de línea solo para fecha+operario+turno; respeta bloqueos duros.

asignar_turno_roster(base_empresa, fecha_str, id_operario, id_turno) -> Tuple[bool, Optional[str]]
# INSERT si es turno nuevo ese día (multi-turno); upsert idempotente si ya existe la terna.
# Bloquea parte aprobada/física o CC confirmado del turno afectado.

eliminar_asignacion_roster(base_empresa, fecha_str, id_operario, id_turno=None) -> Tuple[bool, Optional[str]]
# Si hay varios turnos el día, `id_turno` indica cuál quitar. Bloquea parte aprobada/física o CC.

# Filtros de grilla (planificación, sin MySQL):
filtrar_operarios_roster_excepciones(operarios, asignaciones) -> list
filtrar_operarios_roster_sin_asignar(operarios, asignaciones, dias) -> list
filtrar_operarios_roster_por_turno(operarios, asignaciones, id_turno) -> list
filtrar_operarios_roster_busqueda(operarios, q) -> list
aplicar_filtros_roster_grilla(operarios, asignaciones, dias, *, filtro, id_turno, q) -> list
# Orden: vista (excepciones/sin_asignar) → turno → búsqueda por nombre.
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
    modo: str = "agregar",
    dias_semana: Optional[List[Any]] = None,
) -> Tuple[bool, Optional[str], Dict[str, Any]]
```

- **URL:** `planificacion-turnos/asignar-masivo/` (`roster_asignar_masivo`), vista `AsignarTurnoRosterMasivoView` (POST).
- **Campos del formulario:** `ids_operario` (lista), `id_turno`, `fecha_desde`, `fecha_hasta` (ISO `YYYY-MM-DD` desde inputs HTML), `semana` (redirect), `modo` (`agregar` | `solo_vacio` | `reemplazar`), `id_linea` (opcional), `alcance_dias` (`todos` | `lun_vie` | `personalizado`), `dias_semana` (lista `0`–`6` si personalizado; convención Python weekday).
- **Plantilla de días:** `alcance_dias=todos` (default) aplica cada día del rango; `lun_vie` omite sábado y domingo aunque el rango los incluya; `personalizado` filtra por los checkboxes enviados. Helper `_normalizar_dias_semana_roster(dias) -> Optional[set[int]]`. Contador `omitidos_plantilla` en resumen (celdas saltadas por plantilla); mencionado en flash si `> 0`. Atajo UI **Semana visible Lun–Vie** setea fechas lunes–viernes de la grilla visible y alcance `lun_vie`.
- **Modos:**
  - `agregar` (default): upsert del turno; no quita otros turnos del mismo día.
  - `solo_vacio`: omite días donde el operario ya tiene cualquier turno (`omitidos_con_turno`).
  - `reemplazar`: quita turnos no bloqueados del día y deja el turno objetivo; UI pide confirmación Synap antes del POST.
- **Reglas:** valida empresa, operarios y turno; recorre el rango con `_iter_dias_rango`; **omite celdas con parte aprobada/física o CC confirmado** (`omitidos_bloqueados`); **omite días fuera de la plantilla** (`omitidos_plantilla`); al reasignar celdas con borrador/pendiente migra sus líneas antes del `upsert_roster`. Retorna resumen `{aplicados, omitidos_pasados (siempre 0), omitidos_bloqueados, omitidos_con_turno, omitidos_plantilla, errores}`; éxito parcial si `aplicados > 0`.
- **Helper UI:** `mensaje_flash_asignacion_masiva(resumen, modo=...)` construye el mensaje de éxito en español.

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

> **UI refactor P0+P1 (12/08/2026):** grilla **compacta** (solo chips + override corto + candado / «Asignar»);
> edición en **modal de celda** (`celdaEditorOpen`); filtro **Excepciones** en chrome (`?filtro=excepciones`);
> asignación masiva con modos `agregar` / `solo_vacio` / `reemplazar`.

> **Chrome:** barra `slate-800` según [TABLERO_PRODUCCION_CHROME_DENSIDAD.md](TABLERO_PRODUCCION_CHROME_DENSIDAD.md) §3.1.

- Tabla con sticky-left en columna Operario; `thead` compacto (`text-[10px]`).
- Celdas clicables abren modal editor (quitar, línea, agregar turno); forms POST server-rendered dentro del modal.
- Celdas **bloqueadas**: chip + candado; sin edición inline en grilla.
- Celdas vacías: texto tenue «Asignar».
- Filtro **Todos** / **Excepciones** (servidor): operarios con override de línea o multi-turno en la semana.
- **Quitar turno** y **reemplazar día (masiva)** usan modales Synap (`bg-black/50 backdrop-blur-sm`); sin diálogos nativos.

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
| Unicidad (empresa, fecha, operario, turno) | DB UK `uk_mpr_roster_fecha_operario_turno` + upsert/INSERT en service |
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

Archivos principales:

- `mpr/tests/test_turnos_roster.py` — CRUD turnos, roster, asignación masiva
- `mpr/tests/test_roster_multi_turno_repo.py` — repo multi-turno, override, `listar_roster_semana`
- `mpr/tests/test_roster_multi_turno_ddl.py` — proveedor `mpr_roster_multi_turno` (UK idempotente)
- `mpr/tests/test_roster_migracion_parte.py` — guardrails, migración T→T', bloqueo por turno
- `mpr/tests/test_parte_movil_multi_turno.py` — carga móvil multi-turno

Ejecutar suite roster + móvil:

```bash
docker exec Synap_app python manage.py test \
  mpr.tests.test_turnos_roster \
  mpr.tests.test_roster_multi_turno_repo \
  mpr.tests.test_roster_multi_turno_ddl \
  mpr.tests.test_roster_migracion_parte \
  mpr.tests.test_parte_movil_multi_turno \
  --keepdb --noinput
```

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
