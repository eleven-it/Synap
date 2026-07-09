# Tasks: Permisos y roles Synap independientes de AdministraNET

**Change:** `permisos-roles-synap-independientes`  
**Design:** `design.md` | **Specs:** `specs/permisos-synap-store/spec.md`, `specs/roles-synap-por-puesto/spec.md`  
**Apply:** contenedor `docker exec Synap_app`

> **P0 = mínimo entregable seguro:** crear tablas `synap_*` + seed de catálogo **sin cambiar runtime** (`SYNAP_PERMISOS_SOURCE=legacy` por defecto).

---

## Phase 1: P0 — Esquema y seed (sin cambiar runtime)

- [x] 1.1 Crear `core/sql/001_synap_permisos_tables.sql` con DDL de `synap_permiso`, `synap_rol`, `synap_rol_permiso`, `synap_puesto_rol` (latin1, FK solo intra-`synap_*`, sin FK a `puestos`) — *spec: Esquema synap_* — Tablas y relaciones*
- [x] 1.2 Implementar `run_synap_permisos_tables_mysql(conn)` en `core/services/legacy_mysql_schema/catalog.py` (lee SQL, split `;`, `_sc_sql_strip_leading_comments`, invoca seed post-DDL) — *spec: Despliegue DDL idempotente vía catálogo central*
- [x] 1.3 Registrar proveedor `id: "synap_permisos_tables"`, `risk: "bajo"` en `PROVIDER_REGISTRY` de `catalog.py` (solo bajo demanda; no añadir a `run_all_providers` global)
- [x] 1.4 Exportar `run_synap_permisos_tables_mysql` en `core/services/legacy_mysql_schema/__init__.py`
- [x] 1.5 Extraer `MODULOS_CON_COMODIN` desde `core/services/sync_permisos_synap.py` hacia `core/constantes_permisos.py` (mantener compatibilidad de import temporal en sync hasta P3)
- [x] 1.6 Crear `core/services/synap_permisos_seed.py` con `seed_synap_permiso_catalog(conn)` idempotente desde `PERMISOS_POR_MODULO` + comodines — *spec: Seed del catálogo desde PERMISOS_POR_MODULO*
- [x] 1.7 Crear comando `core/management/commands/apply_synap_permisos_tables.py` (wrapper como `apply_mpr_core_tables`, args `base_empresa`, `--dry-run`)
- [x] 1.8 Crear `asegurar_synap_schema_si_procede(base_empresa)` en `core/services/synap_permisos_seed.py` (DDL+seed; **sin** escribir `permiso_sistema`)
- [x] 1.9 Verificar idempotencia P0: ejecutar proveedor 2× en BD dev (`SHOW TABLES LIKE 'synap_%'`; conteo estable en `synap_permiso`) — *spec: Re-ejecución del proveedor sin fallo* — **Aplicado en `administranet96`: 4 tablas, `synap_permiso`=217 (estable 2×), resto vacías. NOTA: el DDL no debe contener `;` dentro de `COMMENT` (el proveedor separa sentencias por `;`).**
- [x] 1.10 Confirmar que `SYNAP_PERMISOS_SOURCE` **no existe aún** o permanece implícito `legacy`; runtime sigue usando `permiso_sistema_puesto` sin cambios

---

## Phase 2: P1 — Backfill, capa de lectura y dual-read

- [x] 2.1 Crear `core/services/synap_permisos.py` con `get_permisos_desde_synap_store`, `get_permisos_legacy_synap`, `get_permisos_complementarios_legacy` (+ `puesto_tiene_mapeo_synap`) — *spec: Fuente de verdad runtime y feature flag*
- [x] 2.2 Añadir `SYNAP_PERMISOS_SOURCE` en `django_project/settings.py` (`legacy`|`synap`|`dual`, default `legacy`)
- [x] 2.3 Refactorizar `get_permisos_totales_administranet` en `core/services/administranet_permisos_usuario.py`: ramas `legacy` / `synap` / `dual` + invariantes supervisor `{"*"}`, `REPORTS_PERMISSIONS_FOR_SUPERVISOR`, suma Clavemenu — *spec: Paridad de permisos efectivos post-migración; Lecturas legacy complementarias conservadas*
- [x] 2.4 En modo `synap`, implementar fallback a legacy por puesto sin mapeo + log diagnóstico — *spec: Flag synap con fallback por dato faltante*
- [x] 2.5 En modo `dual`, unión legacy+synap con warning si difieren (design § cutover)
- [x] 2.6 Crear `core/management/commands/backfill_synap_permisos_from_legacy.py` (`base_empresa`, `--dry-run`, `--force`; rol por puesto `Synap · {nombre} (#idpuesto)`, `es_sistema=1`, `INSERT IGNORE`; solo key_permiso presentes en el catálogo synap_permiso) — *spec: Backfill idempotente desde legacy*
- [x] 2.7 En `login/views.py`, reemplazar `asegurar_permisos_synap_si_procede` por `asegurar_synap_schema_si_procede` (solo DDL+seed en login; **sin** INSERT en `permiso_sistema`)
- [x] 2.8 Auditar consumidores de `get_permisos_totales_administranet`: firma intacta; smoke import OK de middleware/context_processors/decorators/utils.permissions/self_checkout.permissions
- [x] 2.9 Crear `core/tests/test_synap_permisos.py`: 9 tests (enrutado legacy/synap/dual, fallback, complementarios, supervisor `{"*"}`, nombre_puesto Supervisor, catálogo único+comodines) — **verdes**
- [x] 2.10 Backfill aplicado en `administranet96` (idempotente 2×); paridad `synap == legacy ∩ catálogo` verificada para el puesto migrado (puesto 1 → {clientes.ver})

---

## Phase 3: P2 — Cutover lectura y UI `/core/permisos-puesto/`

- [x] 3.1 Extender `core/services/synap_permisos.py` con `SynapPermisosService`: `obtener_o_crear_rol_puesto` (rol dedicado por puesto), `listar_permisos`, `actualizar_valor_permiso` (toggle), `establecer_modulo_para_puesto` (atajo), `obtener_grupos` — *spec: Operaciones UI escriben solo en synap_* [decisión: rol dedicado por puesto, sin roles compartidos en UI]*
- [x] 3.2 `obtener_o_crear_rol_puesto` mapea `synap_puesto_rol` por valor `idpuesto` (sin FK a VB6); la vista valida el puesto vía `AdministraNETPuestosService.obtener_puesto`
- [x] 3.3 Refactorizar `core/views/views_permisos_puesto.py`: eliminado `sincronizar_permisos_synap_para_empresa` (→ `asegurar_synap_schema_si_procede`); pestaña Synap usa `SynapPermisosService`; payload toggle `id_permiso`
- [x] 3.4 Actualizar `core/templates/core/permisos_puesto_gestionar.html` (IDs `id_permiso`, texto synap_*). *UI de roles compartidos N/A: decisión de rol dedicado por puesto.*
- [x] 3.5 Pestañas Menú (`permisos`/Clavemenu) y Sistema (`permisos_sistema`) intactas, sin escritura en `permiso_sistema_puesto`
- [x] 3.6 Bloquear `crear_puesto` en `core/services/administranet_puestos.py` (`CreacionPuestoBloqueadaError`, flag `SYNAP_BLOQUEAR_CREAR_PUESTOS` default True) + mensaje español en `views_roles.py`
- [ ] 3.7 Cutover staging: `SYNAP_PERMISOS_SOURCE=synap` — **pendiente (decisión: code_only, cutover por env cuando se indique)**. Verificado en smoke: toggle/atajo NO tocan `permiso_sistema_puesto` (1865→1865)
- [x] 3.8 Actualizar `core/tests/test_permisos_puesto_supervisor.py` con mocks `SynapPermisosService` + `asegurar_synap_schema_si_procede`
- [x] 3.9 Regresión: 16 tests `test_synap_permisos` + `test_permisos_puesto_supervisor` verdes. `self_checkout.tests.test_permissions` con 4 fallas **preexistentes** (302 auth en entorno test, confirmadas con git stash; ajenas a este cambio)

---

## Phase 4: P3 — Limpieza legacy, retiro sync y documentación

- [x] 4.1 Crear `core/management/commands/purge_synap_legacy_permisos.py` (solo `grupo_permiso='Synap'`; dry-run por defecto, `--ejecutar` para borrar). Dry-run verificado en `administranet96`: 217 filas `permiso_sistema` + 1 `permiso_sistema_puesto`.
- [ ] 4.2 Eliminar `core/services/sync_permisos_synap.py` y referencias (`sync_synap_permissions_to_adminet`, `bootstrap_instalacion`) — **DIFERIDO: gated en cutover real `synap` estable** (runtime aún en `legacy` depende de `permiso_sistema`; borrarlo ahora rompería instalaciones nuevas)
- [ ] 4.3 Establecer `SYNAP_AUTO_SYNC_PERMISSIONS=False` por defecto — **DIFERIDO al cutover**. Preparado: `asegurar_synap_schema_si_procede` desacoplado a flag propio `SYNAP_AUTO_ENSURE_SCHEMA` (default True) → apagar el sync legacy no afectará el aseguramiento de esquema.
- [ ] 4.4 Ejecutar purge en empresas con backfill validado y `SYNAP_PERMISOS_SOURCE=synap` estable — **DIFERIDO (requiere confirmación explícita + cutover)**
- [x] 4.5 Actualizar `docs/general/APPS_CORE_Y_PERMISOS_ADMINISTRANET.md` (modelo `synap_*`, flag, fachada)
- [x] 4.6 Actualizar `docs/general/SYNC_PERMISOS_SYNAP.md` (banner de deprecación + reemplazo por seed/backfill/purge)
- [x] 4.7 Actualizar `docs/general/PERMISOS_ASIGNACION_POR_PUESTO_SUPERVISOR.md` (tablas synap_*, rol dedicado, re-login)
- [x] 4.8 Crear `docs/general/PERMISOS_SYNAP_STORE.md` (esquema, componentes, flag, comandos, rollout P0–P3, cutover, rollback)
- [x] 4.9 Suite verde: `test_synap_permisos` + `test_permisos_puesto_supervisor` (14 tests). Nota: `self_checkout.tests.test_permissions` con 4 fallas **preexistentes** (ajenas).

---

## Criterios de aceptación / verificación

Enlazado a **Criterios de éxito** (`proposal.md` §8):

- [x] **CA-1** Synap no escribe en `permiso_sistema` / `permiso_sistema_puesto` desde la UI (smoke `administranet96`: 1865→1865 tras toggle/atajo). Login usa schema-ensure sin inyección.
- [x] **CA-2** Permisos/roles persisten en `synap_*`; paridad `synap == legacy ∩ catálogo` validada en 8 puestos (0 divergencias, equivalente a modo `dual`).
- [x] **CA-3** Suite Synap verde (`test_synap_permisos`, `test_permisos_puesto_supervisor`).
- [x] **CA-4** Documentación actualizada (3 docs existentes + `PERMISOS_SYNAP_STORE.md`).
- [x] **CA-5** Rollback: `SYNAP_PERMISOS_SOURCE=legacy` es el default; la fachada lee legacy sin DROP de `synap_*` (test `test_source_legacy`).
- [x] **CA-6** `crear_puesto` bloqueado (`CreacionPuestoBloqueadaError` + flag); ningún flujo Synap incrementa `MAX(idpuesto)`.
- [x] **CA-7** Lecturas complementarias `permisos` (Clavemenu) intactas en los 3 modos (test `test_complementarios_clavemenu_siempre_sumados`); `permisos_sistema` (TPV) no tocado.

**Verificación rápida por fase:**

| Fase | Comando / check |
|------|-----------------|
| P0 | `apply_synap_permisos_tables <base>` 2×; `SELECT COUNT(*) FROM synap_permiso` estable |
| P1 | `backfill_synap_permisos_from_legacy <base>` 2×; tests paridad con `SYNAP_PERMISOS_SOURCE=dual` |
| P2 | Toggle en `/core/permisos-puesto/` persiste solo en `synap_rol_permiso`; flag `synap` en staging |
| P3 | `purge_synap_legacy_permisos --dry-run`; sync retirado; filas grupo Synap ausentes en legacy |
