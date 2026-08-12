# Diseño: override de línea por UI + multi-turno el mismo día

**Estado:** implementado (Fases 1–5, change `mpr-roster-override-linea-multi-turno`)  
**Fecha:** 12/08/2026  
**Openspec:** `openspec/changes/mpr-roster-override-linea-multi-turno/`  
**Empresa / contexto operativo:** carga del parte al día siguiente; correcciones de línea frecuentes vía SQL hoy.  
**Relacionado:** [TURNOS_Y_ROSTER.md](TURNOS_Y_ROSTER.md), [TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md), [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md).

---

## 1. Problema de negocio

1. El encargado carga el parte **un día después** de la fecha de producción.
2. Suele no corregir a tiempo la línea de cada operario; la UI actual **no permite override de línea** en planificación, y la habitual solo se edita **desde hoy**.
3. En ocasiones un operario trabaja **más de un turno el mismo día** (p. ej. Mañana y Tarde). Hoy el roster lo impide (`UNIQUE (fecha, id_operario)`).
4. Las correcciones se hacen a mano en MySQL; hay que llevarlas a UI **sin perder ni pisar** datos ya guardados al desplegar.

---

## 2. Alcance del cambio (paquete único)

| # | Capacidad | Hoy | Objetivo |
|---|-----------|-----|----------|
| A | Override de línea por día **y turno** vía UI | Solo SQL; UI no envía `id_linea` | Selector en planificación (o modal equivalente) |
| B | Varios turnos el mismo día por operario | UK bloquea | UK `(fecha, id_operario, id_mpr_turno)` |
| C | Usable en **fecha pasada** antes de aprobar parte | Celda con candado si ya hay parte/CC | Permitir override/agregar turno si no hay ledger bloqueante de ese turno |
| D | Deploy seguro | — | Migración DDL idempotente + sin reescritura destructiva de filas |

**Fuera de alcance (fase 1):**

- Cambiar línea habitual con vigencia retroactiva como mecanismo de corrección diaria (prohibido como flujo normal).
- Migrar automáticamente `mpr_parte_linea` al cambiar override de línea (el parte no guarda `id_linea`; guarda operario + máquina).
- Permitir override de línea **después** de parte aprobado / movimiento físico / CC confirmado de ese turno.

---

## 3. Modelo de datos objetivo

### 3.1 `mpr_roster_dia` (MySQL empresa)

| Campo | Rol |
|-------|-----|
| `fecha` | Día de producción |
| `id_operario` | Operario |
| `id_mpr_turno` | Turno (Mañana / Tarde / Noche / …) |
| `id_mpr_linea` | Override de línea; `NULL` = habitual vigente a esa fecha |
| `creado_en` | Auditoría |

**Constraint objetivo:**

```text
UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)
```

Reemplaza:

```text
UNIQUE KEY uk_mpr_roster_fecha_operario (fecha, id_operario)
```

### 3.2 Resolución de línea

```text
resolver_linea_operario(id_operario, fecha, id_turno):
    fila = mpr_roster_dia(fecha, id_operario, id_turno)
    if fila.id_mpr_linea is not null:
        return fila.id_mpr_linea
    return mpr_operario_linea.vigente(id_operario, fecha).id_mpr_linea
```

**MUST** usar `id_turno` en el lookup de override (hoy el parámetro existe en firma pero no filtra).

### 3.3 Relación con el parte

- Cabecera `mpr_parte`: ya es por `(fecha_produccion, id_mpr_turno)`.
- Líneas `mpr_parte_linea`: `id_operario` + `id_mpr_maquina` (+ snapshot nombres); **sin** `id_mpr_linea`.
- Por tanto, multi-turno en roster **habilita** carga en varios turnos; no reescribe partes ya aprobados.

---

## 4. UI / UX (planificación de turnos)

> **Refactor UX P0+P1 (12/08/2026):** grilla compacta + modal editor de celda; filtro excepciones;
> asignación masiva con modos agregar / solo_vacio / reemplazar. Ver [TURNOS_Y_ROSTER.md](TURNOS_Y_ROSTER.md).

### 4.1 Grilla semanal

- Celda operario × día muestra **chips** de turnos (0..N); override de línea como texto corto bajo el chip.
- **Clic en celda** abre modal editor (no formularios densos inline en la grilla).
- Acciones por turno (en el modal):
  - Quitar turno (con confirmación Synap; mismos bloqueos que hoy).
  - Override de línea: `Habitual` | Fila 1..N (solo ese `fecha+operario+turno`).
- Acción “Agregar turno”: elegir turno aún no asignado ese día.
- Filtro **Excepciones** en chrome: operarios con override o multi-turno en la semana.

### 4.2 Bloqueos por integridad (por celda = fecha + operario + turno)

| Situación | Override línea | Agregar otro turno | Quitar / cambiar ese turno |
|-----------|----------------|--------------------|----------------------------|
| Sin parte ni CC de ese turno | Permitir | Permitir | Permitir |
| Borrador/pendiente con líneas | Advertir (cantidades no se mueven al cambiar línea) | Permitir otro turno distinto | Migración T→T' solo si cambia turno (regla actual) |
| Parte aprobado / `movimiento_fisico_ok` / CC de ese turno | **Bloquear** | Permitir **otro** turno sin ledger | **Bloquear** ese turno |

### 4.3 Upsert seguro

- Servicio dedicado `set_linea_override_roster(fecha, id_operario, id_turno, id_linea|None)`.
- Al cambiar **solo turno** (si aún aplica en algún flujo), **MUST NOT** borrar `id_mpr_linea` existente (`COALESCE` / update parcial).
- Al agregar segundo turno: `INSERT` nueva fila; no `UPDATE` la del primer turno.

---

## 5. Deploy y migración: no perder ni pisar datos

### 5.1 Principio

La migración de esquema **solo amplía** lo permitido. Las filas actuales (1 turno por operario/día) siguen siendo válidas bajo la nueva UK. **No** se borran, no se reescriben turnos, no se tocan `mpr_parte*` ni stock.

### 5.2 Pasos DDL (idempotente, catálogo central)

Proveedor nuevo o extensión en `core/services/legacy_mysql_schema/catalog.py` (p. ej. `mpr_roster_multi_turno`):

1. Verificar existencia de `mpr_roster_dia`.
2. Si existe `uk_mpr_roster_fecha_operario` y **no** existe `uk_mpr_roster_fecha_operario_turno`:
   - `ALTER TABLE ... DROP INDEX uk_mpr_roster_fecha_operario`
   - `ALTER TABLE ... ADD UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)`
3. Si la UK nueva ya existe → no-op.
4. **No** ejecutar `DELETE` / `TRUNCATE` / `UPDATE` masivo de datos de negocio en este proveedor.

Orden recomendado en deploy:

1. Backup / snapshot operativo de la BD empresa (procedimiento habitual).
2. Desplegar código que **tolera ambas UK** durante una ventana corta **o** aplicar DDL **antes** de activar UI multi-turno (preferido: DDL primero vía herramienta global / ensure schema, luego código que usa la UK nueva).
3. Smoke: conteo de filas `mpr_roster_dia` antes/después (debe ser igual).
4. Activar UI (mismo release o feature flag si se prefiere).

### 5.3 Compatibilidad de código en el deploy

| Capa | Riesgo | Mitigación |
|------|--------|------------|
| `upsert_roster` con UK vieja | Segundo turno pisa el primero | No desplegar UI multi-turno sin DDL nuevo |
| `upsert_roster` con UK nueva + código viejo que asume 1 fila/día | Lecturas con `LIMIT 1` / mapa `op→turno` pierden turnos extras | Actualizar **todas** las lecturas en el mismo release: `turno_del_operario_dia` → `turnos_del_operario_dia`; `listar_roster_semana` → lista de turnos; móvil |
| Override SQL manual previo (`id_mpr_linea` en fila única) | Se conserva | Ningún UPDATE masivo; solo cambia la UK |
| Reasignar turno desde UI vieja sin `id_linea` | Borra override | Corregir upsert en el mismo release que la UI de línea |

### 5.4 Checklist pre/post deploy (obligatorio)

**Antes**

- [ ] Contar filas: `SELECT COUNT(*) FROM mpr_roster_dia`
- [ ] Muestra de overrides: `SELECT COUNT(*) FROM mpr_roster_dia WHERE id_mpr_linea IS NOT NULL`
- [ ] Confirmar índice actual: `SHOW INDEX FROM mpr_roster_dia`
- [ ] Backup BD empresa

**DDL**

- [ ] Ejecutar proveedor idempotente en Staging → validar → Producción
- [ ] Recontar filas = mismo número
- [ ] Overrides count = mismo número
- [ ] `SHOW INDEX` muestra UK nueva; la vieja no existe

**Después (código)**

- [ ] Asignar 2 turnos al mismo operario en un día de prueba sin parte
- [ ] Override de línea en un turno no cambia el otro
- [ ] Celda con parte aprobado sigue bloqueada para ese turno
- [ ] Parte planilla / móvil resuelven línea con `id_turno`

### 5.5 Rollback

- **Código:** rollback de app a versión anterior **solo si** no se crearon filas multi-turno en prod; si ya hay 2+ turnos por operario/día, el código viejo es incorrecto.
- **DDL:** rollback de UK (volver a `(fecha, id_operario)`) **solo es seguro** si se garantiza `COUNT(*) GROUP BY fecha, id_operario HAVING COUNT(*) > 1` = 0. Si hay multi-turno reales, **no** revertir la UK sin consolidar/eliminar filas extra con criterio de negocio.

Por eso el DDL se considera **ampliación irreversible en la práctica** una vez usado multi-turno; el rollback preferente es de feature/UI, no de índice.

---

## 6. Servicios y puntos de código (implementado)

```
mpr/sql/005_mpr_roster_multi_turno_uk.sql + catalog.py → DDL UK (proveedor mpr_roster_multi_turno)
mpr/repositories/turno_roster.py     → turnos_del_operario_dia, override/upsert por turno
mpr/services_operario.py             → resolver_linea_operario(id_turno)
mpr/services.py                      → listar_roster_semana, set_linea_override_roster, asignar_turno_roster
mpr/services_parte_movil.py          → multi-turno del día + selector ?turno=
mpr/services_maquina_linea.py        → planilla QC usa resolver_linea_operario(id_turno)
mpr/templates/mpr/planificacion_turnos.html
mpr/templates/mpr/includes/parte_movil_selector_turno.html
docs/mpr/TURNOS_Y_ROSTER.md
tests: test_roster_multi_turno_*, test_parte_movil_multi_turno, test_roster_migracion_parte
```

---

## 7. Criterios de aceptación (fase 1)

1. Un operario puede tener Mañana y Tarde el mismo día en planificación; ambas filas persisten tras F5.
2. Override Fila X en Mañana no altera la línea efectiva de Tarde ese día.
3. En fecha pasada, sin parte de ese turno, se puede setear override por UI.
4. Con parte aprobado de ese turno, UI muestra candado; no cambia override ni quita turno.
5. Tras deploy DDL: `COUNT(*)` de `mpr_roster_dia` e overrides iguales a pre-deploy; ningún parte/stock modificado por la migración.
6. Habitual desde `/mpr/operarios-lineas/` sigue siendo “desde hoy”; no se usa para corregir un día pasado.

---

## 8. Orden de implementación sugerido

1. DDL UK + tests de migración idempotente (sin UI).
2. Lecturas multi-turno + `resolver_linea_operario(id_turno)` + upsert que no borre override.
3. UI override de línea (un turno por celda, como hoy).
4. UI agregar/quitar segundo turno el mismo día.
5. Carga móvil multi-turno.
6. Docs + manual usuario.

---

## 9. Decisiones cerradas

| Decisión | Valor |
|----------|--------|
| Override diario vs habitual retroactiva | Solo override en `mpr_roster_dia` |
| Granularidad override | `fecha + operario + turno` |
| Multi-turno mismo día | Sí |
| Post-aprobación / CC | Bloquear cambios de ese turno |
| Deploy | DDL amplía UK; cero DELETE de roster; checklist conteos; código y DDL alineados en el release |
