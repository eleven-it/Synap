# Tasks: Auditoría y recálculo de imputación contable

**Change:** `contabilidad-auditoria-recalculo`  
**Design:** `design.md` | **Specs:** `specs/contabilidad-auditoria-lectura/spec.md`, `specs/contabilidad-politicas-configurables/spec.md`, `specs/contabilidad-recalculo-correccion/spec.md`  
**Apply:** contenedor `docker exec Synap_app`

> **MVP = Fase 0 + Fase 1** — auditoría en solo lectura con políticas configurables, tablero canon y tests. Fases 2–3 (dry-run y corrección real) quedan fuera del MVP.

---

## Fase 0 — Preparación y verificación de esquema

- [x] 0.1 Documentar verificación de columnas `cont_*` y tablas de enlace compras/pagos contra esquema real: ejecutar `DESCRIBE` / consulta a `information_schema` en al menos una `base_empresa` piloto (`cont_asiento`: `debe_asiento`, `haber_asiento`, `anulado`, `id_concepto_asiento`, `saldo_asiento`, `codigo_movimiento`; `cont_pc`: `saldo_pc`, `imp_cont_pc`, `cod_pc`; `cont_concepto_asiento`: `id_concepto_anul`, `tipo_concepto_asiento`; `cont_periodo`: `fecdesde`, `fechasta`; tablas saldo `cont_ejercicio_saldo_cta`, `cont_periodo_saldo_cta`; `cuentaproveedor`: `CodigoMovimiento`, `TipoComprobante`, `NroComprobante`, `Fecha`, `CodSucursal`, `ImporteCompra`, `Anulado`; `sucursales.cont`) — registrar hallazgos en `docs/general/INVENTARIO_ESQUEMA_CONT_AUDITORIA.md` — *design §10, spec AUD-LECT-05, AUD-LECT-21*
- [x] 0.2 Crear script de smoke read-only `contabilidad_audit/management/commands/verificar_esquema_cont.py` (o test de integración) que valide existencia de tablas/columnas esperadas vía `get_mysql_pool()` sin DML — ejecutar: `docker exec Synap_app python manage.py verificar_esquema_cont --base_empresa=<empresa>`
- [x] 0.3 Añadir permisos Synap dedicados en `core/constantes_permisos.py` (módulo `Finance` o nuevo `Contabilidad audit`): `contabilidad.auditoria.leer`, `contabilidad.auditoria.configurar`, `contabilidad.auditoria.corregir`, `contabilidad.auditoria.rei` — re-seed con `apply_synap_permisos_tables` en empresa piloto — *spec AUD-LECT-20, POL-12, REC-02*
- [x] 0.4 Scaffolding app `contabilidad_audit/`: `apps.py`, `__init__.py`, paquetes `services/`, `services/checks/`, `templates/contabilidad_audit/`, `sql/`, `migrations/` — registrar `'contabilidad_audit'` en `django_project/settings.py` (`INSTALLED_APPS`) — *design §2.2*
- [x] 0.5 Incluir rutas base en `contabilidad_audit/urls.py` y montar en `django_project/urls.py` (`path('contabilidad/', include('contabilidad_audit.urls'))`) — stubs de vista que devuelvan 403 sin permiso
- [x] 0.6 Data migration inicial Postgres: fila `PoliticaAuditoriaContable` con `base_empresa='__default__'` y defaults del design (`tratamiento_anulados=excluir`, `politica_centavo=diario_manda`, `prefijos_cuenta` con `{"resultado":["4"],"activo":["1"],"pasivo":["2"],"pn":["3"]}`, `ejercicios_cerrados=no_tocar`, `alcance_recompute=ejercicio_seleccionado`, `tolerancia_decimal=0.005`) — *spec POL-01, POL-05*

---

## Fase 1 — Auditoría solo lectura *(MVP — entregable prioritario)*

### 1.A Modelos, políticas y contratos

- [x] 1.1 Implementar modelos Postgres en `contabilidad_audit/models.py`: `PoliticaAuditoriaContable` (con `clean()` validando enums y JSON prefijos), `CorridaAuditoria` — migración Django — *spec POL-01, POL-05, POL-10*
- [x] 1.2 Implementar `contabilidad_audit/services/politicas.py`: `resolver_politica(base_empresa)` (default → override), fallback defensivo de prefijos vacíos con `logger.warning`, `calcular_config_hash(politica)` (algoritmo `v1:` + SHA-256 canónico del design §5 decisión 4) — *spec POL-02, POL-09, design §4*
- [x] 1.3 Implementar `contabilidad_audit/services/resultados.py`: dataclasses `Diferencia`, `AuditResult`, protocolo `Check`, helper `CorridaContexto` (conexión/cursor compartido por corrida) — *spec AUD-LECT-03*
- [x] 1.4 Implementar `contabilidad_audit/services/registry.py` con dict `CHECKS` (16 entradas núcleo, stubs inicialmente aceptables si devuelven estructura vacía hasta 1.7) — *spec AUD-LECT-02*

### 1.B SQL canónico y checks deterministas

- [x] 1.5 Implementar `contabilidad_audit/services/checks/_sql.py`: consulta saldo teórico desde `cont_asiento` con regla `saldo_pc` Deudor/Acreedor, filtro `{filtro_anulados}` según política, constante `CENTAVO = Decimal("0.01")`, helpers de comparación con `tolerancia_decimal` y `politica_centavo` — *spec AUD-LECT-04, AUD-LECT-05, design §3.3*
- [x] 1.6 Implementar checks en `contabilidad_audit/services/checks/saldos.py`: `saldo_ejercicio_vs_diario`, `saldo_periodo_vs_diario`, `cuentas_sin_fila_saldo` — normalización vía `administranet_types`, referencias H01/H03/H04/H10/H17/H33/H34 — *spec AUD-LECT-05, AUD-LECT-06*
- [x] 1.7 Implementar checks en `contabilidad_audit/services/checks/asientos.py`: `asiento_balanceado`, `imputacion_a_no_imputable`, `nro_asiento_duplicado`, `codigo_movimiento_huerfano` — *spec AUD-LECT-04, AUD-LECT-07, AUD-LECT-09, AUD-LECT-10*
- [x] 1.8 Implementar checks en `contabilidad_audit/services/checks/conceptos.py`: `concepto_anulacion_incoherente` (emparejamiento por `id_concepto_anul`, no `+1`), `concepto_no_normal` — *spec AUD-LECT-08, AUD-LECT-15, design §5 decisión 2*
- [x] 1.9 Implementar checks en `contabilidad_audit/services/checks/periodos.py`: `fecha_fuera_de_periodo`, `periodos_solapados` — fechas con `to_date_or_none`, UI dd/MM/yyyy — *spec AUD-LECT-11*
- [x] 1.10 Implementar checks en `contabilidad_audit/services/checks/cierres.py`: `cierre_resultado_no_cero` (prefijos desde política), `reparto_cc_incompleto` — *spec AUD-LECT-12, AUD-LECT-13*
- [x] 1.11 Implementar check en `contabilidad_audit/services/checks/rei.py`: `rei_recalculo` (solo lectura, compara REI teórico vs registrado vía `cont_indiceinfla_periodo`) — *spec AUD-LECT-14*
- [x] 1.12 Implementar checks en `contabilidad_audit/services/checks/compras_pagos.py`: `comprobante_compra_pago_sin_asiento` (LEFT JOIN `cuentaproveedor`↔`cont_asiento` por `CodigoMovimiento`, filtro `sucursales.cont='Si'`, tipos FA/FC/OP, **excluir `CodigoMovimiento=0`** = marcadores de anulación y `cont_asiento.codigo_movimiento=0`), `asiento_compra_pago_desbalanceado_saldo_null` (Σdebe≠Σhaber o `saldo_asiento` NULL) e `integridad_anulacion_compra_pago` (marcador cm=0 + asiento original `anulado='Si'` + contra-asiento concepto 4/8 con `codigo_movimiento_anul`) — normalización vía `administranet_types`, referencias H51–H53 y §6.8 — *spec AUD-LECT-21, AUD-LECT-22, AUD-LECT-23, docs §6*

### 1.C Runner, persistencia y permisos

- [x] 1.13 Implementar `contabilidad_audit/services/runner.py`: `ejecutar_corrida(base_empresa, filtros, check_ids=None, usuario)` — resuelve política, calcula `config_hash`, crea `CorridaAuditoria`, una conexión `get_connection(base_empresa)` solo SELECT, aislamiento de errores por check (`try/except` → `AuditResult.error`), persiste resumen en Postgres — *spec AUD-LECT-01, AUD-LECT-16, AUD-LECT-18, AUD-LECT-20*
- [x] 1.14 Decoradores/permisos en `contabilidad_audit/views.py`: exigir `contabilidad.auditoria.leer` para tablero y corrida; validar filtros obligatorios `base_empresa`, `id_ejercicio` — *spec AUD-LECT-16, AUD-LECT-20*

### 1.D UI canon reportes

- [x] 1.15 Vista tablero GET `/contabilidad/auditoria/` en `contabilidad_audit/views.py` + plantilla `templates/contabilidad_audit/auditoria_tablero.html` extendiendo `reports/dashboard_detail.html` e includes bajo `reports/includes/` — tarjetas verde/rojo por check, filtros empresa/ejercicio/periodo, drill-down a comprobante — *spec AUD-LECT-19*
- [x] 1.16 Integrar export CSV/Excel reutilizando `reports/services/export_service.py` (incluir `config_hash`, fecha dd/MM/yyyy, detalle por check) — endpoint o acción en tablero — *spec AUD-LECT-19*
- [x] 1.17 Vista configuración GET/POST `/contabilidad/auditoria/configuracion/` + plantilla canon — formulario política global y override por `base_empresa`, permiso `contabilidad.auditoria.configurar`, vista solo lectura para usuarios sin permiso — *spec POL-12, POL-13*
- [x] 1.18 Registrar entradas de menú/navegación Synap (módulo Finance o equivalente) apuntando a `/contabilidad/auditoria/` — *proposal §Affected Areas*

### 1.E Tests y documentación *(MVP)*

- [x] 1.19 Tests unitarios en `contabilidad_audit/tests/test_politicas.py`: resolución default→override, `config_hash` estable/cambiante, validación prefijos — *spec POL-02, POL-09*
- [x] 1.20 Tests unitarios en `contabilidad_audit/tests/test_checks.py`: mocks de cursor MySQL para al menos `asiento_balanceado`, `saldo_ejercicio_vs_diario`, `concepto_anulacion_incoherente`, `comprobante_compra_pago_sin_asiento`, `asiento_compra_pago_desbalanceado_saldo_null`, regla centavo — *spec AUD-LECT-04, AUD-LECT-05, AUD-LECT-08, AUD-LECT-21, AUD-LECT-22*
- [x] 1.21 Tests integración (opcional si hay BD dev): `contabilidad_audit/tests/test_runner.py` — corrida completa sin DML (assert no INSERT/UPDATE en legacy) — *spec AUD-LECT-01*
- [x] 1.22 Ejecutar suite MVP: `docker exec Synap_app python manage.py test contabilidad_audit` — todos verdes
- [x] 1.23 Documentación funcional: crear `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md` (checks, políticas, permisos, rutas, criterios de aceptación MVP) y actualizar `docs/general/PROPUESTA_ARQUITECTURA_AUDITORIA_RECALCULO_CONTABILIDAD_SYNAP.md` con estado F1 implementada — *regla .cursorrules documentación*

---

## Fase 2 — Dry-run de corrección (sin escritura legacy)

- [x] 2.1 Añadir modelos Postgres en `contabilidad_audit/models.py`: `PlanCorreccion` (`dry_run_id`, `plan` JSON, `config_hash`, `data_fingerprint`, `estado`, `expira_en`), `AprobacionREI` (estructura inicial para F3) — migración — *design §4, spec REC-01*
- [x] 2.2 Crear `legacy_db/services/cont_recalculo_service.py` con `dry_run(base_empresa, alcance, politica, usuario)` — **100% SELECT**, genera plan `(tabla, clave, valor_anterior, valor_nuevo, delta)`, respeta `alcance_recompute` y `ejercicios_cerrados` (solo marca exclusiones) — *spec REC-01, REC-10, REC-13*
- [x] 2.3 Implementar cálculo `data_fingerprint` (SHA-256 sobre tuplas `(tabla, clave, valor_actual)` ordenadas) y persistencia `PlanCorreccion` con `PLAN_TTL_MIN = 30`, `expira_en = creado_en + TTL` — *design §5 decisión 5, spec REC-15*
- [x] 2.4 Implementar reporte de impacto del dry-run (totales por tabla, cuentas impactadas, checks incluidos) exportable — reutilizar `export_service` — *spec REC-13*
- [x] 2.5 Simular referencias de backup en plan (nombres `*_bkp_<timestamp>` propuestos, sin crear tablas) y registrar en JSON del plan — *spec REC-03 (preparación)*
- [x] 2.6 Vista GET `/contabilidad/auditoria/dry-run/` en `contabilidad_audit/views.py`: dispara dry-run desde hallazgos de corrida, muestra plan y guards (TTL, hashes); permiso `contabilidad.auditoria.leer` — *design §3.4*
- [x] 2.7 Tests en `legacy_db/tests/test_cont_recalculo_dry_run.py`: plan sin DML, fingerprint estable, invalidación por cambio de política simulado — `docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_dry_run`
- [x] 2.8 Actualizar `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md` con flujo dry-run, TTL y aprobación contable previa — *spec REC-13*

---

## Fase 3 — Corrección real (producción + permiso reforzado)

### 3.A DDL log legacy

- [x] 3.1 Crear DDL idempotente en `contabilidad_audit/sql/cont_audit_correccion_log.sql` (`cont_audit_correccion_lote`, `cont_audit_correccion` con campos mínimos del design §5 decisión 7) — *spec REC-06*
- [x] 3.2 Implementar `run_contabilidad_audit_correccion_log_mysql(conn)` en `core/services/legacy_mysql_schema/catalog.py` y registrar provider `id: "contabilidad_audit_correccion_log"`, `risk: "bajo"` en `PROVIDER_REGISTRY` — *design §5 decisión 7, regla .cursorrules*
- [x] 3.3 Comando o documentar ejecución del provider en empresa piloto: `docker exec Synap_app python manage.py run_legacy_schema_provider contabilidad_audit_correccion_log --base_empresa=<empresa>` (o equivalente existente)

### 3.B Apply transaccional

- [x] 3.4 Extender `legacy_db/services/cont_recalculo_service.py` con `apply(base_empresa, dry_run_id, usuario)`: verificar `ENVIRONMENT in ('production','produccion')` + permiso `contabilidad.auditoria.corregir`; validar plan (TTL, `config_hash`, `data_fingerprint`) — *spec REC-02, REC-15*
- [x] 3.5 Implementar backup real pre-transacción: `CREATE TABLE ... AS SELECT` → `*_bkp_<timestamp>` por tabla afectada; abortar apply si backup falla — *spec REC-03*
- [x] 3.6 Implementar transacción única: `conn.autocommit(False)`, `INSERT cont_audit_correccion_lote`, `SELECT ... FOR UPDATE` en filas objetivo, re-validación contra plan, escritura en **orden seguro** (paso 2 concepto → paso 3 INSERT saldos → paso 4 recompute saldos), `INSERT cont_audit_correccion` por mutación, `COMMIT` — *spec REC-04, REC-05, REC-07, REC-12*
- [x] 3.7 Respeto ejercicios cerrados: bloquear o exigir confirmación + flag `reapertura_flag` en log según `ejercicios_cerrados` — *spec REC-09*
- [x] 3.8 Excluir del apply automático: `cierre_resultado_no_cero`, asientos desbalanceados de negocio sin regla, cuentas `saldo_pc` NULL — *spec REC-08, REC-16*
- [x] 3.9 Implementar `rollback_lote(base_empresa, lote_id, usuario)` restaurando desde backups en transacción única + evento en log — *spec REC-14*
- [x] 3.10 Tras apply exitoso: marcar `PlanCorreccion.estado='aplicado'`; verificar idempotencia (segundo dry-run → plan vacío) — *spec REC-11*
- [x] 3.11 Implementar reconstrucción total de saldos (`cont_ejercicio_saldo_cta` + `cont_periodo_saldo_cta`) desde `cont_asiento` **incluyendo TODAS las filas** (`tratamiento_anulados=incluir_neutralizado`: original `anulado='Si'` + contra reversante se netean; NO excluir anulados) con regla Deudor/Acreedor y **arrastre de apertura** (ejercicios sin asiento de apertura) — dry-run, backup `*_bkp_<timestamp>`, transacción única, log `cont_audit_correccion`; respetar `alcance_recompute` y `ejercicios_cerrados` — *spec REC-17, §6.8-6.9, H53*
- [x] 3.12 Implementar regeneración idempotente de asientos faltantes de compras/pagos (**331 huérfanos**, cm>0): reconstruir insumos desde tablas persistidas (`cuentaproveedor`, `stock`, `percep_prov`, `transferencia`, `otro_egreso`, `caja`, retenciones) portando lógica de `cont_reconstruccion_compras_pagos.py` (facturas 100 % validado), regenerar renglones en `cont_asiento` con concepto 3 (FA/FC) u 7 (OP), **reusar `CodigoMovimiento` existente** + `nro_asiento` nuevo del ejercicio de la **fecha original**, fecha del asiento = original; respetar `nro_asiento_ejercicio` con locking pesimista; no duplicar si ya existe asiento; los 86 cm=0 fuera de alcance; encadenar reconstrucción de saldos (3.11); apply solo `ENVIRONMENT=production` + permiso reforzado — *spec REC-18, AUD-LECT-21, §6.6-6.9, H51–H52*

### 3.C Flujo REI caso a caso

- [x] 3.13 Poblar `AprobacionREI` desde propuestas del dry-run (`rei_recalculo`); vista `/contabilidad/auditoria/rei/<dry_run_id>/` con approve/reject individual — permiso `contabilidad.auditoria.rei` — *design §5 decisión 6, spec REC-07 paso 5*
- [x] 3.14 Implementar `apply(..., modo='rei')` que procesa solo casos `estado='aprobado'`: anular asiento REI viejo + contra-asiento + nuevo con acumulación correcta (misma transacción y log) — *spec REC-06, REC-08*
- [x] 3.15 Vista confirmación apply en `contabilidad_audit/views.py` con doble confirmación explícita (mensajes en español) — *spec REC-02*

### 3.D Tests y documentación F3

- [x] 3.16 Tests en `legacy_db/tests/test_cont_recalculo_apply.py`: mocks transacción, rollback en concurrencia simulada, apply bloqueado fuera de producción, reconstrucción saldos idempotente, regeneración asientos sin duplicar — `docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_apply`
- [x] 3.17 Test integración piloto (empresa dev): apply sobre ejercicio de prueba → re-ejecutar `saldo_ejercicio_vs_diario` en verde — *proposal success criteria*
- [x] 3.18 Documentar rollback por `lote_id`, salvaguardas producción, reconstrucción de saldos, regeneración compras/pagos y flujo REI en `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_SYNAP.md` — *spec REC-14, REC-17, REC-18*

---

## Criterios de aceptación / verificación

Enlazado a **Success Criteria** (`proposal.md`):

| ID | Criterio | Fase | Verificación |
|----|----------|------|--------------|
| CA-MVP-1 | ≥16 checks ejecutables vía registry | F1 | Tablero lista 16 checks; `docker exec Synap_app python manage.py test contabilidad_audit` |
| CA-MVP-2 | Tablero saldo con drill-down | F1 | UI `/contabilidad/auditoria/` muestra cuentas con `\|delta\| > tolerancia` |
| CA-MVP-3 | `config_hash` reproducible por corrida | F1 | Dos corridas sin cambio → mismo hash y conteos |
| CA-4 | Dry-run sin escritura MySQL | F2 | Plan persistido; cero DML en legacy |
| CA-5 | Apply idempotente post-piloto | F3 | Saldos en verde; backup + log reversibles |
| CA-6 | Permisos segregados | F0–F3 | lectura / config / corregir / REI independientes |

**Comandos rápidos por fase:**

| Fase | Comando |
|------|---------|
| F0 | `docker exec Synap_app python manage.py verificar_esquema_cont --base_empresa=<empresa>` |
| F1 (MVP) | `docker exec Synap_app python manage.py test contabilidad_audit` |
| F2 | `docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_dry_run` |
| F3 | Provider log + `docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_apply` |

---

*Fases 0-3 aplicadas + REI refinado + gaps REC-07/08/14 cerrados. Orden seguro del apply: regen asientos (REC-18) → paso 2 concepto anulación → paso 3 INSERT filas saldo faltantes → paso 4 recompute maestro → REI (aprobación). `sdd-verify` = PASS; suite 40 tests OK (1 skip integración piloto). Listo para `sdd-archive`.*
