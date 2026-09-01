# 02 — Target vs Transition Rules

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## TARGET (permanente)

- Domain modules MUST NOT depend on ERP table names, connection details, or `base_empresa`.
- Dependency direction: Application → Port ← Adapter → External System.
- Core MUST NOT depend on domain modules.
- Each business datum MUST have one logical System of Record.
- Principal, Tenant, Company, Security MUST be explicit ExecutionContext — not session dict ad hoc.
- UI authorization MUST NOT substitute API authorization.
- Screens MUST derive navigation from product capabilities, not Django app names.

## TRANSITION (temporal)

| Transition Rule | Reason | Module | Expiration |
|-----------------|--------|--------|------------|
| Legacy SQL MAY remain in registered legacy boundaries | 587 write paths | mpr, ecom, core | Per Port migration |
| `administranet_*` services MAY be called until Port exists | Wrap not rewrite | core | Per capability |
| Session `user` dict MAY be used until PrincipalContext | Login path | login | Identity Phase |
| declarative-v1 + slug runners MAY coexist | Reports engine | reports | semantic-v2 ready |
| `mysql_pool.get_connection(base_empresa)` MAY be used in adapters | AN adapter | all adapters | Until abstract connection factory |

## ADMINISTRANET COMPATIBILITY (adapter only)

- AdministraNET adapter MAY use `base_empresa` internally.
- AdministraNET adapter MAY use `administranet_types` normalization.
- AdministraNET adapter MAY map Principal → `cod_usuario` / `id_usuario`.
- Domain MUST NOT import AdministraNET adapter concretely.
