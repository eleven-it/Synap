# Delta for roles-synap-por-puesto

## ADDED Requirements

### Requirement: Rol Finanzas/Créditos por Puesto

El sistema MUST permitir asignar a puestos legacy (p. ej. Finanzas, Créditos, Administración) uno o más roles Synap que incluyan `finance.credito.aprobar` y/o `finance.credito.configurar`, vía `synap_puesto_rol`, sin crear puestos nuevos en `puestos`. La documentación MUST indicar puestos tipo recomendados: operador de cola (aprobar) vs administrador de políticas (configurar).

#### Scenario: Puesto Finanzas con permiso crédito

- **GIVEN** puesto «Finanzas» existente en `puestos` mapeado a rol «Créditos operador»
- **WHEN** se calculan permisos con `SYNAP_PERMISOS_SOURCE=synap`
- **THEN** el set MUST incluir `finance.credito.aprobar` si el rol lo tiene activo

#### Scenario: Asignación desde UI permisos-puesto

- **GIVEN** supervisor en `/core/permisos-puesto/` editando puesto Créditos
- **WHEN** asigna rol con permiso `finance.credito.aprobar` o `finance.credito.configurar`
- **THEN** MUST persistirse en `synap_puesto_rol` y `synap_rol_permiso`
- **AND** MUST NOT insertarse fila en `puestos`

#### Scenario: Vendedor sin rol Finanzas

- **GIVEN** puesto vendedor sin rol de crédito
- **WHEN** usuario intenta acceder cola Finanzas
- **THEN** MUST denegarse acceso por permisos efectivos

#### Scenario: Admin políticas sin cola

- **GIVEN** puesto solo con `finance.credito.configurar`
- **WHEN** usuario abre ABM políticas
- **THEN** MUST permitirse
- **AND** CTAs de aprobar/rechazar cola MUST permanecer denegados
