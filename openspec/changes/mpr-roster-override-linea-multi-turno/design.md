# Design: Override de línea por UI + multi-turno en roster

## Fuente de verdad del diseño

El diseño funcional y de negocio completo está en:

**`docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md`**

Este `design.md` resume decisiones técnicas y apunta al doc anterior para detalle de UX, bloqueos, checklist deploy y criterios de aceptación. **No duplicar** tablas extensas ni checklist operativo aquí.

Documentación operativa asociada: `docs/mpr/TURNOS_Y_ROSTER.md`, `docs/mpr/TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md`.

---

## Technical Approach

Ampliar el capability `mpr-turnos-roster` en dos ejes acoplados que deben desplegarse alineados:

1. **Esquema:** reemplazar UK `(fecha, id_operario)` por `(fecha, id_operario, id_mpr_turno)` — solo DDL, sin reescritura de filas.
2. **Aplicación:** todas las lecturas/escrituras pasan de “un turno por operario/día” a “N turnos por operario/día”; override de línea granular por turno; UI y móvil consumen la lista.

Estado actual relevante:

- `mpr_roster_dia.id_mpr_linea` ya existe; `override_linea_roster` y `resolver_linea_operario` **no filtran por `id_turno`** (`LIMIT 1`).
- `upsert_roster` usa `ON DUPLICATE KEY UPDATE` sobre UK vieja → segundo turno **pisa** al primero.
- `turno_del_operario_dia` devuelve un solo turno (`LIMIT 1`).

---

## Architecture Decisions

| # | Decisión | Elegido | Alternativa rechazada | Rationale |
|---|----------|---------|-----------------------|-----------|
| ADR-1 | Granularidad override | `fecha + operario + turno` en `mpr_roster_dia` | Override solo por día (sin turno) | Un operario puede estar en líneas distintas por turno el mismo día |
| ADR-2 | Multi-turno | Sí; UK `(fecha, id_operario, id_mpr_turno)` | Mantener UK `(fecha, id_operario)` | Caso real Mañana+Tarde; habilita partes por turno sin conflicto |
| ADR-3 | Corrección diaria | Override en roster | Habitual retroactiva desde operarios-líneas | Habitual sigue “desde hoy”; no mezclar flujos |
| ADR-4 | Servicio override | `set_linea_override_roster(fecha, id_operario, id_turno, id_linea\|None)` dedicado | Reusar `asignar_turno_roster` con side-effect | Separar cambio de línea de cambio de turno; upsert parcial |
| ADR-5 | Upsert turno | `INSERT` nuevo turno; update parcial con `COALESCE(id_mpr_linea, …)` al cambiar turno | `ON DUPLICATE KEY UPDATE id_mpr_linea = VALUES(...)` siempre | Evita borrar override existente |
| ADR-6 | Resolución línea | `resolver_linea_operario(..., id_turno)` filtra roster por turno | `LIMIT 1` sin turno | Paridad planilla, parte analista y móvil |
| ADR-7 | Bloqueos | Por `(fecha, operario, turno)` — regla actual | Bloqueo por operario+día entero | Permite agregar otro turno si el primero tiene parte aprobado |
| ADR-8 | Deploy | **DDL primero**, idempotente, cero DELETE masivo; código multi-turno en mismo release | UI multi-turno antes de DDL | Previene pérdida de datos y pisado de filas |

---

## Decisión UK y migración DDL

**Constraint objetivo:**

```text
UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)
```

Reemplaza `uk_mpr_roster_fecha_operario (fecha, id_operario)`.

**Proveedor:** nuevo o extensión en `core/services/legacy_mysql_schema/catalog.py` (p. ej. `mpr_roster_multi_turno`).

**Pasos idempotentes:**

1. Verificar existencia de `mpr_roster_dia`.
2. Si existe UK vieja y **no** existe UK nueva → `DROP INDEX uk_mpr_roster_fecha_operario` + `ADD UNIQUE KEY uk_mpr_roster_fecha_operario_turno (...)`.
3. Si UK nueva ya existe → no-op.
4. **Prohibido** en este proveedor: `DELETE`, `TRUNCATE`, `UPDATE` masivo de datos de negocio.

**SQL de referencia:** nuevo archivo en `mpr/sql/` (p. ej. `005_mpr_roster_multi_turno_uk.sql`).

Filas actuales (1 turno/operario/día) siguen válidas bajo la nueva UK.

---

## Deploy seguro (resumen)

Ver checklist completo en `docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md` §5.

| Fase | Acción |
|------|--------|
| Pre | Backup BD; `COUNT(*)` total roster; `COUNT(*)` con `id_mpr_linea IS NOT NULL`; `SHOW INDEX` |
| DDL | Ejecutar proveedor en Staging → validar conteos iguales → Producción |
| Código | Mismo release (o flag): lecturas multi-turno + UI; **no** UI multi-turno sin DDL |
| Post | Smoke: 2 turnos mismo día; override aislado por turno; candado con parte aprobado |

**Compatibilidad crítica:**

| Capa | Mitigación |
|------|------------|
| `upsert_roster` + UK vieja | No desplegar UI multi-turno sin DDL |
| Lecturas `LIMIT 1` | Reemplazar por `turnos_del_operario_dia` en el release |
| Overrides SQL previos | Se conservan; solo cambia UK |
| Upsert sin `COALESCE` | Corregir en mismo release que UI línea |

**Rollback DDL:** solo seguro si no hay filas con `COUNT > 1` por `(fecha, id_operario)`. Tras uso real de multi-turno, rollback de índice es **irreversible en la práctica**; preferir rollback de feature/UI.

---

## Data Flow (servicios)

```text
Planificación GET
  listar_roster_semana(fecha_lunes)
    → listar_roster_rango (N filas por op×día)
    → por turno: id_mpr_linea, línea efectiva, bloqueado?

Override línea POST
  set_linea_override_roster(fecha, op, turno, id_linea|None)
    → validar bloqueo (fecha, op, turno)
    → UPDATE id_mpr_linea WHERE (fecha, op, turno)

Agregar turno POST
  asignar_turno_roster / insert_roster_turno
    → INSERT nueva fila (no UPDATE fila existente)

Resolución (planilla / móvil)
  resolver_linea_operario(base, op, fecha, id_turno)
    → override_linea_roster(..., id_turno)
    → else linea_habitual_operario(...)
```

---

## File Changes (implementación futura)

| File | Action | Description |
|------|--------|-------------|
| `core/services/legacy_mysql_schema/catalog.py` | Modify | Proveedor `mpr_roster_multi_turno` |
| `mpr/sql/005_mpr_roster_multi_turno_uk.sql` | Create | DDL UK idempotente |
| `mpr/repositories/turno_roster.py` | Modify | `turnos_del_operario_dia`, `override_linea_roster(..., id_turno)`, upsert seguro, `insert_roster_turno`, delete por turno |
| `mpr/services_operario.py` | Modify | `resolver_linea_operario` usa `id_turno` |
| `mpr/services.py` | Modify | `listar_roster_semana`, `set_linea_override_roster`, `asignar_turno_roster` multi-turno |
| `mpr/services_parte_movil.py` | Modify | Multi-turno del día |
| `mpr/views.py` | Modify | Endpoints override / agregar turno |
| `mpr/templates/mpr/planificacion_turnos.html` | Modify | Chips, override, agregar/quitar |
| `mpr/tests/test_turnos_roster.py` | Modify | Multi-turno, override, UK |
| `mpr/tests/test_roster_migracion_parte.py` | Modify | Bloqueos por turno |
| `docs/mpr/TURNOS_Y_ROSTER.md` | Modify | UK, resolución, UI |

---

## UX / Canon MPR

- Grilla semanal existente; celda pasa de un selector a **chips por turno** (Mañana/Tarde/Noche).
- Override: `Habitual` \| Fila 1..N por turno; fechas dd/MM/yyyy.
- Confirmaciones destructivas: modal Synap; feedback `mprShowAviso` / `SynapMessages`.
- Candado + tooltip cuando ledger bloqueante de **ese turno**.
- Extender `mpr/base_mpr.html`; **sin** `alert`/`confirm`/`prompt`.

Detalle UX: doc diseño §4.

---

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| DDL | Idempotencia UK; conteos pre/post | Test proveedor catalog + smoke SQL |
| Unit | `turnos_del_operario_dia`, override por turno, upsert no borra override | `docker exec Synap_app python manage.py test mpr.tests.test_turnos_roster` |
| Integration | Bloqueos por turno; multi-turno + planilla/móvil | `test_roster_migracion_parte`, tests planilla |
| Regresión | Asignación simple 1 turno/día sigue OK | Tests existentes roster |

---

## Open Questions

- [ ] ¿Feature flag para UI multi-turno post-DDL o activación directa en el release? Default propuesto: mismo release tras smoke Staging.
- [ ] ¿Endpoint AJAX separado para override vs reutilizar `asignar_turno_roster` con acción? Default: endpoint/servicio dedicado `set_linea_override_roster`.
