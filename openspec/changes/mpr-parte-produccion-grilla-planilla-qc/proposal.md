# Proposal: Grilla analista alineada a planilla QC

## Intent

El analista carga producción desde la planilla física de Control de Calidad (máquina×artículo, turnos en columnas). La grilla actual filtra por un turno y usa operarios como columnas, desalineada del flujo real y del móvil (que ya persiste máquina). Refactor UX de `/mpr/parte-produccion/` para paridad con `construir_datos_planilla_control_calidad`.

## Scope

### In Scope
- Filas máquina×artículo (orden planilla QC); columnas fijas Mañana | Tarde | Noche con docenas + pares
- Columna Cupo Fabricando; inputs activos solo si cupo > 0; validación suma turnos del artículo ≤ Fabricando
- Filtros: Fecha (oblig.), Línea, Máquina, Marcas, búsqueda; nombre artículo sin código (código en tooltip/búsqueda)
- Celdas: operario desde roster línea/turno; herencia `id_operario`; selector si varios; deshabilitada sin roster
- Persistencia `id_mpr_maquina` en `mpr_parte_linea`; servicio, vista y template analista
- Tests y actualización `docs/mpr/PARTE_PRODUCCION.md`

### Out of Scope
- PWA operario `/mpr/mi-parte/`; columnas Color/Talle; flujo aprobación supervisor; DDL nuevo

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `mpr-opp-parte-produccion`: grilla analista tipo planilla QC; turnos como columnas; máquina en línea; cupo Fabricando por artículo
- `ui-fuente-verdad-reportes-mpr`: layout filtros y grilla según canon MPR/reports

## Approach

1. Builder de filas reutilizando `construir_datos_planilla_control_calidad` (`mpr/services_maquina_linea.py`) para fecha, línea y filtros.
2. Payload grilla: por fila `{id_maquina, id_articulo, fabricando, ingresado, turnos[{docenas, pares, operarios[]}]}`; precarga partes por (fecha, máquina, artículo, turno).
3. `RegistrarParteProduccionView`: celdas `parte_maq_{id}_art_{id}_turno_{id}`; `MprParte` por turno; líneas con `id_mpr_maquina` y unicidad `(parte, artículo, operario, máquina)`.
4. `parte_produccion.html`: tabla planilla, modales Synap, toggle docenas/pares, filtros MPR existentes.
5. Conservar validaciones cupo/techo envíos y asiento físico componente (E8).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `mpr/services.py` | Modified | Refactor o servicio analista dedicado |
| `mpr/services_maquina_linea.py` | Modified | Reuso planilla QC |
| `mpr/views.py` | Modified | ParteProduccionView, RegistrarParteProduccionView |
| `mpr/templates/mpr/parte_produccion.html` | Modified | UX planilla |
| `mpr/tests/` | Modified | Grilla, máquina, cupo |
| `docs/mpr/PARTE_PRODUCCION.md` | Modified | Flujo analista |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Regresión partes sin máquina | Med | Lectura compatible; nuevos exigen máquina |
| Roster vs línea filtrada | Med | Override roster; avisos en celdas deshabilitadas |
| Performance grilla grande | Low | Queries planilla QC; filtros server-side |

## Rollback Plan

Revertir commits de servicio, vistas y template; restaurar selector turno primario y grilla operarios×componentes. Sin migraciones destructivas. Partes con máquina ya guardados permanecen válidos.

## Dependencies

- `mpr-catalogo-maquina-linea`, `mpr-asignacion-maquina-articulo`, `mpr-turnos-roster` operativos
- `construir_datos_planilla_control_calidad` estable

## Success Criteria

- [ ] Filas coinciden con planilla QC (fecha/línea/orden)
- [ ] Tres columnas turno con docenas+pares; sin Color/Talle
- [ ] Suma por artículo ≤ Fabricando; celdas inactivas sin cupo
- [ ] `id_mpr_maquina` persistido en cada línea analista
- [ ] Operario roster visible; selector multi; celda deshabilitada sin roster
- [ ] UI español, canon MPR, sin diálogos nativos
- [ ] Tests contenedor OK; `/mpr/mi-parte/` sin cambios
