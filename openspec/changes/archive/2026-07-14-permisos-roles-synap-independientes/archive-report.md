# Archive report — permisos-roles-synap-independientes

**Fecha:** 14/07/2026  
**Veredicto de verify:** PASS WITH WARNINGS  
**Archivado en:** `openspec/changes/archive/2026-07-14-permisos-roles-synap-independientes/`

## Specs sincronizadas a source of truth

| Dominio | Acción | Path |
|---------|--------|------|
| `permisos-synap-store` | Creada | `openspec/specs/permisos-synap-store/spec.md` |
| `roles-synap-por-puesto` | Creada | `openspec/specs/roles-synap-por-puesto/spec.md` |

## Cierre P3 / cutover

- `SYNAP_PERMISOS_SOURCE=synap` en `.env` local
- `SYNAP_AUTO_SYNC_PERMISSIONS` default `False`; sync legacy retirado
- Eliminados `sync_permisos_synap.py` y `sync_synap_permissions_to_adminet`
- Bootstrap usa `apply_synap_permisos_tables`
- Purge local `administranet` (Synap_mysql57): 203 filas `permiso_sistema` grupo Synap eliminadas
- Purge remoto (`administranet1` / `administranet96` en `192.168.0.2`): pendiente por conectividad

## Tests

`core.tests.test_synap_permisos` + `core.tests.test_permisos_puesto_supervisor` — 13 OK

## Ciclo SDD

Completo (explore → archive).
