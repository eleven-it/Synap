# Proposal: Mapeo endpoints reports para módulo IA

## Intent

Documentar y acotar el contrato de las APIs REST del módulo `reports` bajo `/api/reports/` para que el asistente de reportes en `ia` pueda resolver filtros y rutas de forma explícita, sin depender solo del código disperso o de llamadas directas a `QueryRunnerService`.

## Scope

### In Scope

- Inventario de endpoints relevantes (consulta, catálogo, filtros, schema, casos relay/ejecutivo/logística) con método, permisos y parámetros.
- Requisitos sobre el contrato de `POST /api/reports/query/` (serializer) y `GET /api/reports/filters/`.
- Criterio de qué endpoints el agente MUST/SHOULD exponer vía herramientas o documentación.

### Out of Scope

- Refactor grande unificando HTTP y `ReportToolsService` en un solo cliente (queda como decisión de diseño opcional).
- Cambiar permisos DRF ni comportamiento de runners SQL.

## Capabilities

### New Capabilities

- `reports-api-ia-bridge`: Contrato documentado y verificable entre APIs `reports` y consumo por el agente IA (incluye filtros y dependencias de sesión).

### Modified Capabilities

- None (no hay specs principales previas en `openspec/specs/`).

## Approach

Delta/full specs en `openspec/changes/mapeo-endpoints-reportes-ia/specs/`; diseño con decisiones sobre fuente de verdad (documento vs código vs tests checklist) y riesgo `base_empresa`/sesión.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/changes/mapeo-endpoints-reportes-ia/` | New | Artefactos SDD |
| `docs/reports/` o `ia/agents/reportes/` | Future | Destino probable del inventario publicado |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Desalineación doc vs código | Med | Referenciar rutas `reports/api_urls.py` y revisar en PR |

## Rollback Plan

Revertir commits que añadan solo documentación/specs; sin migraciones ni datos.

## Dependencies

- Sesión Synap con `base_empresa` para muchos GET de filtros.

## Success Criteria

- [x] Especificaciones aprobadas con escenarios Dado/Cuando/Entonces.
- [x] `design.md` con decisiones y estrategia de pruebas.
