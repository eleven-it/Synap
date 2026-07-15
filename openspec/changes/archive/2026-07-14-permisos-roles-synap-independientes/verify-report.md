# Informe de verificación

**Change:** `permisos-roles-synap-independientes`  
**Versión:** N/A  
**Modo:** Standard (sin Strict TDD)  
**Fecha:** 14/07/2026  
**Verificador:** sdd-verify (subagente)

---

## Completitud

| Métrica | Valor |
|--------|-------|
| Tareas totales (implementación) | 38 |
| Tareas completadas | 38 |
| Tareas incompletas | 0 |
| Criterios de aceptación (CA-1…CA-7) | 7/7 |

Todas las tareas marcadas `[x]`, incluyendo **3.7** (cutover `SOURCE=synap` en `.env`), **4.2** (retiro `sync_permisos_synap.py`), **4.3** (`SYNAP_AUTO_SYNC_PERMISSIONS=False` por defecto) y **4.4** (purge local ejecutado; remoto pendiente de conectividad).

---

## Ejecución de build y tests

**Build:** ➖ No configurado en `openspec/config.yaml` (proyecto Django; sin paso de build obligatorio).

**Tests:** ✅ 13 passed / ❌ 0 failed / ⚠️ 0 skipped

```bash
docker exec Synap_app python manage.py test \
  core.tests.test_synap_permisos \
  core.tests.test_permisos_puesto_supervisor --keepdb
```

```
Ran 13 tests in 95.242s
OK
```

**Cobertura:** ➖ No disponible (sin umbral configurado).

---

## Comprobaciones operativas P3

| Check | Resultado | Evidencia |
|-------|-----------|-----------|
| `sync_permisos_synap.py` eliminado | ✅ | `glob **/sync_permisos_synap.py` → 0 archivos |
| `sync_synap_permissions_to_adminet` eliminado | ✅ | `glob **/sync_synap_permissions_to_adminet.py` → 0 archivos |
| `SYNAP_AUTO_SYNC_PERMISSIONS` default `False` | ✅ | `django_project/settings.py:448` → `default=False` |
| `.env` local `SYNAP_PERMISOS_SOURCE=synap` | ✅ | `.env:56` |
| `.env` local `SYNAP_AUTO_SYNC_PERMISSIONS=False` | ✅ | `.env:62` |
| Purge legacy grupo Synap (local) | ✅ | Ejecutado en BD `administranet` (tarea 4.4) |
| Purge legacy remoto `192.168.0.2` | ⚠️ Pendiente | MySQL remoto inalcanzable en entorno de verificación |

---

## Matriz de cumplimiento de specs (validación conductual)

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| Fuente de verdad runtime | Flag legacy mantiene comportamiento | `test_synap_permisos > test_source_legacy` | ✅ COMPLIANT |
| Fuente de verdad runtime | Flag synap con datos completos | `test_synap_permisos > test_source_synap_solo_store` | ✅ COMPLIANT |
| Fuente de verdad runtime | Flag synap sin mapeo (sin fallback) | `test_synap_permisos > test_source_synap_sin_permisos_no_usa_permiso_sistema` | ✅ COMPLIANT |
| Fuente de verdad runtime | Flag dual unión | `test_synap_permisos > test_source_dual_union` | ✅ COMPLIANT |
| Paridad permisos efectivos | Supervisor acceso total | `test_synap_permisos > test_supervisor_cod_usuario_acceso_total` | ✅ COMPLIANT |
| Paridad permisos efectivos | Nombre puesto supervisor + Reports | `test_synap_permisos > test_nombre_puesto_supervisor_agrega_reports` | ✅ COMPLIANT |
| Lecturas complementarias | Clavemenu siempre sumados | `test_synap_permisos > test_complementarios_clavemenu_siempre_sumados` | ✅ COMPLIANT |
| Seed catálogo | Keys únicas y comodines | `test_synap_permisos > test_catalogo_keys_unicas_y_comodines` | ✅ COMPLIANT |
| Ancla fija idpuesto | crear_puesto bloqueado | `test_synap_permisos > test_crear_puesto_bloqueado_lanza_excepcion` | ✅ COMPLIANT |
| Gestión /core/permisos-puesto/ | Lista rechaza no supervisor | `test_permisos_puesto_supervisor > test_lista_rechaza_no_supervisor` | ✅ COMPLIANT |
| Gestión /core/permisos-puesto/ | Lista OK supervisor | `test_permisos_puesto_supervisor > test_lista_ok_supervisor` | ✅ COMPLIANT |
| Gestión /core/permisos-puesto/ | Gestionar OK con SynapPermisosService | `test_permisos_puesto_supervisor > test_gestionar_ok_supervisor` | ✅ COMPLIANT |
| Esquema synap_* — Tablas | Tablas sin FK a VB6 | (ninguno) | ⚠️ PARTIAL — evidencia estática DDL/SQL |
| Despliegue DDL idempotente | Re-ejecución sin fallo | (ninguno) | ⚠️ PARTIAL — verificado manualmente P0 (tarea 1.9) |
| Backfill idempotente | Preserva permisos activos | (ninguno) | ⚠️ PARTIAL — verificado manualmente P1 (tarea 2.10) |
| Prohibición escritura VB6 | Login sin inyección legacy | (ninguno) | ⚠️ PARTIAL — código retirado; sin test E2E login |
| Operaciones UI synap_* | Toggle permiso Synap | (ninguno) | ⚠️ PARTIAL — mock en vista gestionar |
| Roles independientes idpuesto | Creación rol sin puesto legacy | (ninguno) | ⚠️ PARTIAL — diseño rol dedicado por puesto |
| Mapeo idpuesto → synap_rol | Mapeo válido / rechazado | (ninguno) | ⚠️ PARTIAL — validación en servicio, sin test unitario |
| Cardinalidad múltiple rol | Puesto con múltiples roles | (ninguno) | ⚠️ PARTIAL — modelo soporta; UI rol dedicado |

**Resumen de cumplimiento conductual:** 12/12 escenarios con test automatizado pasaron. 8 escenarios adicionales cubiertos por evidencia estática o verificación manual documentada en `tasks.md`.

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| Esquema `synap_*` (4 tablas) | ✅ Implementado | `core/sql/001_synap_permisos_tables.sql`, `catalog.py` |
| Proveedor DDL idempotente | ✅ Implementado | `synap_permisos_tables` en `PROVIDER_REGISTRY` |
| Seed desde `PERMISOS_POR_MODULO` | ✅ Implementado | `core/services/synap_permisos_seed.py` |
| Backfill legacy → synap_* | ✅ Implementado | `backfill_synap_permisos_from_legacy.py` |
| Fachada `get_permisos_totales_administranet` | ✅ Implementado | Ramas legacy/synap/dual en `administranet_permisos_usuario.py` |
| `SynapPermisosService` (UI) | ✅ Implementado | `core/services/synap_permisos.py` |
| Retiro sync legacy | ✅ Implementado | Archivos eliminados; referencias solo en docs históricos |
| Purge grupo Synap | ✅ Implementado | `purge_synap_legacy_permisos.py` |
| Bloqueo `crear_puesto` | ✅ Implementado | `CreacionPuestoBloqueadaError` + flag settings |
| Documentación | ✅ Actualizada | 4 docs en `docs/general/` |

---

## Coherencia (diseño)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| `synap_*` en MySQL por empresa | ✅ Sí | |
| Rol por puesto (`idpuesto` ancla) | ✅ Sí | Rol dedicado por puesto en UI P2 |
| Charset latin1 | ✅ Sí | DDL |
| Sin FK a `puestos` | ✅ Sí | |
| Cutover flag legacy→dual→synap | ✅ Sí | `.env` en `synap` |
| Escritura UI solo `synap_*` | ✅ Sí | `views_permisos_puesto.py` refactorizado |
| Retiro `sync_permisos_synap` P3 | ✅ Sí | Archivo eliminado |
| Roles compartidos en UI | ⚠️ N/A | Decisión: rol dedicado por puesto (design open question cerrada) |

---

## Issues encontrados

**CRITICAL** (bloquean archivo):
- Ninguno.

**WARNING** (no bloquean):
- Purge remoto MySQL (`192.168.0.2`) pendiente por conectividad; ejecutar `purge_synap_legacy_permisos --ejecutar` cuando el host sea alcanzable.
- Referencias históricas a `sync_permisos_synap` / `sync_synap_permissions_to_adminet` en docs secundarios (`ANALISIS_FORMULARIOS_STOCK`, `PLAN_MODULO_LOGISTICA`, `GUIA_IMPLEMENTACION_SERVIDOR_STAGING`, etc.) — no afectan runtime.
- `self_checkout.tests.test_permissions`: 4 fallas preexistentes (302 auth), ajenas a este change.
- 8 escenarios de spec sin test automatizado dedicado (cubiertos por verificación manual P0–P2).

**SUGGESTION** (mejoras):
- Añadir tests de integración MySQL para backfill y purge cuando BD dev esté disponible en CI.
- Actualizar docs secundarios que aún mencionan comandos sync retirados.

---

## Veredicto

**PASS WITH WARNINGS**

Implementación completa y coherente con diseño y specs. Suite objetivo (13 tests) verde. Retiro de sync legacy confirmado. Cutover local `SYNAP_PERMISOS_SOURCE=synap` activo. Purge local ejecutado; purge remoto diferido por conectividad a `192.168.0.2`.
