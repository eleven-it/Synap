# Permisos y roles Synap independientes (`synap_*`)

Este documento describe el **almacén propio de permisos/roles de Synap**, independiente de
las tablas VB6 compartidas con AdministraNET (`permiso_sistema` / `permiso_sistema_puesto`).

Cambio SDD: `openspec/changes/permisos-roles-synap-independientes/` (design.md, tasks.md).

## 1. Motivación

AdministraNET (VB6) usa IDs fijos de permisos y puestos. Synap agregaba dinámicamente sus
`key_permiso` dentro de `permiso_sistema` (grupo `Synap`), **contaminando** tablas de VB6 y
acoplando el ciclo de vida de permisos de Synap al esquema legacy. La solución: mover los
permisos/roles de Synap a tablas namespaced `synap_*` en la misma base de cada empresa,
usando `puestos.idpuesto` como **ancla fija por valor** (sin FK a VB6).

## 2. Esquema (`core/sql/001_synap_permisos_tables.sql`)

| Tabla | Rol |
|-------|-----|
| `synap_permiso` | Catálogo de permisos Synap (`key_permiso` único). Sembrado desde `PERMISOS_POR_MODULO` + comodines. |
| `synap_rol` | Roles dinámicos (`es_sistema=1` = generado por backfill/UI, no eliminable). |
| `synap_rol_permiso` | M2M permiso ↔ rol. |
| `synap_puesto_rol` | Mapeo `idpuesto` (valor legacy, sin FK) ↔ rol. |

- Charset `latin1`, `InnoDB`. FKs físicas **solo** intra-`synap_*`.
- **Modelo actual: rol dedicado por puesto** (un `synap_rol` `es_sistema=1` por `idpuesto`).

## 3. Componentes

| Componente | Archivo |
|------------|---------|
| DDL + seed idempotente | `core/services/legacy_mysql_schema/catalog.py::run_synap_permisos_tables_mysql`; `core/services/synap_permisos_seed.py` |
| Capa de lectura | `core/services/synap_permisos.py` (`get_permisos_desde_synap_store`, `get_permisos_legacy_synap`, `get_permisos_complementarios_legacy`, `puesto_tiene_mapeo_synap`) |
| Fachada runtime | `core/services/administranet_permisos_usuario.py::get_permisos_totales_administranet` |
| Servicio UI | `core/services/synap_permisos.py::SynapPermisosService` |
| UI | `core/views/views_permisos_puesto.py`, `core/templates/core/permisos_puesto_gestionar.html` |

## 4. Feature flag `SYNAP_PERMISOS_SOURCE`

Controla la fuente de verdad en runtime (`django_project/settings.py`):

| Valor | Comportamiento |
|-------|----------------|
| `synap` (**cutover / menú Synap**) | Lee **solo** `synap_*`. **Sin** fallback a `permiso_sistema*`. |
| `dual` | Unión de ambas; registra `WARNING` si difieren (validación de paridad). |
| `legacy` | Lee de `permiso_sistema` + `permiso_sistema_puesto` (rollback / entornos no migrados). |

**Política de producto:** el menú y el control de acceso de pantallas Synap se arman con
permisos del almacén `synap_*`. Las tablas `permiso_sistema` / `permiso_sistema_puesto`
solo se leen cuando hace falta paridad con una funcionalidad legacy de AdministraNET
(o en modos `legacy`/`dual` de migración), **nunca** para “completar” el menú en modo `synap`.

Invariantes en los 3 modos: `cod_usuario='supervisor' → {"*"}`; permisos Reports para
supervisor; suma de complementarios de la tabla `permisos` (Clavemenu VB6; distinta de
`permiso_sistema*`).

**Rollback:** `SYNAP_PERMISOS_SOURCE=legacy` (sin DROP de tablas `synap_*`).

## 5. Otros settings

| Variable | Default | Descripción |
|----------|---------|-------------|
| `SYNAP_PERMISOS_SOURCE` | `legacy` (settings); en cutover usar `synap` | Fuente de permisos runtime. |
| `SYNAP_AUTO_ENSURE_SCHEMA` | `True` | Crea `synap_*` + siembra catálogo tras login / al abrir la UI. No escribe en VB6. |
| `SYNAP_AUTO_ENSURE_SCHEMA_TTL` | `86400` | TTL (s) del cache por empresa. |
| `SYNAP_BLOQUEAR_CREAR_PUESTOS` | `True` | Bloquea `crear_puesto` (los puestos se crean en AdministraNET). |
| `SYNAP_AUTO_SYNC_PERMISSIONS` | `False` | *(Retirado)* Sync que inyectaba en `permiso_sistema`. Mantener en `False`. |

## 6. Comandos

```bash
# Crear tablas synap_* + sembrar catálogo (idempotente)
docker exec Synap_app python manage.py apply_synap_permisos_tables <base>

# Migrar asignaciones legacy → synap_* (rol dedicado por puesto; idempotente)
docker exec Synap_app python manage.py backfill_synap_permisos_from_legacy <base> [--dry-run] [--force]

# Limpiar permiso_sistema/psp (grupo_permiso='Synap') — SOLO tras cutover synap estable
docker exec Synap_app python manage.py purge_synap_legacy_permisos <base>            # dry-run
docker exec Synap_app python manage.py purge_synap_legacy_permisos <base> --ejecutar # borra
```

También disponible como proveedor global: *Archivo → Migración esquema MySQL → «Synap — permisos y roles»*.

**Desde la UI (empresa logueada):** en `/core/permisos-puesto/` (usuario supervisor) hay botones
**«Simular (dry-run)»** y **«Ejecutar migración»** que corren el backfill para la empresa activa.
Ambos reutilizan `core.services.synap_permisos.backfill_synap_permisos_desde_legacy`.

## 7. Rollout por fases (P0–P3)

| Fase | Contenido | Estado |
|------|-----------|--------|
| **P0** | DDL `synap_*` + seed catálogo, sin cambio de runtime (`legacy`). | Completado (aplicado en `administranet96`). |
| **P1** | Capa de lectura, flag `SYNAP_PERMISOS_SOURCE`, fachada, backfill, tests. | Completado. |
| **P2** | UI escribe en `synap_*`; guard `crear_puesto`. | Completado (cutover por env pendiente). |
| **P3** | Retiro del sync legacy, purge de `grupo_permiso='Synap'`, docs. | Sync retirado; cutover local/dev con `SOURCE=synap` confirmado; purge pendiente de ejecución explícita (4.4). |

### Procedimiento de cutover recomendado

1. `apply_synap_permisos_tables <base>` y `backfill_synap_permisos_from_legacy <base>`.
2. `SYNAP_PERMISOS_SOURCE=dual` → observar logs de divergencia (deben ser 0 en el subconjunto Synap).
3. `SYNAP_PERMISOS_SOURCE=synap` (cutover). El menú usa **solo** `synap_*` (sin fallback
   a `permiso_sistema*`). Verificar que login y `/core/permisos-puesto/` **no** escriben
   en `permiso_sistema*`.
4. Estable → `purge_synap_legacy_permisos <base> --ejecutar` (comando listo; ejecución manual tras validación).

## 8. Refresco de permisos en sesión

Los permisos se calculan por request desde la fachada; los cambios en la UI de permisos por
puesto se reflejan al **volver a calcular** (normalmente en el siguiente login o al expirar
la cache de sesión). Tras editar permisos de un puesto, el usuario afectado debe **re-loguear**
para refrescar su sesión.

## 9. Prohibiciones

- Synap **no** escribe en `permiso_sistema` / `permiso_sistema_puesto`.
- Con `SYNAP_PERMISOS_SOURCE=synap`, el menú y `get_permisos_totales_administranet`
  **no** leen `permiso_sistema*` (ni como fallback).
- Synap **no** crea `puestos` (`idpuesto` es ancla fija de AdministraNET).
- Lecturas complementarias legacy (`permisos`/Clavemenu) se conservan.
- Lecturas puntuales de `permiso_sistema*` solo para funcionalidad legacy AdministraNET
  (p. ej. paridad MayoristApp / TPV) fuera del armado del menú Synap.
