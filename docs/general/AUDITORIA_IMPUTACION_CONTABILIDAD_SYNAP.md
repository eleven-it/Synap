# Auditoría de imputación contable en Synap (MVP Fase 1)

**Change SDD:** `contabilidad-auditoria-recalculo`  
**Estado:** **Fase 1 + Fase 2 + Fase 3 implementadas** — auditoría solo lectura (MVP) + dry-run + apply/rollback transaccional + flujo REI caso a caso + vista apply con doble confirmación.  
**Fecha:** 18/07/2026

## Objetivo

Motor de auditoría **determinista y solo lectura** sobre tablas `cont_*` del MySQL legacy AdministraNET. Políticas configurables en PostgreSQL Synap. Cero escritura legacy en Fase 1.

## App y rutas

| Ruta | Vista | Permiso |
|------|-------|---------|
| `/contabilidad/auditoria/` | Tablero canon reportes (Alpine fetch al JSON); `?format=json` ejecuta corrida; `?format=csv` / `?format=xlsx` descargan el detalle | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/ejercicios-periodos/` | JSON de ejercicios y períodos de la **empresa base de la sesión** (solo lectura legacy) para los dropdowns predictivos del tablero. Orden fecha desc | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/configuracion/` | Configuración de políticas (GET consulta, POST guarda). Lectura con `.leer`; edición requiere `.configurar` (POL-12) | `contabilidad.auditoria.leer` (ver) / `contabilidad.auditoria.configurar` (editar) |
| `/contabilidad/auditoria/configuracion/historial/` | Historial consultable de cambios de política (`?format=json` para API) | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/dry-run/` | Dry-run Fase 2: genera plan de corrección (SELECT legacy), persiste `PlanCorreccion`, muestra guards; `?format=json|csv|xlsx` | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/rei/<uuid>/` | Aprobación REI caso a caso | `contabilidad.auditoria.rei` |
| `/contabilidad/auditoria/apply/` | Confirmación apply (GET formulario) | `contabilidad.auditoria.corregir` |
| `/contabilidad/auditoria/apply/ejecutar/` | Ejecutar apply (POST, doble confirmación) | `contabilidad.auditoria.corregir` |

Montaje: `django_project/urls.py` → `path('contabilidad/', include('contabilidad_audit.urls'))`.

Menú Synap: módulo **Contabilidad** (`core/utils/utils.py::APPS_MENU`, id `contabilidad`, orden 6.2) con ítems *Tablero de auditoría* (`contabilidad.auditoria.leer`) y *Configuración de políticas* (`contabilidad.auditoria.configurar`). El módulo es core-visible (siempre activo si hay permiso).

## Permisos Synap

Módulo **Contabilidad audit** en `core/constantes_permisos.py`:

- `contabilidad.auditoria.leer` — ejecutar checks / tablero
- `contabilidad.auditoria.configurar` — editar políticas
- `contabilidad.auditoria.corregir` — apply Fase 3 (producción)
- `contabilidad.auditoria.rei` — aprobar REI caso a caso

## Políticas (`PoliticaAuditoriaContable`)

Fila global `base_empresa='__default__'` con defaults:

| Campo | Default |
|-------|---------|
| tratamiento_anulados | excluir |
| politica_centavo | diario_manda |
| prefijos_cuenta | resultado `["4"]`, activo `["1"]`, pasivo `["2"]`, pn `["3"]` |
| ejercicios_cerrados | no_tocar |
| alcance_recompute | ejercicio_seleccionado |
| tolerancia_decimal | 0.005 |

Resolución: `resolver_politica(base_empresa)` (default → override). Hash: `calcular_config_hash` prefijo `v1:` + SHA-256 JSON canónico.

## Checks registrados (17)

| check_id | Severidad | Descripción breve |
|----------|-----------|-------------------|
| saldo_ejercicio_vs_diario | critico | Diario vs cont_ejercicio_saldo_cta |
| saldo_periodo_vs_diario | critico | Diario vs cont_periodo_saldo_cta |
| cuentas_sin_fila_saldo | alto | Imputables sin fila saldo |
| asiento_balanceado | alto | Σdebe ≈ Σhaber por codigo_movimiento |
| imputacion_a_no_imputable | alto | Movimiento en cuenta no imputable |
| concepto_anulacion_incoherente | alto | Contra-asiento vs id_concepto_anul |
| nro_asiento_duplicado | alto | Colisión nro_asiento en ejercicio |
| codigo_movimiento_huerfano | alto | CC sin asiento padre |
| fecha_fuera_de_periodo | medio | fecha_asiento fuera de intervalo periodo |
| periodos_solapados | medio | Intervalos periodo superpuestos |
| cierre_resultado_no_cero | medio | Cuentas 4x con saldo ≠ 0 |
| reparto_cc_incompleto | medio | Σ CC vs renglón |
| rei_recalculo | alto | REI teórico vs registrado |
| concepto_no_normal | medio | tipo_concepto_asiento ≠ Normal |
| comprobante_compra_pago_sin_asiento | critico | FA/FC/OP sin cont_asiento |
| asiento_compra_pago_desbalanceado_saldo_null | alto | Desbalance o saldo_asiento NULL |
| integridad_anulacion_compra_pago | alto | Anulación partida doble incompleta |

Registry: `contabilidad_audit/services/registry.py` → `CHECKS`.

## Ejecución

```bash
# Smoke esquema legacy
docker exec Synap_app python manage.py verificar_esquema_cont --base-empresa=administranet89

# Tests MVP
docker exec Synap_app python manage.py test contabilidad_audit

# Corrida vía API stub
GET /contabilidad/auditoria/?base_empresa=administranet89&id_ejercicio=1&format=json
```

Servicio: `contabilidad_audit/services/runner.py` → `ejecutar_corrida(base_empresa, filtros, check_ids, usuario)`.

Filtros obligatorios: `base_empresa`, `id_ejercicio`. Opcionales: `id_periodo`, `fecha_desde`, `fecha_hasta`, `check_ids[]`.

## UI (canon reportes)

Plantillas en `contabilidad_audit/templates/contabilidad_audit/`, extienden `base_app.html` y reutilizan los patrones Tailwind/Alpine del canon (`reports/dashboard_detail.html`): encabezado con degradado slate, panel de filtros, tarjetas y tablas. **No** se usa como referencia visual `ventas/objetivos-venta/` ni `ventas/presupuestos/` (regla `FUENTE_VERDAD_UI_REPORTES_MPR.md`).

### Tablero (`auditoria_tablero.html`)

- **Filtros:**
  - **Empresa base — fija de sesión (solo lectura):** el tablero y el dry-run toman `base_empresa` **siempre** de `request.session['user']['base_empresa']` (`_base_empresa_sesion`), **ignorando** cualquier `?base_empresa` de la URL. En la UI se muestra como chip deshabilitado (no editable); el valor se mantiene en el estado Alpine `filtros.baseEmpresa` (más un `<input type="hidden">`) solo para armar las queries. Motivo: evitar que un usuario audite/corrija otra empresa cambiando el querystring. La pantalla de **Configuración** sí sigue usando `?base_empresa` por GET (editar la política default/override).
  - **Ejercicio (obligatorio) y Período (opcional):** dropdowns con **búsqueda predictiva** (single-select, componente Alpine autocontenido dentro de `auditoriaTablero`). En `init()` hacen `fetch` a `/contabilidad/auditoria/ejercicios-periodos/`. Al enfocar/click despliegan la lista **completa** ordenada por fecha descendente (más reciente arriba, orden ya provisto por el backend); al escribir filtran por `label`. Botón «x» para limpiar. **El período depende del ejercicio elegido** (solo se listan períodos cuyo `id_ejercicio` coincide); sin ejercicio el período queda deshabilitado. `puedeEjecutar()` = empresa + ejercicio. Cierre con `@click.outside` y `Escape`.
- **Endpoint de datos (`auditoria_ejercicios_periodos`):** `GET /contabilidad/auditoria/ejercicios-periodos/` — permisos `.leer`. Toma la empresa de la sesión, abre conexión legacy con `get_mysql_pool().get_connection(base_empresa)` (solo SELECT) y devuelve:
  ```json
  {
    "base_empresa": "administranet89",
    "ejercicios": [{"id": 7, "label": "Ejercicio 2026 (01/04/2026 – 31/03/2027)", "descripcion": "...", "desde": "01/04/2026", "hasta": "31/03/2027", "cerrado": false}],
    "periodos": [{"id": 84, "id_ejercicio": 7, "label": "Abril 2026 (01/04/2026 – 30/04/2026)", "desde": "01/04/2026", "hasta": "30/04/2026", "cerrado": false}]
  }
  ```
  Consultas: `cont_ejercicio ORDER BY fecdesde_ejercicio DESC, id_ejercicio DESC` y `cont_periodo ORDER BY fecdesde_periodo DESC, id_periodo DESC`. Los `id` (DOUBLE en legacy) se castean a `int`; las fechas DATE se formatean dd/MM/yyyy (`_fecha_date_ui`); `cerrado` normaliza 'Si'/'No' a bool. Ante error de conexión devuelve `{"error": "...", "ejercicios": [], "periodos": []}` con status 500 (el front degrada mostrando listas vacías).
- **Ejecución:** Alpine hace `fetch` a `?format=json`. Auto-ejecuta si la URL trae `id_ejercicio` (empresa siempre de sesión).
- **Layout (fix solapamiento):** el encabezado oscuro usa `pt-8 pb-20` (más padding inferior) y el panel de filtros `-mt-12 relative z-20`, de modo que la tarjeta blanca queda claramente **debajo** de la banda oscura sin superponerse al título/texto, manteniendo el efecto de tarjeta flotante del canon. Los dropdowns desplegados usan `z-50` sobre el panel `z-20`.
- **Tarjetas verde/rojo por check:** verde = `ok` sin diferencias; rojo = con diferencias; ámbar = check con `error`. Muestran severidad (Crítico/Alto/Medio), evaluados y `total_diferencias`.
- **Drill-down:** al abrir una tarjeta con diferencias, tabla con `referencia_hallazgo`, `cod_pc`/`id_pc`, `id_ejercicio`, `nro_asiento`, `codigo_movimiento`, `valor_esperado`, `valor_actual`, `delta`.
- **Metadatos:** `config_hash`, `fecha_corrida` (dd/MM/yyyy HH:mm), conteos OK / con diferencias.

### Export CSV/Excel

`contabilidad_audit/services/export.py` (`exportar_corrida_csv`, `exportar_corrida_xlsx`) reutiliza las convenciones openpyxl del canon (`reports/services/export_service.py`). Endpoints `?format=csv` y `?format=xlsx` sobre el tablero. Incluyen bloque de metadatos (empresa, ejercicio, período, `config_hash`, fecha dd/MM/yyyy), resumen por check y detalle de diferencias (Excel: hojas *Resumen* + *Diferencias*).

> **Desviación documentada:** `reports/services/export_service.ExportService` está acoplado a `ReportDefinition` + `QueryRunnerService`, por lo que no se instancia directamente. Se creó un exportador dedicado que **replica sus convenciones visuales** (estilos openpyxl, bloque de metadatos, cabeceras) operando sobre el payload de `ejecutar_corrida()`.

### Configuración (`auditoria_configuracion.html`)

Formulario de la política global (`__default__`) y override por `base_empresa` (selector). Campos del modelo: `tratamiento_anulados`, `politica_centavo`, `prefijos_cuenta` (4 categorías, coma-separado), `ejercicios_cerrados`, `alcance_recompute`, `tolerancia_decimal`. El POST valida con `PoliticaAuditoriaContable.full_clean()` (enums + JSON de prefijos + tolerancia positiva) y muestra errores en español. Usuarios sin `contabilidad.auditoria.configurar` ven el formulario en **sólo lectura** (POL-12).

#### POL-07 — Aviso de performance (alcance histórico)

Cuando `alcance_recompute=historico` está seleccionado en el formulario de configuración, Alpine muestra un banner naranja advirtiendo que el recálculo histórico es costoso y debe ejecutarse por lotes y fuera de horario operativo. En el dry-run (`auditoria_dry_run.html`), el mismo aviso aparece si la política efectiva resuelta usa alcance histórico.

#### POL-10 — Historial de cambios de política

Modelo Postgres `HistorialPoliticaAuditoria` (`contabilidad_audit/models.py`): `base_empresa`, `snapshot_anterior`, `snapshot_nuevo`, `config_hash_anterior`, `config_hash_nuevo`, `cambiado_por`, `cambiado_en`. Al guardar una política (POST en configuración), `registrar_historial_politica()` en `services/politicas.py` persiste el estado anterior (o `None` en altas), el nuevo, ambos hashes (`calcular_config_hash`) y el usuario.

La pantalla de configuración incluye una sección **Historial de cambios** (tabla con fecha dd/MM/yyyy HH:mm, usuario, diffs campo a campo y config_hash). Endpoint JSON: `GET /contabilidad/auditoria/configuracion/historial/?base_empresa=...&format=json`. Permiso de consulta: `contabilidad.auditoria.leer`.

## Criterios de aceptación MVP

- CA-MVP-1: 17 checks ejecutables vía registry ✅
- CA-MVP-2: Tablero con drill-down (implementado) ✅
- CA-MVP-3: `config_hash` reproducible por corrida ✅
- CA-4: Dry-run sin escritura MySQL ✅ (plan en Postgres; servicio legacy solo SELECT)
- CA-6: Permisos segregados lectura / config / corregir / REI ✅

## Contexto expuesto por la vista del tablero

`_contexto_tablero()` devuelve para la plantilla:

- `titulo_pagina`, `base_empresa` (de sesión), `id_ejercicio`, `id_periodo`
- `checks_disponibles` (metadatos por check: id, título, severidad; embebido con `json_script`)
- `permiso_leer`, `permiso_configurar`, `puede_configurar`
- `tablero_url`, `configuracion_url`, `ejercicios_periodos_url`, `auto_ejecutar`

JSON corrida (`?format=json`): `corrida_id`, `config_hash`, `filtros`, `checks[]` con `diferencias[]` y metadatos dd/MM/yyyy.

## Fase 2 — Dry-run de corrección (REC-01, REC-10, REC-13, REC-15)

Regla de oro: **cero DML/DDL en MySQL legacy**. El plan se persiste en PostgreSQL (`PlanCorreccion`). La Fase 3 (`apply`) exige aprobación contable previa sobre el reporte de impacto.

### Servicio

`legacy_db/services/cont_recalculo_service.py` → `dry_run(base_empresa, alcance, politica, usuario)`:

1. **Concepto anulación incoherente** (REC-07 paso 2 / REC-08): contra-asientos con `id_concepto_asiento` ≠ `id_concepto_anul` del original; items `accion=update`, `campo=id_concepto_asiento`, `check_id=concepto_anulacion_incoherente`, `referencia=H05`.
2. **Regeneración de asientos faltantes** (REC-18): comprobantes FA/FC/OP con `CodigoMovimiento>0` sin filas en `cont_asiento`; concepto 3/7; reuso de `codigo_movimiento`; `nro_asiento` simulado desde contador del ejercicio; ajuste de redondeo en `id_pc=300` si aplica.
3. **Filas saldo faltantes** (REC-07 paso 3 / REC-08): cuentas con movimientos sin fila en `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta`; items `accion=insert`, `check_id=cuentas_sin_fila_saldo`, `referencia=H10` (ejercicio) o `H17` (periodo).
4. **Reconstrucción de saldos** (REC-07 paso 4 / REC-17): modelo sin arrastre, Σ firmada de **todas** las filas de `cont_asiento` (incluye anulados neutralizados) más los asientos simulados del paso 2; solo `accion=update` sobre filas existentes, `check_id=saldo_ejercicio_vs_diario` / `saldo_periodo_vs_diario`, `referencia=H53`.

Respeta `alcance_recompute` (`ejercicio_seleccionado`, `ejercicio_activo`, `historico`) y `ejercicios_cerrados=no_tocar` (items marcados `excluido=True`, motivo `ejercicio_cerrado`).

### Estructura de un item del plan

```json
{
  "tabla": "cont_asiento",
  "clave": {"codigo_movimiento": "12345", "id_pc": 100, "nro_asiento": 501},
  "accion": "insert",
  "valor_anterior": null,
  "valor_nuevo": {"nro_asiento": 501, "fecha_asiento": "2024-03-15", "id_ejercicio": 7, "debe_asiento": "1000.00", "haber_asiento": "0.00", "id_pc": 100, "id_concepto_asiento": 3, "codigo_movimiento": "12345"},
  "delta": "1000.00",
  "check_id": "comprobante_compra_pago_sin_asiento",
  "referencia": "H51",
  "excluido": false
}
```

Para saldos desincronizados (paso 4): `tabla=cont_ejercicio_saldo_cta`, `accion=update`, `valor_anterior`/`valor_nuevo`/`delta` numéricos en string, `check_id=saldo_ejercicio_vs_diario`, `referencia=H53`.

Para filas faltantes (paso 3): `accion=insert`, `valor_anterior=null`, `check_id=cuentas_sin_fila_saldo`, `referencia=H10`.

Para concepto anulación (paso 2):

```json
{
  "tabla": "cont_asiento",
  "clave": {"codigo_movimiento": "9999", "nro_asiento": 42, "id_pc": 100},
  "accion": "update",
  "campo": "id_concepto_asiento",
  "valor_anterior": "4",
  "valor_nuevo": "7",
  "check_id": "concepto_anulacion_incoherente",
  "referencia": "H05"
}
```

### Guards de validez (design §5 decisión 5)

| Guard | Campo | Regla |
|-------|-------|-------|
| TTL | `expira_en` | `creado_en + 30 min` (`PLAN_TTL_MIN`) |
| Política | `config_hash` | `calcular_config_hash(politica)` al generar el plan |
| Concurrencia | `data_fingerprint` | SHA-256 `v1:` sobre tuplas `(tabla, clave, valor_anterior)` ordenadas |

Cambiar la política entre dry-run y apply **invalida** el plan (REC-15).

### Backups propuestos (REC-03 preparación)

En `plan.backups_propuestos`: nombres simulados `{tabla}_bkp_{YYYYMMDD_HHMMSS}` por tabla afectada. **No** se crean tablas en Fase 2.

### Vista y export

- GET `/contabilidad/auditoria/dry-run/?base_empresa=administranet89&id_ejercicio=7`
- JSON: `?format=json` — CSV/Excel: `?format=csv` / `?format=xlsx` (`contabilidad_audit/services/export.py`: `exportar_dry_run_csv`, `exportar_dry_run_xlsx`)
- Plantilla: `auditoria_dry_run.html` (canon reportes; muestra guards, impacto, muestra de items; **sin** botón apply)

### Tests Fase 2

```bash
docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_dry_run contabilidad_audit --keepdb
```

## Fase 3 tramo 1 — Apply transaccional (REC-02..REC-18 parcial)

Servicio: `legacy_db/services/cont_recalculo_service.py` → `apply()`, `rollback_lote()`.

### DDL log legacy (3.1–3.3)

Tablas nuevas por empresa (no alteran `cont_*`):

- `cont_audit_correccion_lote` — cabecera del lote (`lote_id`, `dry_run_id`, `config_hash`, `backups_json`, `reapertura_flag`, …)
- `cont_audit_correccion` — detalle por mutación

Ejecutar en empresa piloto (idempotente):

```bash
docker exec Synap_app python manage.py apply_contabilidad_audit_correccion_log administranet89
```

Equivalente vía catálogo: provider `contabilidad_audit_correccion_log` en `core/services/legacy_mysql_schema/catalog.py` (UI `/core/legacy-mysql-schema/` o `run_provider_by_id`).

### Salvaguardas apply

| Guard | Verificación |
|-------|----------------|
| Producción | `settings.ENVIRONMENT in ('production','produccion')` |
| Permiso | `contabilidad.auditoria.corregir` (flag `tiene_permiso_corregir` desde vista) |
| Plan | `PlanCorreccion.estado='propuesto'`, TTL, `config_hash`, `data_fingerprint` |
| Backup | `CREATE TABLE {tabla}_bkp_{timestamp} AS SELECT * FROM {tabla}` antes de DML |
| Concurrencia | Re-lectura fingerprint intra-transacción + `SELECT … FOR UPDATE` |

### Orden de escritura (transacción única, REC-07)

1. `INSERT cont_audit_correccion_lote`
2. `SELECT … FOR UPDATE` contadores/filas objetivo
3. Re-validación `data_fingerprint`
4. Regeneración asientos (`cont_asiento` INSERT, REC-18, agrupados por `codigo_movimiento`)
5. **Paso 2** — `concepto_anulacion_incoherente`: `UPDATE cont_asiento SET id_concepto_asiento=…` con re-validación del valor anterior
6. **Paso 3** — `cuentas_sin_fila_saldo`: `INSERT` filas faltantes en `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta` (idempotente si la fila ya existe)
7. **Paso 4** — `saldo_ejercicio_vs_diario` / `saldo_periodo_vs_diario`: `UPDATE` recompute maestro sobre filas existentes (REC-17)
8. `INSERT cont_audit_correccion` por mutación
9. `COMMIT` → `PlanCorreccion.estado='aplicado'`

NO se ejecuta el paso 4 antes de completar 2–3 cuando el plan los incluye.

Excluidos del auto-apply: `cierre_resultado_no_cero`, asientos desbalanceados sin regla, `rei_recalculo`, cuentas con `saldo_pc` NULL.

### Rollback (REC-14)

`rollback_lote(base_empresa, lote_id, usuario, tiene_permiso_corregir=True)` restaura desde `backups_json` del lote en **transacción única** (`DELETE` + `INSERT SELECT * FROM {tabla}_bkp_{ts}` por tabla), marca el lote `estado='revertido'` y registra evento `check_id=rollback_lote` en `cont_audit_correccion`. Exige las mismas salvaguardas que apply (`ENVIRONMENT=production` + permiso `contabilidad.auditoria.corregir`). Si falta alguna tabla backup (p. ej. purgada manualmente), aborta con error explícito sin cambios parciales.

### Hook REI (Fase 3.C — implementado)

Flujo caso a caso (design §5 decisión 6):

1. **Dry-run** detecta diferencias REI (`rei_recalculo`) y persiste `AprobacionREI(estado='pendiente')` por `(id_pc, id_ejercicio)` ligadas al `dry_run_id`. También guarda `propuestas_rei[]` en el JSON del plan.
2. **UI** `/contabilidad/auditoria/rei/<dry_run_id>/` — permiso `contabilidad.auditoria.rei`; approve/reject individual con `aprobado_por` / `aprobado_en` (fechas dd/MM/yyyy).
3. **Apply modo REI** — `apply(..., modo='rei')` procesa **solo** casos `estado='aprobado'` y **rechaza** si el REI no es computable:
   - Marca asiento REI original (concepto 13) `anulado='Si'`
   - Inserta **contra-asiento** reversante (`codigo_movimiento` nuevo, `codigo_movimiento_anul` = original, concepto de anulación vía `id_concepto_anul`)
   - Genera **asiento REI nuevo** balanceado (cuenta + contrapartida paramatriz **63**) con importe `rei_teorico`, concepto 13, desc «Asiento por ajuste de inflación - REI »
   - Actualiza `cont_ejercicio_saldo_cta` al saldo corrido tras anulación + nuevo asiento
   - Misma transacción y log `cont_audit_correccion_*` que apply general

Apply REI desde UI: `/contabilidad/auditoria/apply/?modo=rei&dry_run_id=...` (doble confirmación).

### REI refinado (fórmula VB6 + fix H02)

Fuente de verdad: `Cont_ProcesosC.frm` — `GeneraAsientoInflacion` / `generar_asiento_cont`. Implementación compartida en `contabilidad_audit/services/rei_calculo.py`.

**Fórmula por cuenta con `ajuste_infla_pc='Si'`:**

1. **`ind_cierre`**: `cont_indiceinfla_periodo.importe` donde `fechasta_indiceinfla_periodo = cont_ejercicio.fechasta_ejercicio` y `anulado<>'Si'`. Si no existe → REI **no computable** (motivo: «falta índice de cierre para dd/MM/yyyy»). No se asume 1 ni 0.
2. **Por cada renglón base** de `cont_asiento` de la cuenta en el ejercicio (**excluye** `id_concepto_asiento=13`; incluye anulados):
   - **`ind_origen`**: índice cuyo intervalo contiene `fecha_asiento`. Si falta o es 0 → no computable («falta índice de origen para dd/MM/yyyy»).
   - **`mov`**: `(debe-haber)` si `saldo_pc='Deudor'`; `(haber-debe)` si `'Acreedor'`.
   - **`subt = mov × (ind_cierre / ind_origen) − mov`**; **`total += subt`** en **todos** los renglones (fix H02: no omitir el último de cada grupo).
3. **`REI_teorico(cuenta) = total`**. Comparación vs **REI registrado** = suma firmada de renglones **concepto 13** (no anulados) de esa cuenta/ejercicio.

**Comportamiento defensivo:**

| Situación | Check `rei_recalculo` | Dry-run / apply |
|-----------|----------------------|-----------------|
| Falta `ind_cierre` u `ind_origen` | Diferencia `estado=no_computable`, `delta=None`, H02 | Propuesta `excluido=True`; apply rechaza con mensaje ES |
| Delta computable > tolerancia | Diferencia con `valor_esperado`/`valor_actual`, H02 | Propuesta aplicable (requiere aprobación REI) |
| Cuentas con concepto 13 sin `ajuste_infla_pc='Si'` | H44 desalineación config | Propuesta excluida H44 |
| Contrapartida REI ≠ `cont_paramatriz` id 63 | H44 desalineación config | Propuesta excluida H44 |

**Apply modo REI:** anula asientos REI viejos (concepto 13) con contra-asiento (`id_concepto_anul` del concepto 13); genera asiento nuevo con importe `rei_teorico`, concepto 13, descripción «Asiento por ajuste de inflación - REI », contrapartida **solo** paramatriz 63. Identificación canónica: **`id_concepto_asiento=13`** (sin heurística de textos ni conceptos 45/47/53).

**administranet89 (empírico):** un solo índice cargado (2012-01-01→2012-12-31, importe 20); ejercicios 2025-04→2026-03 y 2026-04→2027-03 → `ind_cierre`/`ind_origen` **no existen** → check reporta no computable (H02). Hay REI histórico (concepto 13) en cuentas 17/22/28/… pero hoy sólo id_pc 115 tiene `ajuste_infla_pc='Si'` y contrapartida vigente id_pc 109 (paramatriz 63) → desalineación H44.

Tests: `contabilidad_audit/tests/test_rei.py`, apply en `legacy_db/tests/test_cont_recalculo_apply.py`.

### Vista apply — doble confirmación (3.15)

- **GET** `/contabilidad/auditoria/apply/` — resumen del plan + formulario (no ejecuta).
- **POST** `/contabilidad/auditoria/apply/ejecutar/` — requiere:
  1. Checkbox «entiendo que se modificarán datos contables»
  2. Token escrito `APLICAR-<dry_run_id>` (o frase `APLICAR DEFINITIVAMENTE`)
- Pasa `tiene_permiso_corregir=True` al servicio. Muestra `lote_id`, filas afectadas o error de guard/concurrencia.

### Test integración piloto (3.17)

Archivo: `legacy_db/tests/test_cont_recalculo_apply_integracion.py`

```bash
# Solo en piloto real (NO dev/administranet89 habitual):
docker exec -e SYNAP_PILOTO_CONT=1 -e ENVIRONMENT=production Synap_app \
  python manage.py test legacy_db.tests.test_cont_recalculo_apply_integracion --keepdb
```

Variables opcionales: `SYNAP_PILOTO_BASE_EMPRESA`, `SYNAP_PILOTO_ID_EJERCICIO`. En dev el test **SKIP** (no falla).

### Tests Fase 3 completos

```bash
docker exec Synap_app python manage.py test contabilidad_audit legacy_db.tests.test_cont_recalculo_dry_run legacy_db.tests.test_cont_recalculo_apply legacy_db.tests.test_cont_recalculo_rollback legacy_db.tests.test_cont_recalculo_apply_integracion --keepdb
```

## Referencias

- Design: `openspec/changes/contabilidad-auditoria-recalculo/design.md`
- Hallazgos VB6: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`
- Esquema verificado: `docs/general/INVENTARIO_ESQUEMA_CONT_AUDITORIA.md`
- Script validado compras/pagos: `legacy_db/scripts/cont_reconstruccion_compras_pagos.py`
