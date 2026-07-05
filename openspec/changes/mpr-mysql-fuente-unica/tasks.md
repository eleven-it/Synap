# Tasks: MPR fuente única en MySQL

**Change:** `mpr-mysql-fuente-unica`  
**Design:** `design.md` | **Apply:** contenedor `docker exec Synap_app`

---

## Phase 1: P0 — Esquema MySQL (sin runtime)

- [x] 1.1 Crear `docs/mpr/sql/001_mpr_core_tables.sql` (13 tablas, utf8mb4, FK, seed `mpr_config`)
- [x] 1.2 Implementar `run_mpr_core_tables_mysql` en `catalog.py` + entrada `mpr_core_tables` en `PROVIDER_REGISTRY`
- [x] 1.3 Crear `manage.py apply_mpr_core_tables` (wrapper CLI, `--dry-run`, `--base-empresa`)
- [x] 1.4 Actualizar `docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md` § tablas Synap `mpr_*`
- [x] 1.5 Verificar DDL en BD dev: proveedor idempotente 2× sin error

---

## Phase 2: P1 — Repositorios y db

- [x] 2.1 Crear `mpr/db.py` (re-export `mysql_cursor`, `get_base_empresa_from_request`)
- [x] 2.2 Crear `mpr/repositories/config.py` (`mpr_config` singleton)
- [x] 2.3 Crear `mpr/repositories/envio_produccion.py`
- [x] 2.4 Crear `mpr/repositories/turno_roster.py`
- [x] 2.5 Crear `mpr/repositories/parte.py` (cabecera, línea, ajuste)
- [x] 2.6 Crear `mpr/repositories/transicion_lote.py`
- [x] 2.7 Crear `mpr/repositories/armado_surtido.py` + `imputacion.py`
- [x] 2.8 Añadir `MPR_LEDGER_BACKEND` en `settings.py` (`postgres`|`dual`|`mysql`)
- [x] 2.9 Tests repositorios envío/config + turno/parte/transición (`test_repositories_*.py`)

---

## Phase 3: P1 — Refactor services (dual-write)

- [x] 3.1 Refactor envío tablero: `enviar_a_produccion_lote`, `_query_enviado_tablero_componente`
- [x] 3.2 Refactor turnos/roster CRUD en `services.py`
- [x] 3.3 Refactor config: `obtener_config_mpr`, `actualizar_config_mpr_bloqueo_fabricando` → `mpr_config`
- [x] 3.4 Refactor transiciones: insert `mpr_transicion_lote` vía repo
- [x] 3.5 Refactor armado surtido + imputación 1ra
- [x] 3.6 Refactor trazabilidad: lectura partes/transiciones/armado desde repos MySQL
- [x] 3.7 Adaptador dual-write Postgres (solo si `MPR_LEDGER_BACKEND=dual`)
- [ ] 3.8 Marcar modelos `managed=False`; docstring `MprEmpresaConfig` → `MprConfig` (P3 cutover)

---

## Phase 4: P2 — Migración datos

- [x] 4.1 Comando `migrate_mpr_ledgers_to_mysql` (--empresa, --dry-run, orden FK)
- [x] 4.2 Mapeo UUID → `uuid_parte` / `uuid_ajuste` / `uuid_lote`
- [ ] 4.3 Test paridad conteos por entidad (Postgres vs MySQL)

---

## Phase 5: P3 — Cutover y limpieza

- [ ] 5.1 Actualizar tests E4–E8, turnos, transiciones, armado → fixtures MySQL
- [ ] 5.2 `MPR_LEDGER_BACKEND=mysql` en dev; suite `mpr` verde (`--keepdb`)
- [ ] 5.3 Migración Django DROP tablas Postgres MPR operativas
- [ ] 5.4 Actualizar docs: `ENVIO_PRODUCCION_TABLERO.md`, `PARTE_PRODUCCION.md`, `TURNOS_Y_ROSTER.md`
- [ ] 5.5 Documentar rollback en `docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md`

---

## Phase 6: P4 — mpr_evento (opcional post-P3)

- [ ] 6.1 DDL `mpr_evento` + proveedor catalog
- [ ] 6.2 Escritura eventos en envío/parte/transición/armado
- [ ] 6.3 `construir_trazabilidad_componente` + tests E8 trazabilidad

---

## Phase 7: P5 — Deprecación OPT (futuro)

- [ ] 7.1 Checklist lectores `lista_produccion_*` / columnas OPT
- [ ] 7.2 Freeze escrituras legacy OPT en código nuevo
- [ ] 7.3 Spec archive + docs deprecación

---

## Verify (cada fase)

- [ ] V1 P0: tablas existen en MySQL dev (`SHOW TABLES LIKE 'mpr_%'`)
- [ ] V2 P1: escenarios spec envío/parte/turnos contra MySQL
- [ ] V3 P3: `docker exec Synap_app python manage.py test mpr --keepdb --noinput` 0 fallos
