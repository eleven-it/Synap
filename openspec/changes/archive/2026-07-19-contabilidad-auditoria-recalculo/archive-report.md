# Informe de archivo SDD

> **ADDENDUM 19/07/2026 — Warnings resueltos post-archivo.** Las tres mejoras menores marcadas como warnings de este informe quedaron cerradas: **POL-07** (aviso reactivo de performance para `alcance_recompute=historico` en configuración y dry-run), **POL-10** (modelo `HistorialPoliticaAuditoria` + migración `0003`, registro al guardar y sección/endpoint de consulta) y **cobertura de tests** (18 tests nuevos para los 11 checks AUD-LECT sin cobertura). Suite conjunta `contabilidad_audit` + `legacy_db` (recalculo): **61 tests OK**. El veredicto efectivo pasa a **PASS**.

**Change:** `contabilidad-auditoria-recalculo`  
**Fecha de archivo:** 19/07/2026  
**Modo:** openspec (filesystem)  
**Veredicto de verificación:** PASS WITH WARNINGS

---

## Resumen ejecutivo

Motor de auditoría contable solo lectura (17 checks, AUD-LECT-01..23), políticas configurables en PostgreSQL Synap (POL-01..13) y pipeline de corrección controlada con dry-run/apply transaccional, regen de asientos compras/pagos, reconstrucción de saldos y REI defensivo (REC-01..18). 58/58 tareas completas; suite 40 tests OK (1 skip integración piloto). Gaps REC-07/08/14 cerrados antes del archivo.

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `contabilidad-auditoria-lectura` | **Creada** | 23 requisitos (AUD-LECT-01..23), motor solo lectura, registry 17 checks, UI tablero canon reports, checks compras/pagos |
| `contabilidad-politicas-configurables` | **Creada** | 13 requisitos (POL-01..13), modelo `PoliticaAuditoriaContable`, resolución default→override, `config_hash` |
| `contabilidad-recalculo-correccion` | **Creada** | 18 requisitos (REC-01..18), dry-run/apply, backup, orden seguro, regen asientos, rebuild saldos, rollback por lote |

**Totales delta:** 54 ADDED · 0 MODIFIED · 0 REMOVED (specs nuevas, sin main previa)

---

## Notas de merge

- No existían specs previas en `openspec/specs/` para las 3 capabilities de contabilidad.
- **Copia directa** del delta con formato main spec (sección `Requirements`, nota de archivo en `Purpose`).
- Sin merge destructivo. Todos los requisitos AUD-LECT, POL y REC preservados en source of truth.

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-19-contabilidad-auditoria-recalculo/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `exploration.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (58/58 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ archived |
| `specs/contabilidad-auditoria-lectura/spec.md` | ✅ (delta congelado) |
| `specs/contabilidad-politicas-configurables/spec.md` | ✅ |
| `specs/contabilidad-recalculo-correccion/spec.md` | ✅ |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/contabilidad-auditoria-recalculo/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/contabilidad-auditoria-lectura/spec.md`
- `openspec/specs/contabilidad-politicas-configurables/spec.md`
- `openspec/specs/contabilidad-recalculo-correccion/spec.md`

---

## Verificación al archivar

- [x] Main specs creadas antes del movimiento
- [x] Carpeta movida a archive con prefijo `2026-07-19`
- [x] Sin issues CRITICAL pendientes (gaps REC-07/08/14 cerrados; ver `state.yaml`)
- [x] Tareas 58/58 completadas
- [x] Tests scope change: 40 OK, 1 skip integración piloto
- [x] Carpeta activa eliminada de `openspec/changes/`

---

## Referencias externas (no rotas)

Referencias en código/docs a `openspec/changes/contabilidad-auditoria-recalculo/` siguen siendo válidas como ruta histórica si se actualizan al path archivado; no se modificaron en este paso (alcance: solo artefactos openspec). Rutas canónicas vigentes: `openspec/specs/contabilidad-*/spec.md`.

---

## Advertencias heredadas (no bloqueantes)

1. **POL-07:** advertencia UI de performance para `alcance_recompute=historico` — parcial/no verificada en verify-report.
2. **POL-10:** historial consultable de cambios de política — no implementado (solo `actualizado_*` último).
3. **Varios checks AUD-LECT** (10, 11, 12, 13, 15, 23) sin tests unitarios dedicados.
4. **`design.md`** contiene notas stale post-apply (p. ej. «contabilidad_audit NO existe»).
5. **`tasks.md`** pie «Listo para sdd-apply» obsoleto (artefacto congelado en archive).
6. **`verify-report.md`** refleja estado pre-cierre de gaps en sección CRITICAL; `state.yaml` confirma verify complete post REC-07/08/14.

---

## Ciclo SDD

**Completo.** Planificado, implementado, verificado (PASS WITH WARNINGS) y archivado. Listo para siguiente change.
