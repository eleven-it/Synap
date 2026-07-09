# Verify — Verificación post-implementación

**Change:** `mpr-trazabilidad-maquina-linea-operario`
**Fecha:** 08/07/2026
**Modo:** Standard (validación por ejecución en contenedor `Synap_app` sobre base `administranet96`)

---

## Completitud (tasks.md)

| Métrica | Valor |
|--------|-------|
| Fases | 9 (1–9) |
| Fases completas | 9 |
| Tareas incompletas | 0 (todas marcadas [x]) |

Fase 1 (esquema), 2 (catálogos máquina/línea), 3 (habilitación máquina→artículo), 4 (login operario/permisos/landing/menú), 5 (operario→línea + roster override), 6 (carga móvil), 7 (aprobación supervisor + asiento), 8 (reportes P1), 9 (docs + verify + archive).

---

## Build & Tests

- **Django check**: ✅ `System check identified no issues (0 silenced)`.
- **Tests reportes MPR**: ✅ `Ran 28 tests ... OK` (`mpr.tests.test_reportes_mpr_view`, `test_reportes_presentacion`, `test_reportes_shell_legacy_map`).
- **Lints**: sin errores en archivos tocados.

---

## Matriz de cumplimiento (evidencia por ejecución en administranet96)

| Capability | Escenario clave | Evidencia | Resultado |
|---|---|---|---|
| catálogo máquina/línea | CRUD + asignación versionada | línea/máquina creadas, `asignar_maquina_linea` con vigencia | ✅ |
| asignación máquina↔artículo | habilitación vigente | `habilitar_articulo` + `listar_articulos_vigentes` | ✅ |
| operario-login | mapeo usuario→operario + landing | `resolver_operario_por_usuario`, landing operario puro | ✅ |
| parte móvil | grilla solo su línea/turno; docenas×12+pares | grilla M-001/artículo; declarada=41 (3×12+5) y 48 (4×12) | ✅ |
| parte móvil | guardar deja pendiente sin stock | `estado=pendiente`, `origen=movil_operario`, `cantidad=0`, `stock_deposito.saldo` sin cambio | ✅ |
| parte móvil | reeditar borrador/pendiente | mismo parte reutilizado; prefill correcto | ✅ |
| parte móvil | bordes | `sin_turno`, `sin_linea`, borrador vacío OK, pendiente vacío rechazado | ✅ |
| aprobación supervisor | gap + motivo obligatorio | gap=-2 sin motivo → error; con motivo → OK | ✅ |
| aprobación supervisor | aprobar mueve stock por aprobada | `cantidad_aprobada=39`, stock +39, `estado=aprobado`, auditoría | ✅ |
| aprobación supervisor | idempotencia | reaprobar no duplica stock | ✅ |
| aprobación supervisor | control de cupo | sin `forzar_cupo` bloquea con avisos de exceso | ✅ |
| parte directo (regresión) | nace aprobado/directo_supervisor | defaults del ALTER preservados; `validar_cupo_parte` compartida | ✅ |
| turnos-roster | override de línea | `id_mpr_linea`, `resolver_linea_operario` override>habitual | ✅ |
| reportes (8.1) | conciliación envíos↔producción | `componentes_sin_respaldo=1`, no_respaldado marcado | ✅ |
| reportes (8.2) | por operario y máquina + gap | filas por operario×máquina con declarada/aprobada/gap | ✅ |

---

## Coherencia (design.md)

| Decisión | Seguida | Notas |
|---|---|---|
| snake_case + prefijo `id_mpr_` | ✅ | tablas `mpr_linea`, `mpr_maquina`, etc. |
| Máquina como dimensión en `mpr_parte_linea` | ✅ | `id_mpr_maquina` + snapshot |
| Versionado vigencia_desde/hasta (half-open) | ✅ | máquina↔línea, máquina↔artículo, operario↔línea |
| Split declaración/aprobación reutilizando asiento OPP | ✅ | `_registrar_asiento_fisico_opp_parte(ya_componentes=True)` |
| Refactor cupo reutilizable | ✅ | `validar_cupo_parte` usado por parte directo y aprobación |
| Coexistencia parte directo | ✅ | comportamiento vigente intacto |
| MySQL fuente única | ✅ | sin espejo Postgres nuevo |

---

## Issues

- **CRITICAL**: Ninguno.
- **WARNING**: Los partes históricos previos a la Fase 1 no tienen `id_mpr_maquina` (se agrupan como "Sin máquina" en el reporte por máquina); esperado por backfill.
- **SUGGESTION**: Selector visual de línea en la grilla de planificación (backend ya soporta override). Cobertura por tests automatizados de la carga/aprobación móvil (hoy validada por ejecución manual en contenedor) podría formalizarse.

---

## Veredicto

**PASS** — Implementación completa y coherente con specs/design; validada por ejecución real en `administranet96`. Lista para archivar (`sdd-archive`).
