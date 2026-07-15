# Sincronización automática de permisos Synap → AdministraNET

> **⛔ RETIRADO (2026-07).** Este mecanismo fue eliminado del código. Inyectaba los
> `key_permiso` de Synap en la tabla VB6 compartida `permiso_sistema` («contaminando»
> tablas de AdministraNET). Fue reemplazado por el **almacén propio Synap** (`synap_*`).
> Ver **[PERMISOS_SYNAP_STORE.md](PERMISOS_SYNAP_STORE.md)**.

## Reemplazo actual

| Antes (retirado) | Ahora |
|------------------|-------|
| `sync_permisos_synap.py` + `sync_synap_permissions_to_adminet` | `apply_synap_permisos_tables` (DDL + seed catálogo) |
| Inyección en `permiso_sistema` tras login | `asegurar_synap_schema_si_procede` (solo `synap_*`, sin VB6) |
| `SYNAP_AUTO_SYNC_PERMISSIONS=True` | `SYNAP_AUTO_SYNC_PERMISSIONS=False` (default); usar `SYNAP_AUTO_ENSURE_SCHEMA=True` |
| Asignaciones en legacy | `backfill_synap_permisos_from_legacy` + UI `/core/permisos-puesto/` |
| Limpieza manual | `purge_synap_legacy_permisos <base> --ejecutar` (tras cutover `synap` estable) |

## Comandos vigentes

```bash
# Crear tablas synap_* + sembrar catálogo (idempotente)
docker exec Synap_app python manage.py apply_synap_permisos_tables <base>

# Migrar asignaciones legacy → synap_*
docker exec Synap_app python manage.py backfill_synap_permisos_from_legacy <base>

# Limpiar filas grupo 'Synap' en permiso_sistema* (solo tras cutover synap estable)
docker exec Synap_app python manage.py purge_synap_legacy_permisos <base> --ejecutar
```

## Archivos eliminados (P3)

- `core/services/sync_permisos_synap.py`
- `core/management/commands/sync_synap_permissions_to_adminet.py`

El bootstrap (`bootstrap_instalacion`) invoca `apply_synap_permisos_tables` cuando se
indica `--base-empresa` (o se omite con `--skip-permisos-mysql`).

## Referencia histórica (comportamiento retirado)

Los permisos que Synap usa para menú y vistas (`usuarios.ver`, `reports.ver`, etc.)
**ya no** se insertan en `permiso_sistema`. Con `SYNAP_PERMISOS_SOURCE=synap` el runtime
lee exclusivamente `synap_*`. Las tablas legacy solo intervienen en modos `legacy`/`dual`
o en funcionalidades AdministraNET que aún las consultan directamente.
