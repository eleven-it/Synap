# Propuesta — Auditoría y recálculo de imputación contable

**Cambio:** `contabilidad-auditoria-recalculo`  
**Fecha:** 18/07/2026  
**Exploración:** [exploration.md](./exploration.md)  
**Fuentes:** `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md` (50 hallazgos), `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md`

---

## Intent

Construir en Synap un sistema de **auditoría en solo lectura** sobre las imputaciones contables del MySQL legacy (tablas `cont_*`), mapeando los 50 hallazgos VB6, y habilitar después un **recálculo/corrección controlada** con dry-run, backup y trazabilidad. Regla de oro: *lectura primero, corrección después*. Paridad de datos/negocio con VB6; la UX puede divergir siguiendo el canon de reportes.

---

## Scope

### In scope

| Fase | Entregable |
|------|------------|
| **F1 (prioritaria)** | App `contabilidad_audit`: registry de checks deterministas (`SELECT`), políticas por empresa, tablero canon, export, tests |
| **F2** | Dry-run del recompute (plan de cambios sin escritura) |
| **F3** | `legacy_db/services/cont_recalculo_service.py`: apply transaccional, backup, log, concurrencia; solo con permiso + `ENVIRONMENT=production` |

Checks núcleo (14): `asiento_balanceado`, `saldo_ejercicio_vs_diario`, `saldo_periodo_vs_diario`, `cuentas_sin_fila_saldo`, `imputacion_a_no_imputable`, `concepto_anulacion_incoherente`, `nro_asiento_duplicado`, `codigo_movimiento_huerfano`, `fecha_fuera_de_periodo`, `periodos_solapados`, `cierre_resultado_no_cero`, `reparto_cc_incompleto`, `rei_recalculo`, `concepto_no_normal`.

### Out of scope

- Modificar código VB6 o formularios `Cont_*`.
- Auto-corrección de cierres PyG/PN ya cerrados (solo marca para revisión manual).
- Cambios de esquema legacy salvo tabla de log vía `catalog.py` (F3, aprobación aparte).
- Pantallas de referencia excluidas (`ventas/objetivos`, `ventas/presupuestos`).

---

## Capabilities (contrato para sdd-spec)

### New Capabilities

| Capability | Descripción |
|------------|-------------|
| `contabilidad-auditoria-lectura` | Catálogo de checks read-only sobre `cont_asiento` y tablas derivadas; `AuditResult` estándar; drill-down; ejecución por empresa/ejercicio/periodo |
| `contabilidad-politicas-configurables` | Modelo `PoliticaAuditoriaContable` en DB Synap; resolución `default → override base_empresa`; snapshot `config_hash` por corrida |
| `contabilidad-recalculo-correccion` | Motor dry-run + apply en `legacy_db`; backup por tabla; transacción única; log `cont_audit_correccion`; orden seguro de ejecución; idempotencia |

### Modified Capabilities

**None** — no existe spec OpenSpec previa para `legacy_db` ni imputaciones contables.

---

## Approach

1. **Auditoría:** app `contabilidad_audit/services/` con registry `CHECKS`; conexión vía `get_mysql_pool()` (patrón `reports/services/reconciliation_*`); tipos con `administranet_types`.
2. **Políticas:** parámetros §8 arquitectura (`tratamiento_anulados`, `politica_centavo`, `prefijos_cuenta`, `ejercicios_cerrados`, `alcance_recompute`, `tolerancia_decimal`); cada corrida persiste `config_hash`.
3. **UI:** `/contabilidad/auditoria/` con tablero verde/rojo, filtros y export; plantillas `reports/dashboard_detail.html` + includes.
4. **Corrección:** servicio en `legacy_db`; dry-run obligatorio; apply solo tras aprobación explícita; recompute maestro desde `cont_asiento` (fuente de verdad) hacia `cont_*_saldo_cta`.
5. **Iteración SDD:** I0–I2 (F1) → I3 (dry-run) → I4–I5 (apply + rollback lote).

---

## Affected Areas

| Área | Rutas |
|------|-------|
| Nueva app | `contabilidad_audit/` (models, services, views, urls, templates) |
| Escritura legacy | `legacy_db/services/cont_recalculo_service.py` |
| Config Django | `django_project/settings.py` (`INSTALLED_APPS`) |
| Conexión | `reports/services/connection_pool.py` |
| DDL log (F3) | `core/services/legacy_mysql_schema/catalog.py` |
| UI canon | `reports/dashboard_detail.html`, `reports/includes/` |
| Docs | `docs/general/` (spec funcional del módulo) |

---

## Risks

| Riesgo | Mitigación |
|--------|------------|
| Criterio de anulados/centavo no consensuado | Políticas configurables + validación con área contable antes de F3 |
| Prefijos de cuenta incorrectos por empresa | Mapping configurable; validar contra plan real |
| `alcance_recompute=historico` — performance | Lotes por ejercicio; ejecución fuera de horario |
| Escritura concurrente con VB6 | Detección de concurrencia + locking pesimista en contadores |
| Implicancia fiscal en ejercicios cerrados | Default `no_tocar`; permiso reforzado si `permitir_con_reapertura` |

---

## Rollback Plan

| Fase | Rollback |
|------|----------|
| F1 (auditoría) | Desinstalar app / feature flag; cero escritura legacy → trivial |
| F3 (corrección) | Backup previo `*_bkp_<timestamp>` por tabla; reversión por `lote_id` desde log |

---

## Dependencies

- Pool MySQL multi-empresa operativo (`get_mysql_pool`).
- App `legacy_db` y tipos `administranet_types`.
- Permisos Synap dedicados (lectura vs corrección).
- Validación contable de políticas default antes de producción.

---

## Success Criteria

- [ ] ≥14 checks ejecutables vía registry para un `base_empresa` y ejercicio dado.
- [ ] Tablero lista cuentas con `|saldo_derivado − saldo_diario| > tolerancia` con drill-down al comprobante.
- [ ] Cada corrida de auditoría registra `config_hash` reproducible.
- [ ] Dry-run genera plan de cambios sin ninguna escritura MySQL.
- [ ] Tras apply (piloto): `saldo_*_vs_diario` en verde e idempotente; backup + log reversibles.
- [ ] Tests en contenedor: `docker exec Synap_app python manage.py test contabilidad_audit`.

---

*Listo para **sdd-spec** y **sdd-design** (paralelo).*
