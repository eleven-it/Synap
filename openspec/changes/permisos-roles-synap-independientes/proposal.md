# Propuesta — Permisos y roles Synap independientes de AdministraNET

**Cambio:** `permisos-roles-synap-independientes`  
**Fecha:** 08/07/2026  
**Modo:** Evolution Mode (nueva persistencia; auth y Clavemenu legacy preservados)  
**Referencias:** `docs/general/APPS_CORE_Y_PERMISOS_ADMINISTRANET.md`, `SYNC_PERMISOS_SYNAP.md`, `PERMISOS_ASIGNACION_POR_PUESTO_SUPERVISOR.md`

---

## 1. Intención

Independizar permisos y roles de Synap de tablas **compartidas con VB6** (`permiso_sistema`, `permiso_sistema_puesto`). Synap MUST NOT escribir en esas tablas. `idpuesto` legacy = **ancla fija**; MUST NOT crear puestos en `puestos`.

---

## 2. Problema

| Hoy | Problema |
|-----|----------|
| `sync_permisos_synap.py` INSERT en `permiso_sistema` | Contamina catálogo VB6 del supervisor |
| `administranet_puestos.py` MAX(idpuesto)+1 | Mezcla roles dinámicos con IDs reservados |
| Runtime vía JOIN legacy | VB6 escribe activamente (`CargaPuesto.frm`, `Funciones.bas`, etc.) |

---

## 3. Alcance

### Incluido (P0–P3)

| Fase | Entregable |
|------|------------|
| **P0** | DDL `synap_permiso`, `synap_rol`, `synap_rol_permiso`, `synap_puesto_rol` en `catalog.py` + provider; seed desde `PERMISOS_POR_MODULO` |
| **P1** | Dual-read + backfill grupo 'Synap'; flag `SYNAP_PERMISOS_SOURCE=synap\|legacy` |
| **P2** | Cutover `get_permisos_totales_administranet`; UI `/core/permisos-puesto/` → `synap_*` |
| **P3** | Retirar `sync_permisos_synap`; limpiar filas grupo 'Synap'; prohibir nuevos `idpuesto`; docs |

### Fuera de alcance

- Migración VB6; lectura legacy `permisos` (Clavemenu) y `permisos_sistema` (TPV)
- Cambio login (`AdministraNETAuth`); DB central Synap (Opción B descartada)

---

## 4. Capabilities

### New

| Capability | Descripción |
|------------|-------------|
| `permisos-synap-store` | Esquema `synap_*`, catálogo, seed, backfill, runtime + flag |
| `roles-synap-por-puesto` | Roles dinámicos y mapeo `idpuesto` → `synap_rol` (sin FK VB6) |

### Modified

None — sin spec previa de permisos en `openspec/specs/`.

---

## 5. Enfoque (Opción A)

Tablas `synap_*` en MySQL por empresa vía `catalog.py`. Runtime: `synap_puesto_rol → synap_rol_permiso → synap_permiso`. Se conserva lectura `permisos` y `permisos_sistema`.

---

## 6. Áreas afectadas

| Área | Impacto |
|------|---------|
| `core/services/legacy_mysql_schema/catalog.py` | New — provider DDL |
| `core/services/administranet_permisos_usuario.py` | Modified — fuente verdad |
| `core/services/sync_permisos_synap.py` | Deprecated P3 |
| `core/services/administranet_puestos.py` | Modified — no nuevos idpuesto |
| `core/middleware/`, `context_processors.py`, `decorators.py`, `utils/permissions.py`, `self_checkout/permissions.py` | Modified |
| `/core/permisos-puesto/`, `core/constantes_permisos.py`, `docs/general/` | Modified |

---

## 7. Riesgos y rollback

| Riesgo | Mitigación |
|--------|------------|
| Divergencia dual-read | Flag + backfill idempotente + tests paridad |
| DDL por empresa | Provider idempotente en bootstrap/comando global |

**Rollback:** `SYNAP_PERMISOS_SOURCE=legacy`; DDL sin DROP; no borrar legacy hasta P3.

---

## 8. Criterios de éxito

- [ ] Synap deja de escribir en `permiso_sistema`/`permiso_sistema_puesto`
- [ ] Permisos/roles en `synap_*`; paridad por usuario (tests)
- [ ] `docker exec Synap_app python manage.py test` verde
- [ ] Docs actualizadas

---

*Listo para **spec** y **design** (paralelo).*
