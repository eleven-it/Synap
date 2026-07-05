# Design: MPR fuente única en MySQL

## Technical Approach

Migrar ledgers MPR de Postgres (`default`) a tablas `mpr_*` en la BD MySQL de cada empresa, siguiendo el patrón **self-checkout**: DDL idempotente + proveedor catalog + repositorios SQL con `get_connection(base_empresa)`. Sin columna `base_empresa` en tablas. Cutover en 3 modos: solo Postgres → dual-write → solo MySQL.

Specs: `openspec/changes/mpr-mysql-fuente-unica/specs/`. Plan: `docs/mpr/PLAN_MIGRACION_MPR_MYSQL_FUENTE_UNICA.md`.

---

## Architecture Decisions

| Decisión | Alternativas | Elección | Rationale |
|----------|--------------|----------|-----------|
| Acceso datos | ORM Django alias `mysql`; raw en services | **`mpr/repositories/` + `mpr/db.py`** | BD cambia por sesión; pool ya resuelve `base_empresa` |
| Router Django | Extender `LegacyDbRouter` a `mpr` | **No extender** | `DATABASES.mysql.NAME` fijo ≠ BD empresa |
| PK ledgers | Mantener UUID Postgres | **`BIGINT AUTO_INCREMENT`** + UUID opcional migración | Alineado AdministraNET + spec |
| Config MPR | `mpr_empresa_config` + base_empresa | **`mpr_config` singleton** | Una BD = una empresa |
| FK físicas | Solo lógicas (self-checkout) | **FK entre `mpr_*` + catálogos InnoDB** | Producto pidió integridad referencial |
| Cutover | Big-bang | **Dual-write + flag settings** | Rollback sin pérdida |
| Modelos Django | Eliminar | **`managed=False` transitorio** | Documentación esquema hasta limpieza P3 |

---

## Data Flow

```
View (base_empresa sesión)
    → mpr/services.py
        → mpr/repositories/*.py
            → mysql_cursor(base_empresa)
                → mpr_* (ledger)
                → movimiento_stock / stock_deposito (físico, sin cambio)
```

Dual-write (P2): repositorio escribe MySQL; adaptador legacy opcional escribe Postgres si `MPR_LEDGER_BACKEND=dual`.

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `docs/mpr/sql/001_mpr_core_tables.sql` | Create | DDL utf8mb4, 13 tablas P0 |
| `core/services/legacy_mysql_schema/catalog.py` | Modify | `run_mpr_core_tables_mysql` + registry `mpr_core_tables` |
| `mpr/db.py` | Create | Re-export pool + `get_base_empresa_from_request` |
| `mpr/repositories/config.py` | Create | CRUD singleton `mpr_config` |
| `mpr/repositories/envio_produccion.py` | Create | Insert/list/sum envíos |
| `mpr/repositories/parte.py` | Create | Parte, líneas, ajustes |
| `mpr/repositories/turno_roster.py` | Create | Turnos + roster |
| `mpr/repositories/transicion_lote.py` | Create | Transiciones |
| `mpr/repositories/armado_surtido.py` | Create | Lote, movimiento, línea, packs habilitados |
| `mpr/repositories/imputacion.py` | Create | Imputación 1ra |
| `mpr/services.py` | Modify | Reemplazar ~40 `.objects` por repos |
| `mpr/management/commands/migrate_mpr_ledgers_to_mysql.py` | Create | Backfill Postgres→MySQL |
| `django_project/settings.py` | Modify | `MPR_LEDGER_BACKEND`: postgres \| dual \| mysql |
| `mpr/models.py` | Modify | `managed=False`; renombrar doc `MprConfig` |
| `docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md` | Modify | § tablas Synap `mpr_*` |
| `mpr/tests/test_*` | Modify | Fixtures MySQL; helper seed `mpr_*` |

P4: `001_mpr_evento.sql`, `repositories/evento.py`, trazabilidad componente.

---

## Interfaces / Contracts

```python
# mpr/repositories/envio_produccion.py
def crear_envio(conn, *, id_articulo: int, cantidad, id_usuario: int) -> int: ...
def sumar_envios_por_componente(base_empresa: str, comp_ids: list[int]) -> dict[int, Decimal]: ...

# mpr/repositories/config.py
def obtener_config(base_empresa: str) -> MprConfigDTO: ...
def guardar_config(base_empresa: str, *, bloquear_parte_supera_fabricando: bool) -> None: ...
```

Tipos: `administranet_types` en todo INSERT/SELECT legacy.

---

## Testing Strategy

| Layer | Qué | Cómo |
|-------|-----|------|
| Unit | Repositorios SQL | Mock cursor o BD test MySQL |
| Integration | Envío, parte, turnos, transición | Patrón `test_opt_flujo_mysql.py` |
| Regression | Tablero E7, parte E8, suite mpr | `docker exec Synap_app python manage.py test mpr --keepdb` |
| Migration | Paridad conteos | Command `--dry-run` + assert counts |

---

## Migration / Rollout

1. **P0**: DDL en staging; sin cambio runtime.
2. **P1–P2**: `MPR_LEDGER_BACKEND=dual`; comando migración histórico.
3. **P3**: `MPR_LEDGER_BACKEND=mysql`; DROP tablas Postgres vía migración Django.
4. **Rollback**: restaurar snapshot Postgres + `dual` o `postgres`.

---

## Open Questions

- [ ] FK estricta a `articulo.IDArt` en bases con engine mixto — pre-check en proveedor.
- [ ] `mpr_evento` en P0 DDL vacío vs P4 — **decisión: P4** (solo spec ADDED).
