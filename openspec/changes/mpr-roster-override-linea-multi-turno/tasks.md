# Tasks: Override de línea por UI + multi-turno en roster

**Change:** `mpr-roster-override-linea-multi-turno`  
**Diseño:** `docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md`  
**TDD base:** `docker exec Synap_app python manage.py test mpr.tests.test_turnos_roster mpr.tests.test_roster_migracion_parte`  
**Out of scope:** habitual retroactiva; migración auto `mpr_parte_linea`; override post-aprobación del turno

---

## Fase 1 — DDL catálogo + SQL idempotente

- [x] **T1** *(RED, sin deps)* — Crear `mpr/tests/test_roster_multi_turno_ddl.py`: tests fallidos del proveedor `mpr_roster_multi_turno` (idempotencia doble ejecución; UK nueva presente; UK vieja ausente; conteo filas sin cambio en fixture con 1 turno/op/día). Ejecutar en contenedor.
- [x] **T2** *(GREEN, T1)* — Crear `mpr/sql/005_mpr_roster_multi_turno_uk.sql`: `DROP INDEX uk_mpr_roster_fecha_operario` + `ADD UNIQUE KEY uk_mpr_roster_fecha_operario_turno (fecha, id_operario, id_mpr_turno)` con guards idempotentes (verificar índices antes).
- [x] **T3** *(GREEN, T2)* — Registrar proveedor `mpr_roster_multi_turno` en `core/services/legacy_mysql_schema/catalog.py`: verificar tabla; aplicar pasos §5.2 del doc diseño; **sin** DELETE/TRUNCATE/UPDATE masivo; registrar en `PROVIDER_REGISTRY` si aplica herramienta global.
- [x] **T4** *(T3)* — Documentar en test/comentario checklist pre/post deploy (conteos, `SHOW INDEX`) como aserciones o helper reutilizable para smoke manual.

## Fase 2 — Repositorio y servicios (UK, resolución, override)

- [x] **T5** *(RED, T4)* — Tests fallidos `turnos_del_operario_dia`: devuelve lista de turnos; reemplaza semántica de `turno_del_operario_dia` (`LIMIT 1`). Deprecar o delegar `turno_del_operario_dia` → primer turno solo donde sea transitorio.
- [x] **T6** *(GREEN, T5)* — Implementar `turnos_del_operario_dia` en `mpr/repositories/turno_roster.py`; ajustar `eliminar_roster` / nuevo `eliminar_roster_turno(fecha, op, id_turno)` para borrar por turno.
- [x] **T7** *(RED, T6)* — Tests fallidos `override_linea_roster(..., id_mpr_turno)`: filtra por turno; no mezcla overrides entre turnos del mismo día.
- [x] **T8** *(GREEN, T7)* — Actualizar `override_linea_roster` con parámetro `id_mpr_turno`; corregir `upsert_roster` / nuevo `insert_roster_turno`: INSERT segundo turno; `ON DUPLICATE KEY UPDATE` con `COALESCE` en `id_mpr_linea` al cambiar turno.
- [x] **T9** *(RED, T8)* — Tests fallidos `resolver_linea_operario(..., id_turno)`: override Mañana no afecta Tarde; NULL usa habitual.
- [x] **T10** *(GREEN, T9)* — Actualizar `mpr/services_operario.py` `resolver_linea_operario` para pasar `id_turno` al repo.
- [x] **T11** *(RED, T10)* — Tests fallidos `set_linea_override_roster`: solo toca `id_mpr_linea`; respeta bloqueo `(fecha, op, turno)`; clear a NULL.
- [x] **T12** *(GREEN, T11)* — Implementar `set_linea_override_roster` en `mpr/services.py`; wire validación guardrails existentes por turno.
- [x] **T13** *(RED, T12)* — Tests fallidos `listar_roster_semana`: payload con N turnos por celda; línea efectiva; flag bloqueado por turno.
- [x] **T14** *(GREEN, T13)* — Refactor `listar_roster_semana` y `asignar_turno_roster` / `asignar_turno_roster_rango` para multi-turno (INSERT agregar turno; no pisar fila existente).
- [x] **T15** *(T14)* — Auditar y actualizar consumidores críticos que usan `turno_del_operario_dia` o `LIMIT 1` (grep en `mpr/services.py`, planilla, trazabilidad) para pasar `id_turno` donde corresponda en esta fase o dejar TODO acotado a Fase 4 móvil.

## Fase 3 — UI planificación

- [x] **T16** *(RED, T14)* — Tests vista (opcional integración): **omitidos** — no hay suite previa de views roster en el repo; el contrato POST queda cubierto por servicios (`set_linea_override_roster`, `asignar_turno_roster`, `eliminar_asignacion_roster`) en `test_roster_multi_turno_repo.py` / `test_turnos_roster.py`. Filtro template `roster_ids_turno` cubierto en `test_turnos_roster.py`.
- [x] **T17** *(GREEN, T16)* — `mpr/views.py`: endpoints/acciones `set_linea_override_roster` (`SetLineaOverrideRosterView` → `roster_linea_override`), agregar turno (`roster_asignar` + `id_turno`), quitar turno por `(fecha, op, turno)`; context `lineas` activas en `PlanificacionTurnosView`.
- [x] **T18** *(T17)* — `mpr/templates/mpr/planificacion_turnos.html`: chips 0..N turnos; selector línea por turno (`Habitual` | filas); botón agregar turno; candado por turno; modales Synap; fechas dd/MM/yyyy; sin diálogos nativos.
- [x] **T19** *(T18)* — JS/Alpine: acciones por chip; confirmación quitar turno; feedback `mprShowAviso`/`SynapMessages`; advertencia borrador al cambiar línea (cantidades no se mueven).

## Fase 4 — Móvil multi-turno

- [x] **T20** *(RED, T10)* — Tests fallidos `services_parte_movil`: operario con Mañana+Tarde hoy; resolución línea independiente; un turno bloqueado no impide el otro.
- [x] **T21** *(GREEN, T20)* — Refactor `mpr/services_parte_movil.py` y template móvil asociado: listar turnos del día vía `turnos_del_operario_dia`; navegación/carga por turno.
- [x] **T22** *(T21)* — Verificar planilla QC / parte analista usan `resolver_linea_operario(..., id_turno)` (ajustes mínimos si Fase 2 dejó gaps).

## Fase 5 — Tests integración, regresión y documentación

- [x] **T23** *(T14, T18, T21)* — Ampliar `test_roster_migracion_parte.py`: multi-turno + bloqueo por turno + migración borrador T→T'.
- [x] **T24** *(T23)* — Regresión suite roster existente + smoke DDL idempotente en CI/contenedor.
- [x] **T25** *(T24)* — Actualizar `docs/mpr/TURNOS_Y_ROSTER.md`: UK `(fecha, id_operario, id_mpr_turno)`, resolución con `id_turno`, UI override, multi-turno, checklist deploy (enlace a doc diseño).
- [x] **T26** *(T25)* — Actualizar `docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md` estado a «implementado» con referencia al change openspec.

---

## Mapa de dependencias

```
T1→T2→T3→T4→T5→T6→T7→T8→T9→T10→T11→T12→T13→T14→T15
T14→T16→T17→T18→T19
T10→T20→T21→T22
T14,T18,T21→T23→T24→T25→T26
```

## Estimación por grupo

| Grupo | Tareas | IDs |
|-------|--------|-----|
| DDL catálogo + SQL | 4 | T1–T4 |
| Repo/servicios multi-turno | 11 | T5–T15 |
| UI planificación | 4 | T16–T19 |
| Móvil multi-turno | 3 | T20–T22 |
| Tests + docs | 4 | T23–T26 |
| **Total** | **26** | |

---

## Tareas listas para apply (Fase 1–2)

Las siguientes tareas están especificadas con criterio RED/GREEN y pueden iniciarse sin UI ni móvil:

| ID | Entregable | Archivos principales |
|----|------------|----------------------|
| **T1** | Tests DDL fallidos | `mpr/tests/test_roster_multi_turno_ddl.py` |
| **T2** | SQL UK idempotente | `mpr/sql/005_mpr_roster_multi_turno_uk.sql` |
| **T3** | Proveedor catalog | `core/services/legacy_mysql_schema/catalog.py` |
| **T4** | Checklist conteos en test | mismo módulo test T1 |
| **T5–T6** | `turnos_del_operario_dia`, delete por turno | `mpr/repositories/turno_roster.py` |
| **T7–T8** | Override por turno + upsert seguro | `mpr/repositories/turno_roster.py` |
| **T9–T10** | `resolver_linea_operario(id_turno)` | `mpr/services_operario.py` |
| **T11–T12** | `set_linea_override_roster` | `mpr/services.py` |
| **T13–T14** | `listar_roster_semana` multi-turno + asignación | `mpr/services.py` |
| **T15** | Audit consumidores `LIMIT 1` | grep + fixes acotados en servicios |

**Orden apply recomendado:** T1 → T2 → T3 → T4 (DDL verde) → T5–T8 (repo) → T9–T10 → T11–T12 → T13–T14 → T15.

**Precondición deploy:** ejecutar proveedor T3 en Staging/prod **antes** de mergear UI Fase 3.
