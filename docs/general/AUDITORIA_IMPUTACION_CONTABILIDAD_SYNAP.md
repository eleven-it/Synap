# Auditoría de imputación contable en Synap (MVP Fase 1)

**Change SDD:** `contabilidad-auditoria-recalculo` (+ delta `contabilidad-auditoria-anulaciones-apply` / REC-19)  
**Estado:** **Fase 1 + Fase 2 + Fase 3 + REC-19** — auditoría solo lectura + dry-run + apply (sin backup de tablas) + REI + **reparación de anulaciones incompletas** (marcador / marcar original / contra) + UI lotes (sin rollback).  
**Fecha:** 25/07/2026

## Objetivo

Motor de auditoría **determinista y solo lectura** sobre tablas `cont_*` del MySQL legacy AdministraNET. Políticas configurables en PostgreSQL Synap. Cero escritura legacy en Fase 1.

## App y rutas

| Ruta | Vista | Permiso |
|------|-------|---------|
| `/contabilidad/manual/` | Manual de usuario HTML (sesión activa) | Sesión |
| `/contabilidad/auditoria/` | Tablero canon reportes (Alpine fetch al JSON); `?format=json` ejecuta corrida; `?format=csv` / `?format=xlsx` descargan el detalle | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/ejercicios-periodos/` | JSON de ejercicios y períodos de la **empresa base de la sesión** (solo lectura legacy) para los dropdowns predictivos del tablero. Orden fecha desc | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/configuracion/` | Configuración de políticas (GET consulta, POST guarda). Lectura con `.leer`; edición requiere `.configurar` (POL-12) | `contabilidad.auditoria.leer` (ver) / `contabilidad.auditoria.configurar` (editar) |
| `/contabilidad/auditoria/configuracion/historial/` | Historial consultable de cambios de política (`?format=json` para API) | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/dry-run/` | Dry-run Fase 2: genera plan de corrección (SELECT legacy), persiste `PlanCorreccion`, muestra guards; `?format=json|csv|xlsx` | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/rei/<uuid>/` | Aprobación REI caso a caso | `contabilidad.auditoria.rei` |
| `/contabilidad/auditoria/apply/` | Confirmación apply (GET formulario) | `contabilidad.auditoria.corregir` |
| `/contabilidad/auditoria/apply/ejecutar/` | Ejecutar apply (POST, confirmación checkbox) | `contabilidad.auditoria.corregir` |
| `/contabilidad/auditoria/lotes/` | Lotes aplicados (`cont_audit_correccion_lote`) | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/lotes/<lote_id>/` | Detalle del lote aplicado; `?format=xlsx` export Excel | `contabilidad.auditoria.leer` |
| `/contabilidad/auditoria/lotes/<lote_id>/rollback/` | Endpoint legacy bloqueado (reversión deshabilitada) | `contabilidad.auditoria.corregir` |

Montaje: `django_project/urls.py` → `path('contabilidad/', include('contabilidad_audit.urls'))`.

Flujo operativo guiado desde el tablero: **Tablero → Ejecutar → tarjeta con diferencias → Generar diagnóstico → Apply → Lotes aplicados**.

El acceso al plan de corrección (`/contabilidad/auditoria/dry-run/`, ruta y payload internos sin renombrar) es **siempre por tarjeta**: el tablero no expone CTA global. El CTA de la tarjeta sólo aparece si el check tiene diferencias y está en `CHECKS_INCLUIDOS` (`legacy_db/services/cont_recalculo_service.py`), que la vista publica al front como `checks_corregibles`; en caso contrario se muestra «Sin corrección automática». La UI usa el término **Diagnóstico** (con «Id diagnóstico» para el `dry_run_id`).

Menú Synap: módulo **Contabilidad** (`core/utils/utils.py::APPS_MENU`, id `contabilidad`, orden 6.2) con ítems *Tablero de auditoría* (`contabilidad.auditoria.leer`), *Configuración de políticas* (`contabilidad.auditoria.configurar`) y *Manual de usuario*. El módulo es core-visible (siempre activo si hay permiso). Manual operativo: [`docs/contabilidad/MANUAL_USUARIO_CONTABILIDAD.md`](../contabilidad/MANUAL_USUARIO_CONTABILIDAD.md) · HTML `/contabilidad/manual/`.

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

## Checks registrados (18)

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
| comprobante_compra_pago_sin_asiento | critico | FA/FC/OP (`cuentaproveedor`) sin cont_asiento |
| comprobante_venta_cobranza_sin_asiento | critico | FA/FB/FC/FE/FM/REC (`cuentacliente`) sin cont_asiento |
| asiento_compra_pago_desbalanceado_saldo_null | alto | Desbalance o saldo_asiento NULL |
| integridad_anulacion_compra_pago | alto | Anulación partida doble incompleta |

### Check venta/cobranza (AUD-LECT-24)

- Tabla: `cuentacliente` (no mezclar con compras).
- Tipos: facturas venta `FA`/`FB`/`FC`/`FE`/`FM` (concepto 1) + `REC` (concepto 5).
- Gating (regla AdministraNET): **`punto_venta.cont='Si'`** (clientes). Compras/pagos usan **`sucursales.cont='Si'`** (proveedores).
- Referencias: H54 (venta), H55 (REC).
- **Regeneración (REC-20):** dry-run/apply vía el mismo motor que compras (`cont_recalculo_service`); marca `REGEN auditoria (bug factura/REC sin asiento)`; conceptos 1/5; gating `punto_venta.cont`. Fuera de alcance: integridad de anulación venta/REC y NC/ND.
- Baseline `administranet89` (25/07/2026, post-restore, solo `pv.cont='Si'`): 2 huérfanos FA/FB balanceables (cm `58305`, `88621`); no usar `sucursales.cont` como alternativa para clientes.

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

**Alcance por ejercicio:** los **18 checks** del registry filtran por el ejercicio del tablero. Los que operan sobre `cont_asiento` usan `id_ejercicio`; los que cruzan con comprobantes (`cuentaproveedor`, `cuentacliente`) o CC huérfanos acotan además por `Fecha` dentro del rango `[fecdesde_ejercicio, fechasta_ejercicio]` de `cont_ejercicio` (y, si se elige período, por `cont_periodo`). Helpers reutilizables en `contabilidad_audit/services/checks/_sql.py`.

## UI (canon reportes)

Plantillas en `contabilidad_audit/templates/contabilidad_audit/`, extienden `base_app.html` y reutilizan los patrones Tailwind/Alpine del canon (`reports/dashboard_detail.html`): encabezado con degradado slate, panel de filtros, tarjetas y tablas. **No** se usa como referencia visual `ventas/objetivos-venta/` ni `ventas/presupuestos/` (regla `FUENTE_VERDAD_UI_REPORTES_MPR.md`).

**Modal de espera:** las operaciones largas (corrida del tablero, generar diagnóstico, apply) muestran el overlay compartido `partials/synap_post_loading_modal.html` con título/subtítulo de estado en español. Ver `docs/general/SYNAP_MENSAJES_TOAST.md` (§ modal de espera). No usar diálogos nativos ni dejar al usuario sin feedback durante la espera. El CTA «Generar diagnóstico» de cada tarjeta llama `mostrarEsperaDiagnostico(evento, check_id)` antes de la navegación GET (el plan se calcula al cargar la página destino) y arma la URL con `diagnosticoLink(check_id)`, que envía **un solo** `check_ids`. En el overlay, el `label` muestra el **título del diagnóstico** (no texto genérico).

**Detalle del plan (dry-run):** la tabla «Detalle de correcciones (muestra)» desglosa cada ítem en columnas contables planas (Diagnóstico, Acción, **Nro asiento**, **Fecha** dd/MM/yyyy, **Cuenta**, **Debe**, **Haber**, **Descripción**, Delta, Excluido, Detalle), sin «Valor anterior» ni JSON crudo. **Celdas iguales y no vacías se combinan solo dentro del mismo nro de asiento** (no cruzan asientos distintos): `rowspan` en la UI y merge en Excel (hoja Plan / Detalle del lote). En filas de saldo numérico solo se muestran cuenta y descripción tipo «$ ant → $ nuevo»; asiento/fecha/debe/haber quedan vacíos. Al hacer clic en la fila o en el ícono de documento se abre un modal Synap con el detalle estructurado; el JSON completo queda bajo «Datos técnicos» (colapsable). Los datos de validez técnica (TTL, `config_hash`, `data_fingerprint`, id, impacto por tabla) van en el acordeón colapsado **Información técnica del plan**, ocultos por defecto al auditor contable.

**Apply desde diagnóstico:** no se navega a `/contabilidad/auditoria/apply/` para el modo general. El CTA **Aplicar correcciones** abre un modal Synap en la misma pantalla (aviso corto + checkbox de confirmación) y hace POST JSON a `/contabilidad/auditoria/apply/ejecutar/` con `"stream": true` (o `Accept: application/x-ndjson`) → `StreamingHttpResponse` NDJSON (`type: progress` / `done` / `error`). Fases: `write`, `finalize`. UI: barra determinada con `synapShowPostLoadingProgress` + `synapUpdatePostLoadingProgress` (mismo patrón que eliminación de asientos). Éxito → redirect del front a **Lotes**; error → toast/mensaje en diagnóstico. La página GET de apply se conserva para el flujo REI (`modo=rei`, sin stream en v1).

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
- **Ejecución:** Alpine hace `fetch` a `?format=json`. Mientras corre, abre `synapShowPostLoadingProgress` («Ejecutando auditoría» / «Evaluando checks») y lo cierra en `finally`. Auto-ejecuta si la URL trae `id_ejercicio` (empresa siempre de sesión).
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

1. **Regeneración de asientos faltantes compra/pago** (REC-18): comprobantes FA/FC/OP con `CodigoMovimiento>0` sin filas en `cont_asiento`; concepto 3/7; reuso de `codigo_movimiento`; `nro_asiento` simulado; ajuste de redondeo en `id_pc=300` si aplica.
2. **Regeneración de asientos faltantes venta/cobranza** (REC-20): FA/FB/FC/FE/FM/REC en `cuentacliente` sin asiento; conceptos 1/5; gating `punto_venta.cont`; marca `REGEN auditoria (bug factura/REC sin asiento)`. Mismo paso de apply que REC-18 (antes de anulaciones/saldos).
3. **Reparación de anulaciones incompletas** (REC-19): hallazgos de `integridad_anulacion_compra_pago` — ver tabla problema→remedio más abajo; sección UI «Reparación de anulaciones» con `anulaciones_reparables` / `anulaciones_bloqueadas`.
4. **Concepto anulación incoherente** (REC-07 / REC-08): contra-asientos con `id_concepto_asiento` ≠ `id_concepto_anul` del original; items `accion=update`, `campo=id_concepto_asiento`, `check_id=concepto_anulacion_incoherente`, `referencia=H05`.
5. **Filas saldo faltantes**: cuentas con movimientos sin fila en `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta`; items `accion=insert`, `check_id=cuentas_sin_fila_saldo`, `referencia=H10` / `H17`.
6. **Reconstrucción de saldos** (REC-17): modelo sin arrastre, Σ firmada de **todas** las filas de `cont_asiento`; `accion=update`, `check_id=saldo_*_vs_diario`, `referencia=H53`.

Respeta `alcance_recompute` (`ejercicio_seleccionado`, `ejercicio_activo`, `historico`) y `ejercicios_cerrados=no_tocar` (items marcados `excluido=True`, motivo `ejercicio_cerrado`).

### REC-19 — Problema → remedio (anulaciones compra/pago)

| Problema | Remedio auto-apply | Acción plan |
|----------|-------------------|-------------|
| `falta_marcador_cuentaproveedor_cm0` | INSERT marcador `CodigoMovimiento=0`, `Detalle="Anulacion - …"`, `codigo_movimiento_anul=cm` | `insert_marcador` |
| `asiento_original_no_anulado` | UPDATE `cont_asiento` del cm → `anulado='Si'` (solo si hay renglones pendientes) | `marcar_original_anulado` |
| `falta_contra_asiento` | INSERT contra (concepto 4/8, debe/haber invertidos, cm nuevo); requiere asiento original | `insert_contra_asiento` |
| `contra_no_invierte_original` | **Excluido** (revisión manual) | `bloqueado` |

Marca trazable en renglones del contra: `REGEN auditoria (anulacion incompleta)`. Backup incluye `cuentaproveedor`. Si el comprobante anulado no tiene filas en `cont_asiento`, el check puede reportar `falta_contra_asiento` pero el dry-run **no** propone contra (no hay original que invertir).

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

Para saldos desincronizados (paso 6): `tabla=cont_ejercicio_saldo_cta`, `accion=update`, `valor_anterior`/`valor_nuevo`/`delta` numéricos en string, `check_id=saldo_ejercicio_vs_diario`, `referencia=H53`.

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

### Backups propuestos (histórico REC-03)

El dry-run ya **no** simula nombres de tablas backup: `plan.backups_propuestos` queda `{}`. Tampoco se crean tablas en Fase 2 ni en apply.

### Vista y export

- GET `/contabilidad/auditoria/dry-run/?base_empresa=administranet89&id_ejercicio=7`
- JSON: `?format=json` — CSV/Excel: `?format=csv` / `?format=xlsx` (`contabilidad_audit/services/export.py`: `exportar_dry_run_csv`, `exportar_dry_run_xlsx`)
- Export dry-run en **formato contador** (redacción potencial): columnas Diagnóstico, Tipo de cambio a aplicar, Nro asiento, Fecha (dd/MM/yyyy), Cód. movimiento, Cuenta, Debe/Haber (`$ x.xxx,xx`), Descripción, Valor ant/nuevo previsto, **Cambios a realizar** (resumen concatenado opcional), Delta. Sin JSON de clave ni `check_id` técnico. Metadatos sin `config_hash`/`dry_run_id`.
- Plantilla: `auditoria_dry_run.html` (canon reportes; guards, impacto, sección anulaciones reparables/bloqueadas; enlace a apply si hay permiso)

### Tests Fase 2

```bash
docker exec Synap_app python manage.py test legacy_db.tests.test_cont_recalculo_dry_run contabilidad_audit --keepdb
```

## Fase 3 tramo 1 — Apply transaccional (REC-02..REC-18 parcial)

Servicio: `legacy_db/services/cont_recalculo_service.py` → `apply()`, `rollback_lote()` (inoperativo: reversión deshabilitada).

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
| Entorno | Cualquiera (development incluido para pruebas); ya no se exige `ENVIRONMENT=production` |
| Permiso | `contabilidad.auditoria.corregir` (flag `tiene_permiso_corregir` desde vista) |
| Plan | `PlanCorreccion.estado='propuesto'`, TTL, `config_hash`, `data_fingerprint` |
| Backup | **No** (por diseño de producto). Atomicidad vía una sola transacción MySQL. `backups_json` del lote queda `{}`. Si falla a mitad, `ROLLBACK` deshace los cambios. |
| Concurrencia | Re-lectura fingerprint intra-transacción + `SELECT … FOR UPDATE` |

### Orden de escritura (transacción única, REC-07)

1. `INSERT cont_audit_correccion_lote`
2. `SELECT … FOR UPDATE` contadores/filas objetivo
3. Re-validación `data_fingerprint`
4. **REC-18 / REC-20** — regeneración asientos huérfanos compra y venta (`cont_asiento` INSERT)
5. **REC-19** — reparación anulaciones: marcador → marcar original → INSERT contra
6. **Concepto anulación** — `UPDATE cont_asiento SET id_concepto_asiento=…`
7. **Filas saldo** — `INSERT` en `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta`
8. **Recompute saldos** — `UPDATE` maestro (REC-17)
9. `INSERT cont_audit_correccion` por mutación
10. `COMMIT` → `PlanCorreccion.estado='aplicado'`

NO se ejecuta el recompute de saldos antes de completar regen/repair/concepto/INSERT saldo cuando el plan los incluye.

Excluidos del auto-apply: `cierre_resultado_no_cero`, `concepto_no_normal`, asientos desbalanceados sin regla, `contra_no_invierte_original`, `rei_recalculo` (salvo modo REI), cuentas con `saldo_pc` NULL.

### UI lotes (sin rollback)

- Listado: `/contabilidad/auditoria/lotes/` — muestra **planes de diagnóstico** recientes (Postgres `PlanCorreccion`, hasta 50 por empresa) y **lotes aplicados** (lectura del log legacy `cont_audit_correccion_lote`).
- **Detalle de lote:** `/contabilidad/auditoria/lotes/<lote_id>/` — resumen del lote + filas de `cont_audit_correccion` (UI con `cambio_resumen` contable, fechas dd/MM/yyyy; columna **Cambios aplicados**). Export Excel `?format=xlsx` (`exportar_lote_xlsx`): hojas **Resumen** (sin hashes) + **Detalle** en formato contador y **redacción en pasado** (Diagnóstico, Tipo de cambio aplicado, Nro asiento, Fecha, CM, Cuenta, Debe/Haber, Descripción, Concepto, Valor ant/aplicado, **Cambios aplicados**, Fecha de aplicación). Sin columnas Clave/Check/JSON. Filename `lote_correccion_{base}_{lote_id_corto}.xlsx`. En el listado, acciones **Ver** y **Excel** por fila.
- **Historial de planes:** cada dry-run persistido aparece con estado **Vigente** (propuesto dentro del TTL) o **Aplicado**. Los vigentes tienen acción **Abrir** (reabre `/contabilidad/auditoria/dry-run/?dry_run_id=…` sin regenerar) y **Actualizar** (`?dry_run_id=…&refresh=1`, re-ejecuta el diagnóstico in-place con el mismo UUID).
- **Purge lazy:** al entrar a lotes o antes de generar un plan nuevo, `_purgar_planes_vencidos` marca propuesto vencido → `expirado` y elimina planes `expirado`/`invalidado` junto con sus `AprobacionREI`. No borra `aplicado` ni propuesto vigente.
- **Reversión de lotes:** deshabilitada. El endpoint POST `/contabilidad/auditoria/lotes/<lote_id>/rollback/` responde con error en UI; `rollback_lote()` en servicio lanza `CorreccionContableError` sin restaurar tablas.

### Rollback (REC-14 — deshabilitado)

`rollback_lote()` se mantiene por compatibilidad de imports pero **no restaura tablas**. Las correcciones contables ya no generan backup (`backups_json='{}'`). Lotes históricos con backups antiguos tampoco son revertibles desde Synap.

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

Apply REI desde UI: `/contabilidad/auditoria/apply/?modo=rei&dry_run_id=...` (confirmación checkbox).

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

### Vista apply — confirmación (3.15)

- **GET** `/contabilidad/auditoria/apply/` — resumen del plan + formulario (no ejecuta).
- **POST** `/contabilidad/auditoria/apply/ejecutar/` — requiere checkbox «entiendo que se modificarán datos contables» (sin token escrito).
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
docker exec Synap_app python manage.py test contabilidad_audit legacy_db.tests.test_cont_recalculo_dry_run legacy_db.tests.test_cont_recalculo_apply legacy_db.tests.test_cont_recalculo_anulaciones legacy_db.tests.test_cont_recalculo_rollback legacy_db.tests.test_cont_recalculo_apply_integracion --keepdb
```

## Piloto administranet89 — re-run 25/07/2026 (REC-19)

Entorno: MySQL `administranet89` @ `190.15.214.142` (piloto, **no** producción de cliente). Apply con contenedor `ENVIRONMENT=production` (`.env` base sigue en development). Empresa de sesión debe tener `base_empresa=administranet89`.

**Autorización de escritura:** el apply del lote `L20260725_175235-16b64871` se ejecutó por **shell del agente**, **no** por la UI. La vía canónica de autorización es `/contabilidad/auditoria/apply/` (checkbox de confirmación + permiso). Ese lote fue **revertido** el 25/07/2026 en una versión anterior que sí generaba backups (`rollback_lote`). Desde julio/2026 la reversión de lotes está deshabilitada. Tablero y dry-run siguen siendo solo lectura; solo apply (y eliminación de asientos) escriben en MySQL legacy.

### Baseline (solo lectura, ejercicio 1)

| Check | Diferencias |
|-------|-------------|
| `comprobante_compra_pago_sin_asiento` | **0** (idempotente post regeneración previa de 331) |
| `integridad_anulacion_compra_pago` | **81** |
| `saldo_ejercicio_vs_diario` | **90** |
| `saldo_periodo_vs_diario` | **0** |

DDL log: `apply_contabilidad_audit_correccion_log administranet89` OK. Esquema `verificar_esquema_cont` OK.

### Apply vía módulo (no script CLI)

1. Dry-run ej.1: **57** `insert_marcador` (0 bloqueados).
2. Apply producción: lote `L20260725_175235-16b64871`, **60** filas afectadas.
3. Post-apply dry-run ej.1: **0** anulaciones reparables / **0** aplicables (idempotente para el alcance).
4. Tablero post-apply (check global, sin filtro de fecha del check): **26** residuales en `integridad_anulacion_compra_pago`:
   - **18** `falta_contra_asiento` sin renglones en `cont_asiento` del cm → dry-run no propone contra (no hay original que invertir).
   - **10** `falta_marcador_…` fuera del alcance `ejercicio_seleccionado` (aparecen con política `alcance_recompute=historico`; para apply hay que **persistir** esa política en UI/Postgres — mutar el dict en shell invalida `config_hash` en apply).
5. Huérfanos: siguen en **0**. Saldos ejercicio: ~91 diffs (recompute aparte si se desea alinear; dry-run ej.1 post-repair no listó updates de saldo en esta corrida).

### Gates y fuera de alcance

- Apply exige `contabilidad.auditoria.corregir` (cualquier entorno; no se bloquea por `ENVIRONMENT`). Rollback deshabilitado.
- **No** usar `legacy_db/scripts/cont_reconstruccion_compras_pagos.py` en este ciclo (credenciales hardcodeadas).
- Fuera de auto-apply: `cierre_resultado_no_cero`, `concepto_no_normal`, `contra_no_invierte_original`, clave rota cm=0 (§6.9 VB6).

## Eliminación de asientos + recálculo de saldos

Proceso operativo para borrar asientos completos `(id_ejercicio, nro_asiento)` cuando la corrección automática del dry-run no aplica (asientos erróneos, duplicados, pruebas en piloto).

| Aspecto | Detalle |
|---------|---------|
| Servicio | `legacy_db/services/cont_eliminacion_asientos_service.py` |
| UI | `/contabilidad/auditoria/asientos/` |
| Listado | Paginado: `listar_asientos` con `page_size` por defecto **500** (máx. 500). La UI permite **Seleccionar visibles** y conservar selección entre páginas. |
| Permiso listar / preview | `contabilidad.auditoria.leer` |
| Permiso eliminar | `contabilidad.auditoria.corregir` |
| Unidad de borrado | `(id_ejercicio, nro_asiento)` — DELETE físico de **todos** los renglones |
| Backup previo | **No** (por diseño de producto: la eliminación no es revertible). Atomicidad vía una sola transacción MySQL (`DELETE` + recálculo + log). `backups_json` del lote queda `{}`. Si falla a mitad, `ROLLBACK` deshace los cambios. |
| Progreso en vivo | POST con `"stream": true` o `Accept: application/x-ndjson` → `StreamingHttpResponse` NDJSON (`type: progress` / `done` / `error`). Fases: `prepare` (primer byte inmediato) → `delete` (DELETE por lotes) → `recalc`. Carga de renglones en consulta agrupada (no N+1). UI: barra determinada con `synapShowPostLoadingProgress` + `synapUpdatePostLoadingProgress`. |
| Recálculo | Saldo teórico post-delete (excluye anulados) → UPDATE o INSERT en tablas de saldo |
| Log | `cont_audit_correccion_lote` + `cont_audit_correccion` con `check_id=eliminacion_asiento` |
| Excel del lote | Expande `valor_anterior` (lista de renglones) a **una fila por renglón**: tipo «Asiento eliminado», Nro asiento, CM, Cuenta, Debe/Haber (`$ x.xxx,xx`), «Renglón eliminado». Sin JSON en «Cambios aplicados». En UI del detalle, resumen «Asiento eliminado · N renglón(es)». |
| Empresa | Siempre la de sesión (`_base_empresa_sesion`) |

Flujo UI: filtrar → seleccionar → vista previa (POST JSON) → modal confirmación Synap → POST eliminar con barra de progreso determinada (`synapShowPostLoadingProgress` + NDJSON) → lote registrado (consultar en Lotes).

Tests:

```bash
docker exec Synap_app python manage.py test legacy_db.tests.test_cont_eliminacion_asientos contabilidad_audit.tests.test_asientos_eliminar_views --keepdb -v2
```

## Referencias

- Design original: `openspec/changes/archive/2026-07-19-contabilidad-auditoria-recalculo/`
- Delta REC-19: `openspec/changes/archive/2026-07-25-contabilidad-auditoria-anulaciones-apply/`
- Spec main: `openspec/specs/contabilidad-recalculo-correccion/spec.md`
- Hallazgos VB6: `docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md`
- Esquema verificado: `docs/general/INVENTARIO_ESQUEMA_CONT_AUDITORIA.md`
- Script CLI (legado; preferir módulo Synap): `legacy_db/scripts/cont_reconstruccion_compras_pagos.py`
