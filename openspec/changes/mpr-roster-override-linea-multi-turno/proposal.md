# Proposal: Override de línea por UI + multi-turno en roster

## Intent

El encargado carga el parte **al día siguiente** y hoy corrige líneas de operarios a mano en MySQL porque la planificación no permite override de línea por día/turno ni asignar más de un turno el mismo día (`UNIQUE (fecha, id_operario)`). Este change habilita **override de línea vía UI** y **multi-turno por operario/día**, con migración DDL segura que no pierde ni pisa datos existentes.

**Fuente de diseño:** `docs/mpr/DISENO_ROSTER_OVERRIDE_LINEA_Y_MULTI_TURNO.md`

## Scope

### In Scope

- Migración DDL idempotente: UK `(fecha, id_operario, id_mpr_turno)` reemplaza `(fecha, id_operario)` en `mpr_roster_dia`
- Servicios/repositorio: `turnos_del_operario_dia`, `resolver_linea_operario` con `id_turno`, `set_linea_override_roster`, upsert que no borra override al cambiar turno
- `listar_roster_semana` y consumidores: N turnos por celda operario×día; línea efectiva (override o habitual)
- UI planificación: chips por turno, selector override línea, agregar/quitar turno; bloqueos por `(fecha, operario, turno)`; modales Synap
- Carga móvil `/mpr/mi-parte/`: operario con varios turnos el mismo día
- Tests (`test_turnos_roster`, `test_roster_migracion_parte`, planilla) y actualización `docs/mpr/TURNOS_Y_ROSTER.md`

### Out of Scope

- Cambiar línea habitual con vigencia retroactiva como mecanismo de corrección diaria
- Migrar automáticamente `mpr_parte_linea` al cambiar override de línea
- Override de línea **después** de parte aprobado / movimiento físico / CC confirmado de ese turno
- Plantillas de rotación automática; historial de auditoría de cambios en roster

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `mpr-turnos-roster`: UK multi-turno; override línea por `(fecha, operario, turno)` con UI; resolución de línea con `id_turno`; deploy DDL seguro; grilla y móvil multi-turno

## Approach

1. **DDL primero** (catálogo central + SQL idempotente): ampliar UK sin DELETE/UPDATE masivo; smoke conteos pre/post.
2. **Backend** en el mismo release: lecturas multi-turno, `set_linea_override_roster`, upsert parcial (`COALESCE` en `id_mpr_linea`).
3. **UI planificación**: celda con 0..N chips turno; acciones por turno; candado por ledger bloqueante.
4. **Móvil**: listar/participar en todos los turnos del día del operario.
5. **Docs + tests** alineados al diseño acordado.

Orden detallado: ver `tasks.md` y sección 8 del doc de diseño.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `core/services/legacy_mysql_schema/catalog.py` | Modified | Proveedor `mpr_roster_multi_turno` (UK) |
| `mpr/sql/` | Added | DDL idempotente UK roster |
| `mpr/repositories/turno_roster.py` | Modified | Multi-turno, override por turno, upsert seguro |
| `mpr/services_operario.py` | Modified | `resolver_linea_operario` filtra por `id_turno` |
| `mpr/services.py` | Modified | `listar_roster_semana`, `set_linea_override_roster`, `asignar_turno_roster` |
| `mpr/services_parte_movil.py` | Modified | Multi-turno del día |
| `mpr/views.py` | Modified | Endpoints override línea / agregar turno |
| `mpr/templates/mpr/planificacion_turnos.html` | Modified | Grilla multi-turno + override |
| `mpr/tests/` | Modified | Roster, migración UK, planilla |
| `docs/mpr/TURNOS_Y_ROSTER.md` | Modified | UK, resolución, UI |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UI multi-turno sin DDL nuevo pisa primer turno | High | Desplegar DDL antes de UI; checklist conteos |
| Código viejo con `LIMIT 1` pierde turnos extra | Med | Actualizar todas las lecturas en el mismo release |
| Upsert borra override al reasignar turno | Med | Update parcial con `COALESCE`; servicio dedicado override |
| Rollback UK con filas multi-turno reales | Med | Documentar irreversibilidad; rollback preferente de feature |

## Rollback Plan

- **Código:** revertir commits de servicio/vista/template/móvil. Seguro solo si no se crearon filas multi-turno en prod.
- **DDL:** revertir UK a `(fecha, id_operario)` **solo** si `COUNT(*) GROUP BY fecha, id_operario HAVING COUNT(*) > 1` = 0. Con multi-turno reales, no revertir índice sin consolidación de negocio.

## Dependencies

- `mpr-turnos-roster` operativo (MySQL fuente única)
- Columna `id_mpr_linea` ya presente en `mpr_roster_dia` (trazabilidad E8)
- Guardrails ledger `(operario, fecha, turno)` ya implementados en `asignar_turno_roster`

## Success Criteria

- [ ] Operario con Mañana y Tarde el mismo día persiste tras F5
- [ ] Override Fila X en Mañana no altera línea efectiva de Tarde
- [ ] Override en fecha pasada permitido sin parte/CC de ese turno
- [ ] Celda con parte aprobado de ese turno: candado; sin cambio override ni quitar turno
- [ ] Tras DDL: `COUNT(*)` roster e overrides iguales pre/post; sin tocar partes/stock
- [ ] Habitual en `/mpr/operarios-lineas/` sigue siendo “desde hoy”
- [ ] Móvil resuelve línea con `id_turno` para cada turno del día
- [ ] UI español, canon MPR, sin diálogos nativos
