# Informe de archivo SDD

**Change:** `tiendanube-customer-mapping-hardening`  
**Fecha de archivo:** 14/07/2026  
**Modo:** hybrid (OpenSpec + Engram)  
**Veredicto de verificación:** PASS WITH WARNINGS (autorizado)

---

## Resumen ejecutivo

Endurecimiento del flujo manual `CustomerMapping` (validación de IDs, anti-duplicado en `create_customer`, unicidad `adminet_codigo`, listado con mapeos incompletos, sync explícito y defaults seguros). Tras sincronizar la spec al source of truth y mover la carpeta a archivo, el ciclo SDD queda completo.

---

## Trazabilidad Engram (IDs de observación)

| Artefacto | ID Engram | topic_key | Notas |
|-----------|-----------|-----------|-------|
| Proposal | — | `sdd/tiendanube-customer-mapping-hardening/proposal` | Solo filesystem (`proposal.md`) |
| Spec | — | `sdd/tiendanube-customer-mapping-hardening/spec` | Solo filesystem (`specs/tiendanube-customer-mapping/spec.md`) |
| Design | — | `sdd/tiendanube-customer-mapping-hardening/design` | Solo filesystem (`design.md`) |
| Tasks | — | `sdd/tiendanube-customer-mapping-hardening/tasks` | Solo filesystem (`tasks.md`) |
| Verify report | #1697 | `sdd/tiendanube-customer-mapping-hardening/verify-report` | PASS WITH WARNINGS |
| Archive report | (este documento) | `sdd/tiendanube-customer-mapping-hardening/archive-report` | Persistido en Engram |

---

## Specs sincronizadas

| Dominio | Acción | Detalle |
|---------|--------|---------|
| `tiendanube-customer-mapping` | **Creada** | Main spec inexistente; delta copiado como spec completa (6 requisitos ADDED, 0 MODIFIED, 0 REMOVED). |

**Totales delta del change:** 6 requisitos añadidos · 0 modificados · 0 eliminados

---

## Contenido archivado

Ruta: `openspec/changes/archive/2026-07-14-tiendanube-customer-mapping-hardening/`

| Artefacto | Estado |
|-----------|--------|
| `proposal.md` | ✅ |
| `design.md` | ✅ |
| `tasks.md` | ✅ (8/8 completadas) |
| `verify-report.md` | ✅ PASS WITH WARNINGS |
| `state.yaml` | ✅ |
| `specs/tiendanube-customer-mapping/spec.md` | ✅ (delta congelado) |
| `archive-report.md` | ✅ (este documento) |

La carpeta activa `openspec/changes/tiendanube-customer-mapping-hardening/` ya no existe.

---

## Source of truth actualizado

- `openspec/specs/tiendanube-customer-mapping/spec.md` — spec nueva creada desde delta

---

## Verificación al archivar

- [x] Main spec creada antes del movimiento
- [x] Carpeta movida a `archive/2026-07-14-tiendanube-customer-mapping-hardening/`
- [x] Sin issues CRITICAL en verify-report
- [x] Tareas 8/8 completadas
- [x] Tests: 15/15 OK (`manage.py check` sin errores)
- [x] Veredicto PASS WITH WARNINGS autorizado por orquestador

---

## Advertencias heredadas (no bloqueantes)

1. **5/7 escenarios spec sin test runtime:** validación IDs inexistentes (TN/Adminet), listado incompleto, sync AJAX UI, defaults sin Celery.
2. **Anti-duplicado CUIT:** implementado en código sin test dedicado (solo email cubierto).
3. **`manage.py test` sin `--keepdb`:** puede bloquearse con BD de test residual (`test_mydatabase`).

---

## Ciclo SDD

**Completo.** El change fue planificado, implementado, verificado (PASS WITH WARNINGS), spec sincronizada y archivado. Listo para el siguiente `/sdd-new` si aplica.
