# Tasks: Fuente de verdad UX/UI — Reportes y MPR

## Fase 1: Documentación y OpenSpec

- [x] 1.1 Crear `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` con rutas, plantillas, estáticos, exclusiones y notas de paleta.
- [x] 1.2 Crear delta spec `openspec/changes/fuente-verdad-ui-reportes-mpr/specs/ui-fuente-verdad-reportes-mpr/spec.md`.
- [x] 1.3 Crear `openspec/changes/fuente-verdad-ui-reportes-mpr/design.md`.
- [x] 1.4 Actualizar `openspec/changes/fuente-verdad-ui-reportes-mpr/state.yaml` (fases spec/design/tasks completas).
- [x] 1.5 Añadir enlace en `docs/general/POLITICA_DOCUMENTACION.md` al documento de fuente de verdad UI.

## Fase 2: Verificación manual

- [x] 2.1 Releer `proposal.md` frente a `spec.md` y comprobar que cada ítem de alcance tiene escenario o requisito correspondiente. *(Cerrado en `verify-report.md`.)*
- [x] 2.2 Comprobar que ningún ejemplo en el doc general cite como “patrón a copiar” rutas bajo `ventas/` para objetivos o presupuestos. *(Solo aparecen en §3 como exclusión.)*

## Fase 3: Cierre SDD (cuando corresponda)

- [x] 3.1 Tras validar en equipo, ejecutar archivo del cambio (`sdd-archive`) para fusionar spec a `openspec/specs/ui-fuente-verdad-reportes-mpr/spec.md` si aplica la convención del proyecto.
- [x] 3.2 Si se archiva, actualizar referencias en `docs/README.md` o índices generales si existen.
