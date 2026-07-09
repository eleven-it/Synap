# Design: Permisos y roles Synap independientes de AdministraNET

## Technical Approach

Independizar la persistencia de permisos/roles Synap en tablas `synap_*` por empresa (MySQL), siguiendo el patrón **self-checkout / MPR**: DDL idempotente en `core/sql/`, proveedor en `catalog.py`, comando `manage.py`, seed Python desde `PERMISOS_POR_MODULO`. La **firma y contrato** de `get_permisos_totales_administranet` se mantiene; solo cambia la fuente interna según `SYNAP_PERMISOS_SOURCE`. Lectura legacy de `permisos` (Clavemenu) y `permisos_sistema` (TPV) **no se toca**.

Specs: `openspec/changes/permisos-roles-synap-independientes/specs/` (paralelo). Propuesta: `proposal.md`.

---

## Architecture Decisions

| Decisión | Alternativas | Elección | Rationale |
|----------|--------------|----------|-----------|
| Persistencia | DB central Synap (Opción B) | **`synap_*` en MySQL por empresa** | Mismo tenancy que runtime actual; sin nueva infra |
| Ancla de asignación | Rol por usuario | **Rol por puesto (`idpuesto`)** | Paridad con VB6/Synap hoy; `usuarios.idpuesto` ya es la ancla |
| Modelo rol backfill | Roles predefinidos compartidos | **Un rol por puesto (`es_sistema=1`)** | Preserva asignaciones actuales 1:1; roles compartidos quedan para UI P2+ |
| Charset tablas | utf8mb4 (MPR) | **latin1** | Alineado `permiso_sistema`, `self_checkout_*` y conexiones `charset='latin1'` |
| FK a `puestos` | FK física | **Sin FK; `idpuesto INT` lógico** | VB6 es dueño de `puestos`; Synap solo referencia el valor |
| FK entre `synap_*` | Solo lógicas | **FK InnoDB intra-`synap_*`** | Integridad del catálogo Synap sin acoplar legacy |
| Cutover | Big-bang | **Flag `legacy` → `dual` → `synap`** | Rollback inmediato; tests de paridad en `dual` |
| Escritura UI | Seguir `permiso_sistema_puesto` | **`synap_rol` / `synap_rol_permiso` / `synap_puesto_rol`** | Elimina contaminación del catálogo VB6 |

---

## Modelo de datos (`synap_*`)

**Archivo DDL:** `core/sql/001_synap_permisos_tables.sql`  
**Charset:** `latin1`, `ENGINE=InnoDB`. Tipos normalizados con `administranet_types` en Python.

```sql
-- synap_permiso: catálogo dinámico (seed desde PERMISOS_POR_MODULO + comodines)
CREATE TABLE IF NOT EXISTS synap_permiso (
    id_permiso INT NOT NULL AUTO_INCREMENT,
    key_permiso VARCHAR(128) NOT NULL,
    modulo VARCHAR(64) NOT NULL DEFAULT '-',
    nombre VARCHAR(255) NOT NULL DEFAULT '-',
    descripcion VARCHAR(500) NOT NULL DEFAULT '-',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_permiso),
    UNIQUE KEY uk_synap_permiso_key (key_permiso),
    KEY idx_synap_permiso_modulo (modulo),
    KEY idx_synap_permiso_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS synap_rol (
    id_rol INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(128) NOT NULL,
    descripcion VARCHAR(500) NOT NULL DEFAULT '-',
    es_sistema TINYINT(1) NOT NULL DEFAULT 0
        COMMENT '1=rol generado por backfill o sistema',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_rol),
    UNIQUE KEY uk_synap_rol_nombre (nombre),
    KEY idx_synap_rol_activo (activo)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS synap_rol_permiso (
    id_rol_permiso INT NOT NULL AUTO_INCREMENT,
    id_rol INT NOT NULL,
    id_permiso INT NOT NULL,
    PRIMARY KEY (id_rol_permiso),
    UNIQUE KEY uk_synap_rol_permiso (id_rol, id_permiso),
    KEY idx_synap_rp_rol (id_rol),
    KEY idx_synap_rp_permiso (id_permiso),
    CONSTRAINT fk_synap_rp_rol FOREIGN KEY (id_rol)
        REFERENCES synap_rol (id_rol) ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_synap_rp_permiso FOREIGN KEY (id_permiso)
        REFERENCES synap_permiso (id_permiso) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS synap_puesto_rol (
    id_puesto_rol INT NOT NULL AUTO_INCREMENT,
    idpuesto INT NOT NULL COMMENT 'Valor legacy; sin FK a puestos',
    id_rol INT NOT NULL,
    PRIMARY KEY (id_puesto_rol),
    UNIQUE KEY uk_synap_puesto_rol (idpuesto, id_rol),
    KEY idx_synap_pr_puesto (idpuesto),
    CONSTRAINT fk_synap_pr_rol FOREIGN KEY (id_rol)
        REFERENCES synap_rol (id_rol) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
```

---

## Provider en `catalog.py`

Imitar `run_mpr_core_tables_mysql` / `run_self_checkout_core_tables_mysql`:

| Paso | Implementación |
|------|----------------|
| Función | `run_synap_permisos_tables_mysql(conn) -> Dict[str, Any]` en `core/services/legacy_mysql_schema/catalog.py` |
| SQL | Lee `core/sql/001_synap_permisos_tables.sql`; split `;` + `_sc_sql_strip_leading_comments` |
| Seed post-DDL | Llama `seed_synap_permiso_catalog(conn)` (idempotente, ver § Seed) |
| Registry | `PROVIDER_REGISTRY` entrada `id: "synap_permisos_tables"`, `risk: "bajo"` |
| Export | Añadir en `core/services/legacy_mysql_schema/__init__.py` |
| CLI | `core/management/commands/apply_synap_permisos_tables.py` (wrapper como `apply_mpr_core_tables`) |
| Aplicación | Herramienta web `core:legacy_mysql_schema`; comando manual; **post-login** reemplaza sync legacy por `asegurar_synap_schema_si_procede(base_empresa)` (solo DDL+seed, sin escribir `permiso_sistema`) |

---

## Seed de `synap_permiso`

**Módulo:** `core/services/synap_permisos_seed.py`

- Fuente: `PERMISOS_POR_MODULO` + `MODULOS_CON_COMODIN` (extraer constante desde `sync_permisos_synap.py` → `core/constantes_permisos.py`).
- Idempotencia: `INSERT ... ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), modulo=VALUES(modulo), activo=1` por `uk_synap_permiso_key`.
- Comodines: `reports.*`, `stock.*`, `self_checkout.*`, `logistica.*` (misma lista que hoy `MODULOS_CON_COMODIN`).
- No crea filas en `permiso_sistema`.

---

## Backfill legacy → `synap_*`

**Comando:** `core/management/commands/backfill_synap_permisos_from_legacy.py`

**Estrategia (rol por puesto):**

1. Ejecutar provider + seed si faltan tablas.
2. Por cada `id_puesto` con filas `valor_permiso='Si'` en `permiso_sistema_puesto` JOIN `permiso_sistema` WHERE `grupo_permiso='Synap'`:
   - Crear/obtener rol `Synap — {nombre_puesto}` (`es_sistema=1`, nombre único por `idpuesto`).
   - `synap_puesto_rol`: `(idpuesto, id_rol)` — `INSERT IGNORE`.
   - Por cada `key_permiso` activo: resolver `id_permiso` en `synap_permiso`; `synap_rol_permiso` — `INSERT IGNORE`.
3. Puestos sin permisos Synap: no crear rol (lectura devuelve set vacío + Clavemenu/TPV).
4. Flags: `--base-empresa`, `--dry-run`, `--force` (re-sincroniza `synap_rol_permiso` desde legacy).

**Idempotencia:** claves únicas + `INSERT IGNORE`; re-ejecutar no duplica.

---

## Capa de lectura y cutover

**Nuevo módulo:** `core/services/synap_permisos.py`

```python
def get_permisos_desde_synap_store(
    base_empresa: str, id_puesto: Optional[int], ...
) -> Set[str]:
    """synap_puesto_rol → synap_rol_permiso → synap_permiso (activos)."""

def get_permisos_legacy_synap(
    base_empresa: str, id_puesto: Optional[int], ...
) -> Set[str]:
    """Query actual permiso_sistema + permiso_sistema_puesto (grupo Synap y resto)."""

def get_permisos_complementarios_legacy(
    base_empresa: str, id_puesto: Optional[int], ...
) -> Set[str]:
    """Tabla permisos (MAPEO_MENU_A_PERMISO) — siempre se suma."""
```

**Facade (sin cambiar consumidores):** `core/services/administranet_permisos_usuario.py::get_permisos_totales_administranet`

```
SYNAP_PERMISOS_SOURCE (settings.py, default "legacy"):
  legacy → permiso_sistema_puesto + complementarios
  synap  → synap_* + complementarios
  dual   → unión(synap, legacy_synap); log warning si difieren
```

**Reglas invariantes (todas las fuentes):**

- `cod_usuario == 'supervisor'` ⇒ `{"*"}` (retorno temprano).
- `nombre_puesto == 'supervisor'` o `cod_usuario == 'supervisor'` ⇒ `REPORTS_PERMISSIONS_FOR_SUPERVISOR`.
- Wildcards `modulo.*` y prefijos `modulo_` — verificación en `base_middleware.AdministraNETUser.tiene_permiso` y `core/utils/permissions.py` (sin cambios).

**Consumidores intactos:** `base_middleware.py`, `context_processors.py`, `decorators.py`, `utils/permissions.py`, `self_checkout/permissions.py`.

---

## Flujo de cálculo de permisos (nuevo)

```
                    get_permisos_totales_administranet
                                    │
                    ┌───────────────┴───────────────┐
                    │  cod_usuario == supervisor?   │
                    └───────────────┬───────────────┘
                          sí │              │ no
                             ▼              ▼
                          {"*"}     SYNAP_PERMISOS_SOURCE
                                    ┌──────┬──────┬──────┐
                                    │legacy│ synap│ dual │
                                    └──────┴──────┴──────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
    permiso_sistema_puesto          synap_puesto_rol              unión + log diff
    (MAX id por permiso)                 │                              │
              │                    synap_rol (activo)                     │
              │                          │                              │
              │                   synap_rol_permiso                      │
              │                          │                              │
              └──────────────────────────┴──────────────────────────────┘
                                           │
                              + permisos (Clavemenu → MAPEO_MENU_A_PERMISO)
                                           │
                              + REPORTS_PERMISSIONS_FOR_SUPERVISOR (si aplica)
                                           │
                                           ▼
                                    Set[key_permiso]
```

---

## Escritura / UI `/core/permisos-puesto/`

| Componente hoy | Cambio P2 |
|----------------|-----------|
| `views_permisos_puesto.py` — `sincronizar_permisos_synap_para_empresa` al abrir | Eliminar; llamar `asegurar_synap_schema_si_procede` |
| `AdministraNETPermisoSistemaService` — tab Synap | **`SynapPermisosService`** en `core/services/synap_permisos.py` |
| `permisos_puesto_toggle_synap_view` — `id_permiso_sistema` | Payload `id_permiso` (synap); escribe `synap_rol_permiso` vía rol del puesto |
| `permisos_puesto_modulo_synap_view` | Activa/desactiva por prefijo módulo en `synap_rol_permiso` |
| Pestañas Menú / Sistema | Sin cambio (`administranet_permisos_menu`, `permisos_sistema` legacy) |

**Flujo escritura por puesto:**

1. `obtener_o_crear_rol_puesto(base_empresa, idpuesto)` → rol dedicado o rol compartido asignado en `synap_puesto_rol`.
2. Toggle permiso: `INSERT/DELETE` en `synap_rol_permiso` (o upsert lógico).
3. Listado: JOIN `synap_permiso` LEFT JOIN `synap_rol_permiso` para el rol del puesto.

Plantillas: `core/templates/core/permisos_puesto_gestionar.html` — cambiar IDs expuestos al front (`id_permiso`).

---

## P3 — Limpieza

| Acción | Detalle |
|--------|---------|
| Retirar sync | Eliminar llamadas en `login/views.py`, `views_permisos_puesto.py`; deprecar `sync_permisos_synap.py` y `sync_synap_permissions_to_adminet` |
| SQL seguro legacy | Solo `grupo_permiso='Synap'`: `DELETE psp ... JOIN ps`; luego `DELETE FROM permiso_sistema WHERE grupo_permiso='Synap'` |
| Prohibir puestos | `administranet_puestos.py::crear_puesto` lanza excepción controlada; documentar alternativa (roles Synap) |
| Settings | `SYNAP_AUTO_SYNC_PERMISSIONS=False` por defecto en producción post-P3 |

**No borrar:** filas `permiso_sistema` con `grupo_permiso != 'Synap'` (AdministraNET VB6).

---

## Compatibilidad legacy

| Fuente | Acción |
|--------|--------|
| `permisos` (Clavemenu) | Lectura permanente vía `MAPEO_MENU_A_PERMISO` |
| `permisos_sistema` (TPV) | Lectura permanente en flujos TPV existentes (`administranet_permisos_sistema.py`) |
| `permiso_sistema` no-Synap | Lectura en modo `legacy`/`dual` hasta P3; después solo VB6 escribe ahí |
| Auth / sesión | Sin cambios (`AdministraNETAuth`, `base_middleware`) |

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `core/sql/001_synap_permisos_tables.sql` | Create | DDL 4 tablas `synap_*` |
| `core/services/legacy_mysql_schema/catalog.py` | Modify | `run_synap_permisos_tables_mysql` + registry |
| `core/services/legacy_mysql_schema/__init__.py` | Modify | Export nueva función |
| `core/services/synap_permisos.py` | Create | Lectura, escritura UI, rol-por-puesto |
| `core/services/synap_permisos_seed.py` | Create | Seed idempotente catálogo |
| `core/services/administranet_permisos_usuario.py` | Modify | Facade + flag + complementarios |
| `core/constantes_permisos.py` | Modify | `MODULOS_CON_COMODIN` centralizado |
| `core/management/commands/apply_synap_permisos_tables.py` | Create | CLI DDL |
| `core/management/commands/backfill_synap_permisos_from_legacy.py` | Create | Migración datos P1 |
| `core/management/commands/purge_synap_legacy_permisos.py` | Create | Limpieza P3 (solo grupo Synap) |
| `core/views/views_permisos_puesto.py` | Modify | UI escribe `synap_*` |
| `core/templates/core/permisos_puesto_gestionar.html` | Modify | `id_permiso` synap |
| `core/services/administranet_puestos.py` | Modify | Bloquear `crear_puesto` |
| `core/services/sync_permisos_synap.py` | Delete (P3) | Inyección legacy |
| `login/views.py` | Modify | Schema ensure en lugar de sync |
| `django_project/settings.py` | Modify | `SYNAP_PERMISOS_SOURCE`, deprecar auto-sync |
| `core/tests/test_synap_permisos.py` | Create | Paridad, idempotencia, flag |
| `core/tests/test_permisos_puesto_supervisor.py` | Modify | Mocks `SynapPermisosService` |
| `docs/general/APPS_CORE_Y_PERMISOS_ADMINISTRANET.md` | Modify | Nuevo modelo |
| `docs/general/SYNC_PERMISOS_SYNAP.md` | Modify | Deprecación |

---

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Seed, backfill, lectura synap | Mock cursor / fixtures MySQL |
| Integration | Paridad legacy vs synap por puesto | `backfill` + assert sets iguales en `dual` |
| Integration | UI toggle módulo | `test_permisos_puesto_supervisor` actualizado |
| Regression | Supervisor `{"*"}`, wildcards, SCO | `self_checkout/tests`, `test_synap_permisos` |
| Idempotencia | Provider + seed + backfill 2× | Sin filas duplicadas |
| Flag | `legacy` / `synap` / `dual` | Parametrize settings override |

Comando: `docker exec Synap_app python manage.py test core.tests.test_synap_permisos core.tests.test_permisos_puesto_supervisor`

---

## Migration / Rollout

| Fase | Acción | Flag |
|------|--------|------|
| **P0** | DDL + seed por empresa | `legacy` (default) |
| **P1** | Backfill + dual-read | `dual` en staging |
| **P2** | UI → `synap_*`; cutover lectura | `synap` |
| **P3** | Purge grupo Synap legacy; retirar sync | `synap`; sync off |
| **Rollback** | `SYNAP_PERMISOS_SOURCE=legacy` | DDL `synap_*` sin DROP |

---

## Riesgos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| Divergencia dual-read | Tests paridad; logs en `dual`; backfill idempotente |
| DDL no aplicado en alguna empresa | Provider en login + herramienta global + comando |
| Rol huérfano tras renombrar puesto VB6 | Rol `es_sistema` keyed por `idpuesto`; nombre es display |
| Borrado accidental legacy | SQL acotado a `grupo_permiso='Synap'`; comando `--dry-run` |
| `crear_puesto` usado por integraciones | Excepción explícita + doc alternativa roles Synap |

---

## Open Questions

- [ ] ¿Roles compartidos entre puestos en UI P2 (asignar mismo `id_rol` a varios `idpuesto`) o solo rol dedicado?
- [ ] ¿Invocar provider en `run_all_providers` global o solo bajo demanda (recomendado: **solo bajo demanda** por riesgo bajo)?
