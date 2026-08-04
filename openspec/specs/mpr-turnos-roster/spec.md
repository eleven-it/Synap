# mpr-turnos-roster

## Purpose

Definir el capability de **gestión de turnos de producción** (CRUD) y **planificación semanal de asignación de turnos a operarios (roster)** en el módulo MPR de Synap. Este capability permite configurar turnos globales por empresa (ej. Mañana, Tarde, Noche) y asignar manualmente el turno de cada operario por fecha a través de una grilla semanal. Es la Etapa 3 del refactor MPR multietapa y cierra el ciclo de configuración de recursos antes del consumo en OPP (Etapa 4).

Archivado desde el change SDD `mpr-pipeline-etapa3-turnos-roster` (2026-07-03).

Documento operativo asociado: `docs/mpr/TURNOS_Y_ROSTER.md`.

---

## Requirements

### Requirement: Modelo MprTurno — Turnos Globales por Empresa

El sistema MUST proveer un modelo Django **`MprTurno`** que represente turnos de producción globales por empresa, con los siguientes campos:

- `base_empresa` (CharField, índice): scope por empresa.
- `nombre` (CharField, max 100): identificador del turno (ej. "Mañana", "Noche").
- `hora_inicio` (TimeField): hora de inicio del turno.
- `hora_fin` (TimeField): hora de finalización del turno.
- `activo` (BooleanField, default True): flag de activación (toggle).
- `creado_en` (DateTimeField, auto_now_add): auditoría.

El sistema MUST garantizar:
- **Unicidad de nombre por empresa**: UniqueConstraint (`base_empresa`, `nombre`).
- **Índice compuesto**: Index (`base_empresa`, `activo`).

#### Scenario: Crear turno estándar

- GIVEN un usuario con base_empresa "Empresa1"
- WHEN crea un turno con nombre="Mañana", hora_inicio="06:00", hora_fin="14:00"
- THEN el turno se guarda con `activo=True` y creado_en con timestamp actual
- AND el turno es visible en el listado de turnos de "Empresa1"

#### Scenario: Rechazar nombre duplicado

- GIVEN un turno existente con nombre="Mañana" en base_empresa="Empresa1"
- WHEN se intenta crear otro turno con nombre="Mañana" en la misma empresa
- THEN el sistema rechaza la operación con error de unicidad
- AND retorna mensaje "Ya existe un turno con ese nombre en la empresa"

---

### Requirement: Soporte para Turnos Nocturnos

El sistema MUST permitir **turnos nocturnos** que cruzan medianoche: si `hora_fin < hora_inicio`, el turno se interpreta como cruzando al día siguiente (ej. Noche 22:00-06:00).

El sistema MUST validar que `hora_inicio ≠ hora_fin`.

El sistema MUST documentar el cálculo de duración para turnos nocturnos: si `hora_fin < hora_inicio`, sumar 24 horas conceptuales al calcular duración.

#### Scenario: Crear turno nocturno

- GIVEN un usuario en base_empresa="Empresa1"
- WHEN crea un turno con nombre="Noche", hora_inicio="22:00", hora_fin="06:00"
- THEN el turno se guarda correctamente (hora_fin < hora_inicio permitido)
- AND el sistema interpreta que el turno cruza medianoche

#### Scenario: Rechazar turno con hora inicio igual a hora fin

- GIVEN un usuario intenta crear un turno con hora_inicio="08:00", hora_fin="08:00"
- WHEN envía el formulario
- THEN el sistema rechaza la operación
- AND retorna mensaje "La hora de inicio y fin no pueden ser iguales"

---

### Requirement: Solape de Horarios entre Turnos

El sistema MUST permitir que múltiples turnos tengan rangos horarios superpuestos (ej. Mañana 06:00-14:00 y Tarde 12:00-20:00).

El sistema NO MUST validar ni rechazar turnos por solape horario.

#### Scenario: Crear turnos con solape

- GIVEN un turno "Mañana" con hora_inicio="06:00", hora_fin="14:00" en empresa="Empresa1"
- WHEN se crea un turno "Tarde" con hora_inicio="12:00", hora_fin="20:00" en la misma empresa
- THEN ambos turnos se guardan sin error
- AND ambos son visibles en el listado de turnos

---

### Requirement: Toggle Activo/Inactivo de Turnos

El sistema MUST permitir activar/desactivar turnos mediante toggle (patrón UI canónico de sucursales/usuarios).

Los turnos inactivos (`activo=False`) NO MUST ofrecerse para nuevas asignaciones de roster.

Los turnos inactivos SE MUST conservar en asignaciones existentes de roster.

#### Scenario: Desactivar turno

- GIVEN un turno "Mañana" con `activo=True` en empresa="Empresa1"
- WHEN el usuario hace click en el toggle para desactivar
- THEN el campo `activo` se actualiza a `False`
- AND el turno desaparece del selector de turnos en la pantalla de planificación
- AND las asignaciones previas de ese turno en roster se mantienen intactas

#### Scenario: Reactivar turno

- GIVEN un turno "Tarde" con `activo=False`
- WHEN el usuario hace click en el toggle para reactivar
- THEN el campo `activo` se actualiza a `True`
- AND el turno vuelve a aparecer en el selector de planificación

---

### Requirement: Modelo MprRosterDia — Planificación Diaria

El sistema MUST proveer un modelo Django **`MprRosterDia`** que represente la asignación de un turno a un operario en una fecha específica, con los siguientes campos:

- `base_empresa` (CharField, índice): scope por empresa.
- `fecha` (DateField): fecha de la asignación.
- `id_operario` (IntegerField): FK lógico a `sue_abm_empleado.id_sue_abm_empleado`.
- `turno` (ForeignKey a MprTurno, on_delete=PROTECT): turno asignado.
- `creado_en` (DateTimeField, auto_now_add): auditoría.

El sistema MUST garantizar:
- **Constraint único**: Un operario tiene UN solo turno por fecha → UniqueConstraint (`base_empresa`, `fecha`, `id_operario`).
- **Índice compuesto**: Index (`base_empresa`, `fecha`).

#### Scenario: Asignar turno a operario en fecha

- GIVEN un operario con id_operario=123 en base_empresa="Empresa1"
- AND un turno id_turno=1 ("Mañana")
- WHEN se asigna el turno al operario para fecha="15/07/2026"
- THEN se crea un registro MprRosterDia con base_empresa="Empresa1", fecha="2026-07-15", id_operario=123, turno=1
- AND el operario aparece con "Mañana" en la grilla de planificación para esa fecha

#### Scenario: Reasignar turno (actualizar asignación existente)

- GIVEN un operario con id_operario=123 ya tiene asignado turno id_turno=1 ("Mañana") para fecha="15/07/2026"
- WHEN se reasigna al mismo operario el turno id_turno=2 ("Tarde") para la misma fecha
- THEN el registro existente se ACTUALIZA: turno=2
- AND NO se crea un registro duplicado

#### Scenario: Rechazar asignación duplicada (operario ya tiene turno en fecha)

- GIVEN un operario con id_operario=123 tiene asignado turno id_turno=1 para fecha="15/07/2026"
- WHEN se intenta crear una nueva asignación del mismo operario con turno id_turno=2 para la misma fecha (sin actualizar la existente)
- THEN el sistema rechaza la operación por violación del constraint único
- AND retorna mensaje "El operario ya tiene un turno asignado para esta fecha"

---

### Requirement: Quitar Asignación de Roster

El sistema MUST permitir desasignar (eliminar) el turno de un operario en una fecha específica.

#### Scenario: Desasignar turno de operario

- GIVEN un operario con id_operario=123 tiene asignado turno id_turno=1 para fecha="15/07/2026"
- WHEN el usuario quita la asignación (selecciona "Sin asignar" o presiona botón eliminar)
- THEN el registro MprRosterDia correspondiente se elimina
- AND la celda del operario en la grilla para esa fecha queda vacía

---

### Requirement: Pantalla de Planificación (Roster) — Grilla Semanal

El sistema MUST proveer una **pantalla de planificación** que muestre una grilla con:

- **Filas**: operarios activos (desde `sue_abm_empleado` con `anulado='No'`).
- **Columnas**: 7 días (lunes a domingo) de la semana seleccionada.
- **Celdas**: selector de turno para asignar el turno del operario en ese día.

El sistema MUST permitir:
- **Navegación semanal**: botones "Semana anterior" y "Semana siguiente" para cambiar de semana.
- **Rotación continua**: soporte para planificar cualquier semana (pasada, presente, futura).

#### Scenario: Visualizar grilla semanal

- GIVEN un usuario en base_empresa="Empresa1" accede a la pantalla de planificación
- AND selecciona semana del 14/07/2026 al 20/07/2026
- WHEN la grilla se carga
- THEN se muestran todos los operarios activos en filas
- AND se muestran 7 columnas (Lu 14/07, Ma 15/07, ..., Do 20/07)
- AND cada celda muestra el turno asignado (si existe) o selector vacío

#### Scenario: Navegar a semana siguiente

- GIVEN el usuario visualiza semana del 14/07/2026 al 20/07/2026
- WHEN hace click en botón "Semana siguiente"
- THEN la grilla se recarga mostrando semana del 21/07/2026 al 27/07/2026

---

### Requirement: Guardrail y migración de roster con ledger no físico (operario+fecha+turno)

El sistema MUST permitir **crear, editar y borrar asignaciones de roster** en **cualquier fecha** (pasado, hoy o futuro), salvo cuando exista producción registrada para la combinación **(operario, fecha, turno)**.

El bloqueo duro MUST aplicarse cuando:

- **Parte:** existe una línea en `mpr_parte` + `mpr_parte_linea` para esa fecha, turno y operario con estado **`aprobado`** o `movimiento_fisico_ok` verdadero.
- **Control de calidad confirmado:** existe al menos una fila en `mpr_transicion_lote` para esa fecha, turno y operario.

El sistema MUST NOT imponer tope de antigüedad ni restricción `fecha >= hoy`.

Si solo existen líneas de parte `borrador` o `pendiente`, sin stock físico:

- Al **reasignar** T → T', el sistema MUST mover atómicamente las líneas y ajustes no físicos del operario hacia un parte destino compatible (misma fecha, turno destino y origen), fusionando la clave artículo×operario×máquina cuando ya exista. También MUST migrar el borrador de clasificación CC del operario si existe.
- La migración MUST preservar `cantidad_declarada`, MUST NOT crear movimientos de stock, y MUST NOT tocar `mpr_transicion_lote` ni MSTOCK.
- Al **eliminar** asignación T → vacío, el sistema MUST rechazar la acción e indicar que el turno debe reasignarse.

Al **reasignar** T → T', MUST bloquear si hay parte aprobada/física o CC confirmado en T **o** en T'.

Al **asignar** vacío → T, MUST bloquear si hay parte aprobada/física o CC confirmado en T.

Al **eliminar** asignación con turno T, MUST bloquear si hay parte aprobada/física o CC confirmado en T.

La misma asignación T → T (idempotente, p. ej. solo override de línea): MUST permitir aunque haya parte o CC.

La UI MUST marcar celdas bloqueadas con ícono candado y tooltip con el motivo; MUST NOT mostrar selectores ni botón quitar en esas celdas.

#### Scenario: Editar asignación sin producción registrada

- GIVEN un operario tiene asignado turno "Mañana" para fecha="08/07/2026"
- AND no hay parte ni CC para ese operario en esa fecha y turno
- WHEN el usuario cambia el turno a "Tarde" en la grilla
- THEN la asignación se actualiza correctamente

#### Scenario: Reasignar borrador sin movimiento físico
- GIVEN un operario con turno "Mañana" y líneas de parte en estado `borrador` o `pendiente`
- AND no hay movimiento físico ni CC confirmado
- WHEN se reasigna al turno "Tarde"
- THEN las líneas, ajustes no físicos y borrador CC del operario se trasladan al turno "Tarde"
- AND no se crea ni modifica ningún movimiento de stock

#### Scenario: Intentar editar asignación con parte aprobado

- GIVEN un operario tiene asignado turno "Mañana" para fecha="08/07/2026"
- AND existe una línea de parte aprobada o con movimiento físico para ese operario, fecha y turno
- WHEN el usuario intenta cambiar o quitar el turno
- THEN el sistema rechaza la operación
- AND retorna mensaje indicando que hay partes registrados
- AND la celda en UI se muestra bloqueada (candado, sin controles de edición)

#### Scenario: Asignar turno en fecha pasada sin producción

- GIVEN hoy es 10/07/2026
- AND un operario no tiene turno asignado para fecha="08/07/2026"
- AND no hay parte ni CC para ese operario en turno "Mañana" el 08/07/2026
- WHEN el usuario asigna turno "Mañana" en esa celda
- THEN la asignación se crea correctamente

#### Scenario: Quitar turno con borrador pendiente
- GIVEN un operario con turno asignado y líneas de parte en `borrador` o `pendiente`
- WHEN intenta quitar el turno
- THEN el sistema rechaza la operación con el mensaje "No se puede quitar el turno: hay datos en parte borrador/pendiente. Reasigná a otro turno."

#### Scenario: Asignación masiva omite celdas bloqueadas

- GIVEN un rango de fechas con al menos una celda con parte aprobada/física o CC confirmado
- WHEN el usuario ejecuta asignación masiva
- THEN las celdas bloqueadas se omiten (`omitidos_bloqueados`)
- AND las celdas editables se aplican normalmente

#### Scenario: Reasignación idempotente con parte registrado

- GIVEN un operario tiene turno "Mañana" con parte registrado en esa fecha y turno
- WHEN el servicio recibe la misma asignación T → T (solo override de línea)
- THEN la operación se permite sin error

---

### Requirement: Formato de Fechas en UI — dd/MM/yyyy

El sistema MUST mostrar todas las fechas en la interfaz de usuario en formato **dd/MM/yyyy** (regla del repositorio para textos en español).

El sistema MUST aceptar entrada de fechas del usuario en formato dd/MM/yyyy y convertirlas internamente a formato ISO (yyyy-MM-dd) para almacenamiento.

#### Scenario: Mostrar fechas en grilla

- GIVEN la grilla de planificación para semana del 14/07/2026
- WHEN el usuario visualiza las columnas de días
- THEN las cabeceras de columna muestran "Lu 14/07/2026", "Ma 15/07/2026", etc.
- AND NO se muestran fechas en formato ISO (2026-07-14)

---

### Requirement: Solo Turnos Activos en Selector de Planificación

El sistema MUST listar únicamente turnos con `activo=True` en los selectores de la pantalla de planificación.

El sistema NO MUST permitir asignar turnos inactivos a nuevas fechas.

#### Scenario: Selector muestra solo turnos activos

- GIVEN turnos "Mañana" (activo=True), "Tarde" (activo=True), "Noche" (activo=False) en empresa="Empresa1"
- WHEN el usuario abre el selector de turno en una celda de la grilla
- THEN el selector lista solo "Mañana" y "Tarde"
- AND "Noche" NO aparece en el selector

---

### Requirement: CRUD de Turnos — Pantalla de Gestión

El sistema MUST proveer una **pantalla de listado de turnos** con las siguientes funcionalidades:

- Listar todos los turnos (activos e inactivos) de la empresa.
- Crear nuevo turno (botón "Nuevo turno" → formulario).
- Editar turno existente (botón "Editar" en fila → formulario).
- Toggle Activo/Inactivo (switch en columna Estado).

La pantalla MUST mostrar columnas: Nombre, Hora inicio, Hora fin, Estado (toggle).

La pantalla MUST incluir breadcrumb: **Producción / Turnos**.

#### Scenario: Listar turnos

- GIVEN un usuario con base_empresa="Empresa1" que tiene 3 turnos creados
- WHEN accede a la pantalla de turnos
- THEN se muestran los 3 turnos en una tabla
- AND cada fila incluye nombre, hora inicio, hora fin y toggle de estado

#### Scenario: Crear nuevo turno desde pantalla

- GIVEN un usuario en pantalla de turnos
- WHEN hace click en botón "Nuevo turno"
- THEN se muestra formulario con campos: nombre, hora inicio, hora fin
- AND al enviar el formulario válido, el turno se crea y redirige a listado

---

### Requirement: Validaciones y Mensajes de Error en Español

El sistema MUST validar:

- Nombre de turno no vacío y único por empresa.
- hora_inicio ≠ hora_fin.
- Constraint único de roster (operario/fecha).

El sistema MUST mostrar mensajes de **error y éxito en español**.

#### Scenario: Mensaje de error por nombre duplicado

- GIVEN un turno "Mañana" existente
- WHEN se intenta crear otro turno con nombre="Mañana"
- THEN el sistema muestra mensaje "Ya existe un turno con ese nombre en la empresa"

#### Scenario: Mensaje de éxito al crear turno

- GIVEN un usuario crea un turno válido
- WHEN el turno se guarda correctamente
- THEN el sistema muestra mensaje "Turno creado exitosamente"

---

### Requirement: Scoping por base_empresa y Autenticación

El sistema MUST aplicar **scoping por `base_empresa`** en todas las operaciones:

- Listar/crear/editar turnos: solo de la empresa del usuario (`request.user.base_empresa`).
- Listar/asignar roster: solo operarios y turnos de la empresa del usuario.

Todas las views MUST utilizar **`MprLoginRequiredMixin`** para autenticación.

#### Scenario: Usuario solo ve turnos de su empresa

- GIVEN usuario1 con base_empresa="Empresa1" y usuario2 con base_empresa="Empresa2"
- AND existen turnos en ambas empresas
- WHEN usuario1 accede al listado de turnos
- THEN solo ve turnos de "Empresa1"
- AND NO ve turnos de "Empresa2"

---

### Requirement: Uso de Tipos AdministraNET al Leer sue_abm_empleado

El sistema MUST aplicar helpers de normalización de tipos (`core.utils.administranet_types`) al leer datos de la tabla MySQL legacy `sue_abm_employado`:

- `to_int_or_none` para campos INT (ej. `id_sue_abm_empleado`, `id_cliente`).
- `str_or_default` para campos VARCHAR opcionales (ej. nombre_empleado, con default '-').

El sistema NO MUST enviar strings numéricos sin convertir a int ni string vacío en campos opcionales.

#### Scenario: Leer operario con tipos normalizados

- GIVEN un registro en sue_abm_empleado con id_sue_abm_empleado='123', nombre_empleado='Juan Pérez', id_cliente=NULL
- WHEN el sistema lee el operario con helper `obtener_operario`
- THEN devuelve {"id_sue_abm_empleado": 123 (int), "nombre_empleado": "Juan Pérez", "id_cliente": None}
- AND NO devuelve id_sue_abm_empleado como string '123'

---

### Requirement: Preparación para Etapa 4 (Consumo en OPP) — Opcional

El sistema PUEDE referenciar el roster como **insumo futuro** para la Etapa 4 (OPP: grilla turno×operador×artículo).

Esta referencia es **preparatoria** y NO implica implementación en Etapa 3.

El sistema NO MUST implementar consumo del roster en OPP en esta etapa.

#### Scenario: Documentar integración futura

- GIVEN el spec de `mpr-pipeline-multietapa`
- WHEN se documenta la Etapa 4
- THEN se menciona que OPP consumirá datos de MprRosterDia para determinar disponibilidad de operarios por turno
- AND esta funcionalidad está marcada como fuera de alcance de Etapa 3

---

### Requirement: Override de línea por día en el roster

La tabla `mpr_roster_dia` SHALL incluir una columna `id_mpr_linea` (BIGINT NULL) que permite **sobrescribir** la línea habitual del operario (`mpr_operario_linea`) para esa fecha/turno. `NULL` significa "usar la línea habitual".

La unicidad `(base_empresa, fecha, id_operario)` SHALL mantenerse; el override no crea filas nuevas, solo agrega el dato a la asignación del día. La resolución de línea del operario SHALL priorizar el override del roster sobre la línea habitual (`resolver_linea_operario`).

> Nota de implementación: la columna real es `mpr_roster_dia.id_mpr_linea` (el delta original la nombraba `id_linea`).

#### Scenario: Asignación con override

- **GIVEN** operario con línea habitual `Línea 1`
- **WHEN** el supervisor asigna en el roster de hoy turno Noche con `id_mpr_linea = Línea 3`
- **THEN** la resolución de línea del operario para hoy/Noche devuelve `Línea 3`

#### Scenario: Asignación sin override

- **WHEN** el supervisor asigna solo turno (sin `id_mpr_linea`)
- **THEN** `id_mpr_linea=NULL` y la resolución usa la línea habitual del operario

#### Scenario: Compatibilidad con roster existente

- **GIVEN** filas de roster anteriores al cambio (sin `id_mpr_linea`)
- **THEN** se interpretan como `id_mpr_linea=NULL` (usar habitual), sin romper la planificación

---

### Requirement: Persistencia del override vía catálogo central

La columna `id_mpr_linea` en `mpr_roster_dia` SHALL agregarse mediante `core/services/legacy_mysql_schema/catalog.py` (proveedor `mpr_maquina_linea_trazabilidad`, función `run_mpr_maquina_linea_mysql`) con DDL en `mpr/sql/004_mpr_parte_maquina_gap.sql`, de forma idempotente.

#### Scenario: Idempotencia

- **WHEN** se ejecuta dos veces el ALTER
- **THEN** no falla ni duplica la columna

---

## Fuera de Alcance

Los siguientes elementos NO están cubiertos por este spec y se abordarán en iteraciones posteriores:

- **Plantillas de rotación automáticas**: configuración de patrones de rotación semanal/mensual para aplicar masivamente.
- **Consumo del roster en OPP**: uso de MprRosterDia en grilla turno×operador×artículo (Etapa 4).
- **Transiciones por lote**: validación de que operarios asignados en roster existen en transiciones de lote (Etapa 5).
- **Trazabilidad OPT**: registro de turno/operario en órdenes de producción cerradas (Etapa 6).
- **Validación de solape horario**: restricción para evitar turnos con rangos superpuestos (permitido en MVP).
- **Historial de cambios en roster**: auditoría de modificaciones de asignaciones (iteración futura).
