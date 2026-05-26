# Propuesta: Fuente de verdad UX/UI — Reportes dashboard y MPR (wizard / OPT)

## Intención

Fijar de forma **explícita y versionada** qué partes de Synap son la **referencia canónica** de interfaz (layout, patrones de feedback, tablas, héroes, modales, accesibilidad mínima) para trabajo futuro de migración, agentes y revisiones de código. Evita ambigüedad cuando coexisten pantallas legacy o en rediseño (p. ej. Ventas).

## Alcance

### En alcance

- Documentar en `docs/general/` la **fuente de verdad UI**: rutas, plantillas clave, estáticos asociados y patrones reutilizables.
- Añadir capability OpenSpec **`ui-fuente-verdad-reportes-mpr`** con requisitos normativos (MUST/MUST NOT) sobre qué referenciar y qué excluir.
- Opcional en fase de diseño/tareas: enlazar esta norma desde `docs/general/POLITICA_DOCUMENTACION.md` o inventario de migración, sin bloquear otros cambios.

### Fuera de alcance

- Rediseñar o refactorizar ahora las pantallas de **Presupuestos** u **Objetivos de venta** en `ventas/`.
- Unificar de inmediato todas las variantes `gray-*` vs `slate-*` entre módulos (puede quedar como deuda en diseño).
- Cambiar comportamiento funcional de informes o de MPR.

## Capabilities

### New Capabilities

| ID | Descripción |
|----|-------------|
| **ui-fuente-verdad-reportes-mpr** | Norma de referencia UI: superficies permitidas (`/reports/dashboard/<slug>/`, `/mpr/wizard/`, `/mpr/opt/...`), exclusiones (`/ventas/...` objetivos y presupuestos hasta rediseño), y artefactos de documentación asociados. |

### Modified Capabilities

Ninguna en `openspec/specs/` existente (no hay spec previo para este dominio).

## Enfoque

1. **Specs:** escenarios en español (Given/When/Then), RFC 2119; cubrir “equipo/agente MUST citar solo plantillas listadas como canon” y “MUST NOT usar ventas objetivos/presupuestos como patrón visual de referencia” hasta decisión explícita de producto.
2. **Design:** tabla de archivos concretos (`dashboard_detail.html`, `executive_summary.html`, `wizard.html`, `opt_list.html`, `opt_detail.html`, `base_mpr.html`, includes de filtros reportes, `dashboard.js` / `widget_engine.js` como runtime, no como “diseño ventas”).
3. **Implementación documental:** un archivo único en `docs/general/` (nombre acordado en design) + este cambio OpenSpec.

## Áreas afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `docs/general/` | Nuevo | Documento de fuente de verdad UI |
| `openspec/changes/fuente-verdad-ui-reportes-mpr/` | Nuevo | Delta specs, design, tasks |
| `reports/templates/`, `mpr/templates/` | Ninguno en esta fase | Solo referencia; sin edición obligatoria |
| `ventas/templates/` | Ninguno | Excluido como canon |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Equipo sigue citando ventas como referencia por hábito | Media | Spec MUST + enlace visible en docs de migración |
| Canon queda desactualizado si se rediseña reportes/MPR | Baja | Revisar spec al archivar cambios mayores en esas rutas |

## Plan de rollback

Eliminar o revertir el documento en `docs/general/` y archivar/abortar el cambio OpenSpec; no hay despliegue ni datos a revertir.

## Dependencias

- Decisión de producto ya tomada en conversación: Ventas objetivos/presupuestos **no** son fuente de verdad UI hasta nuevo aviso.

## Siguiente fase sugerida

`/sdd-continue fuente-verdad-ui-reportes-mpr` → **specs** (`specs/ui-fuente-verdad-reportes-mpr/spec.md`) y **design** (`design.md`).
