# Diseño de cambio — duplicados y validación fiscal (Compras, PASO 2)

**Metodología:** alineado a `.cursor/skills/adminnet-module-migration` (Synap = workflow y validación; legacy = escritura controlada vía adapter existente).  
**Entrada:** `docs/compras/change_analysis.md`.  
**Alcance de este documento:** diseño incremental **sin** implementación, **sin** modificar `LegacyPostingAdapter` / contrato de posting, **sin** cambiar SQL legacy ni migraciones Django.

---

## 1. Ubicación exacta del hook

**Archivo:** `factura_compra_captura/services/expediente_service.py`  
**Función:** `ExpedienteService.aprobar_expediente_con_stub`

**Insertar después de** `validate_posting_command(cmd)` (bloque `try/except PostingValidationError` que hoy traduce a `TransicionEstadoInvalida`).

**Insertar antes de** `adapter.preflight(cmd)`.

**Motivo:**

- Reutiliza el `LegacyPostingCommandV1` ya construido (`map_expediente_to_command_v1` + `validate_posting_command`), coherente con cabecera, líneas y reglas V-*.
- Falla antes de cualquier interacción con el adapter (fake, noop futuro desbloqueado, o legacy), cumpliendo “solo interceptar antes del posting” sin tocar el adapter.
- Cubre ambos entrypoints (`POST …/aprobar/` y transición `simular_posting_exitoso`) sin duplicar lógica.

**Orden obligatorio dentro del hook:**

1. **`ApprovalValidationOrchestrator.run(...)`** (recomendado, ver §2.4) — internamente ejecuta duplicados y luego fiscal en ese orden; o bien las dos llamadas explícitas si se omite el orquestador.
2. `adapter.preflight(cmd)` (sin cambios).
3. `adapter.execute(cmd)` (sin cambios).

---

## 2. Interfaces de servicios

Convención: tipos de retorno inmutables o dataclasses simples; los servicios puros **no** persisten; la persistencia de `metadata` en bloqueo la concentra `aprobar_expediente_con_stub` (o el orquestador, según implementación) siguiendo §6.

### 2.1 `DuplicateDetectionService`

**Ubicación propuesta (paquete):** `factura_compra_captura/services/duplicate_detection.py` (o submódulo `validation/` si se agrupa con fiscal).

| Método | Descripción |
|--------|-------------|
| `check_for_approval(expediente, cmd, *, exclude_expediente_id: UUID \| None = None) -> DuplicateCheckResult` | Evalúa duplicados **antes** de aprobar. `cmd` es `LegacyPostingCommandV1` (solo lectura). |

**Inputs:**

- `expediente`: `ExpedienteFacturaCompra` (estado ya validado como `aprobacion_solicitada`).
- `cmd`: `LegacyPostingCommandV1` — fuente normalizada de PV, tipo, número, proveedor, fechas, totales según mapper v1.
- `exclude_expediente_id`: opcional; por defecto el `expediente.id` para no contarse a sí mismo en búsquedas Synap.

**Output: `DuplicateCheckResult` (conceptual)**

- `status`: enum lógico — p. ej. `CLEAR`, `POSSIBLE_DUPLICATE_SYNAP`, `POSSIBLE_DUPLICATE_LEGACY` (solo si hay puerto configurado), `BLOCKED`.
- `reason_codes`: lista de códigos estables para API y tests (`duplicate_synap_same_key`, `duplicate_synap_semantic`, `duplicate_legacy_count`, …).
- `details`: dict serializable (ids de expedientes candidatos, clave semántica usada, conteos) para persistir en `metadata` (§6).
- `blocking`: `bool` — si `True`, la aprobación debe abortarse con `TransicionEstadoInvalida`.

**Puerto opcional (inyección en PASO 4, no en adapter):**

- `LegacyDuplicateReadPort.count_matches(cmd, base_empresa) -> int` — implementación futura que ejecute **solo lecturas** acordadas con auditoría VB6/SQL existente; si no se configura, el servicio opera solo en modelo Synap.

### 2.2 Clave lógica de duplicado (índice semántico, estilo AdministraNET)

Objetivo: alinear la detección con **criterio legacy (VB6)**, evitando falsos negativos por formato distinto o por usar identificadores que el ERP no usa para la misma regla.

**Componentes de la clave (prioridad legacy):**

| Campo | Regla |
|-------|--------|
| Proveedor | **`codigo_proveedor_legacy`** del expediente (código interno AdministraNET). **No** usar CUIT como clave principal de duplicado si el legacy valida por código de proveedor. |
| Tipo comprobante | Valor **legacy / AFIP** ya presente en `cmd` o `posting_v1.header` (el que use el mapper y el posting); documentar el mismo mapeo que `Validacion_Comp` / auditoría VB6. |
| Punto de venta | Entero normalizado (`int`), sin ceros a la izquierda inconsistentes: normalizar a entero desde string si aplica. |
| Número de comprobante | Normalización **estilo VB6**: trim, quitar separadores decorativos si existen, **padding coherente** con lo que persiste legacy (p. ej. ancho fijo de número según convención de la base; definir una función única `normalize_nro_comprobante` en implementación y testearla contra casos reales). |

**Consultas Synap:** filtrar expedientes de la **misma `empresa_id`**, mismos cuatro componentes normalizados, excluyendo el expediente actual y, según política, solo estados que importen (`aprobado`, `aprobacion_solicitada`, etc.).

**Puerto legacy:** si existe, debe usar la **misma clave normalizada** (o SQL que replique la misma semántica auditada), no otra definición paralela.

### 2.3 `FiscalInvoiceValidationService`

**Ubicación propuesta:** `factura_compra_captura/services/fiscal_invoice_validation.py`.

| Método | Descripción |
|--------|-------------|
| `validate_for_approval(expediente, cmd, *, base_empresa: str \| None) -> FiscalValidationResult` | Valida coherencia fiscal / AFIP-ARCA antes de posting. |

**Inputs:**

- `expediente`, `cmd`: mismos que arriba.
- `base_empresa`: string nombre de base AdministraNET para `get_fe_config` / WSAA+WSFE; ver §5 si es `None`.

**Output: `FiscalValidationResult` (conceptual)**

- `status`: ver alcance v1 en §5.3 (`SKIPPED_NO_CAE`, `SKIPPED_NON_AR`, `SKIPPED_NO_CONFIG` solo cuando aplica según §5.3, `VALID`, `INVALID`, `ERROR_TRANSIENT`).
- `reason_codes`: lista (`fiscal_cae_mismatch`, `fiscal_comprobante_not_found`, …). QR u otras verificaciones totales **quedan fuera del alcance v1** (§5.3).
- `details`: dict (cae consultado, vencimiento, observaciones AFIP sanitizadas, fragmentos no sensibles).
- `blocking`: **derivado de forma determinística** según §4.5 (no dejar a criterio del implementador).

**Nota de diseño:** el servicio **no** importa `pyafipws` directamente si existe un adaptador delgado en `self_checkout` o módulo compartido; ver §5.

### 2.4 `ApprovalValidationOrchestrator` (recomendado)

**Ubicación propuesta:** `factura_compra_captura/services/approval_validation.py` (nombre ajustable).

| Método | Descripción |
|--------|-------------|
| `run(expediente, cmd, *, base_empresa: str \| None) -> ApprovalValidationResult` | Ejecuta en orden: duplicados → fiscal; devuelve resultado unificado. |

**Output conceptual `ApprovalValidationResult`:**

- `ok: bool` — `True` solo si ningún paso bloqueante falló.
- `blocking_step: str | None` — `"duplicate"` \| `"fiscal"` \| `None`.
- `codigo: str | None` — código estable para `TransicionEstadoInvalida` (ej. `duplicate_factura_synap`).
- `message: str` — texto usuario.
- `duplicate: DuplicateCheckResult | None`
- `fiscal: FiscalValidationResult | None`

**Ventajas:** `aprobar_expediente_con_stub` permanece delgado; tests de integración mockean un solo punto; orden y política de blocking centralizados.

---

## 3. Flujo de ejecución completo

```text
POST /api/compras/expedientes/<uuid>/aprobar/
  (o transición simular_posting_exitoso → mismo núcleo)

aprobar_expediente_con_stub:
  1. Validar estado aprobacion_solicitada
  2. Rechazar si backend noop (sin cambio)
  3. get_posting_adapter()  [sin cambio en contrato]
  4. map_expediente_to_command_v1 → cmd
  5. validate_posting_command(cmd)
  6. [NUEVO] Resolver base_empresa (§5.2)
  7. [NUEVO] validation = ApprovalValidationOrchestrator.run(expediente, cmd, base_empresa=...)
     (equivalente: DuplicateDetectionService → FiscalInvoiceValidationService, mismo orden)
  8. [NUEVO] Si not validation.ok:
         → merge de `compras_validacion` en `expediente.metadata` (§6)
         → expediente.save(update_fields=["metadata"])   # §6.1: savepoint / atomic según proyecto
         → raise TransicionEstadoInvalida(validation.message, codigo=validation.codigo)
  9. [NUEVO] Si validation.ok: opcional merge de validación ok en metadata antes del posting
 10. adapter.preflight(cmd)   [sin cambio]
 11. adapter.execute(cmd)     [sin cambio]
 12. Persistir expediente (estado, legacy_*, posting_*), evento, log [save de éxito actual]
```

**Transacción:** ver §6.1: el `metadata` en fallo debe persistir aunque se lance excepción; no alcanza con un único `atomic` externo sin savepoint o patrón equivalente.

---

## 4. Manejo de errores

### 4.1 Contrato hacia la API

Mantener el patrón actual: `TransicionEstadoInvalida` → `400` con `detail` y `codigo`.

**Códigos nuevos sugeridos (estables para cliente y tests):**

| Código | Origen |
|--------|--------|
| `duplicate_factura_synap` | Duplicado claro en expedientes Synap |
| `duplicate_factura_legacy` | Conteo legacy > 0 (si puerto activo) |
| `fiscal_afip_invalid` | Datos no coinciden con AFIP / comprobante inválido |
| `fiscal_afip_not_configured` | Sin certificados/config para `base_empresa` cuando la política exige validación |
| `fiscal_afip_unavailable` | Error transiente (red, WSAA, timeout) — ver §8 |
| `fiscal_validation_skipped` | No usar como error; solo estado en metadata si aplica |

### 4.2 Prioridad de fallo

1. Validaciones ya existentes (`PostingValidationError`).
2. Duplicados (evitar trabajo fiscal si ya está bloqueado por duplicado).
3. Fiscal.
4. Preflight del adapter (comportamiento legacy del módulo posting).

### 4.3 Mensajes usuario

- Texto en español, sin filtrar secretos; truncar observaciones AFIP como ya hace `fe_sync` (`[:300]`).

### 4.4 Errores transitorios AFIP

**Default de producto:** modo **estricto** (tabla §4.5). Modo degradado solo con flag explícito (`FACTURA_COMPRA_FISCAL_ALLOW_TRANSIENT_FAILURE` o similar), documentado en runbook.

### 4.5 Tabla determinística: `status` → `blocking`

Regla obligatoria para implementación: **`blocking` se calcula solo con esta tabla** (más el flag opcional de §4.4 solo para `ERROR_TRANSIENT`).

#### `DuplicateDetectionService` (`DuplicateCheckResult.status`)

| `status` | `blocking` | Notas |
|----------|------------|--------|
| `CLEAR` | `False` | Sin colisiones según clave §2.2. |
| `POSSIBLE_DUPLICATE_SYNAP` | `False` | Heurística / similitud; no bloquea aprobación en v1 salvo decisión de producto futura (si en el futuro se bloquea, renombrar a `BLOCKED_*`). |
| `POSSIBLE_DUPLICATE_LEGACY` | `False` | Mismo criterio: posible ≠ bloqueado. |
| `BLOCKED` | `True` | Duplicado confirmado (Synap y/o legacy según política); lanzar `TransicionEstadoInvalida` con código estable. |

#### `FiscalInvoiceValidationService` (`FiscalValidationResult.status`)

| `status` | `blocking` | Notas |
|----------|------------|--------|
| `VALID` | `False` | CAE comprobado contra AFIP (§5.3). |
| `SKIPPED_NO_CAE` | `False` | No hay CAE en datos capturados → **no** se exige consulta AFIP (§5.3). |
| `SKIPPED_NON_AR` | `False` | Comprobante / empresa fuera del alcance WSFE v1. |
| `SKIPPED_NO_CONFIG` | `False` | Reservado para “sin CAE / no aplica FE” donde no se requiere config WSFE (alineado a §5.3: sin CAE no se llama AFIP). |
| `INVALID` | `True` | Incluye: CAE presente y no coincide AFIP; comprobante no encontrado; **hay CAE y falta `base_empresa` o FE no configurado** (`fiscal_afip_not_configured`). |
| `ERROR_TRANSIENT` | `True` | **Modo estricto (default):** AFIP no responde / timeout / error de red. Código API: `fiscal_afip_unavailable`. |
| `ERROR_TRANSIENT` | `False` | **Solo** si flag degradado §4.4 está activo (documentar riesgo). |

**Orquestador:** `ApprovalValidationResult.ok` es `False` si **cualquier** paso devuelve `blocking=True` (prioridad de mensaje/código: primero duplicado si ambos fallaran; en la práctica se corta tras duplicado bloqueante sin llamar fiscal).

---

## 5. Integración con PyAfipWs

### 5.1 Funciones a reutilizar (no duplicar)

| Función / módulo | Uso en Compras |
|------------------|----------------|
| `self_checkout.fe_sync.consultar_cae_comprobante(base_empresa, pto_vta, tipo_comprobante, nro_comprobante)` | Verificar existencia y recuperar CAE / vencimiento para el comprobante declarado en cabecera (equivalente venta: consulta FECompConsultar). |
| `self_checkout.fe_sync.get_ultimo_autorizado_afip` | Opcional: contrastar numeración si hay política de rango (no sustituye duplicados en Synap). |
| `self_checkout.fe_config.is_fe_configured`, `get_fe_config` | Saber si hay certificados y CUIT emisor **de la empresa receptora** en Synap (comprador) para autenticar WSFE. |

**No reutilizar como núcleo de compras:** `invoice_service` emisión (`CAESolicitar`) — flujo de **venta**; para compras basta consulta y cruce de datos salvo requisito futuro distinto.

**QR:** fuera del alcance **v1** (§5.3). Una fase posterior puede parsear QR solo para **rellenar** CAE / PV / número y reutilizar la misma rama “hay CAE”.

### 5.2 Mapeo `Empresa` (Synap) → `base_empresa`

**Estado actual:** `core.models.Empresa` no expone `base_empresa` como campo dedicado; `base_empresa` vive en sesión de login AdministraNET y en servicios MySQL.

**Estrategia de diseño (sin migración en esta fase):**

1. **Primario — sesión request (flujo web):** si `aprobar_expediente_con_stub` recibe contexto de request (extensión opcional del firma en implementación: `request` o `base_empresa` explícito pasado desde la vista), usar el mismo `base_empresa` que `RequestScopedMysqlMiddleware` / login.
2. **Secundario — metadata del expediente:** clave acordada p. ej. `metadata["compras"]["base_empresa"]` o bajo `posting_v1.context`, establecida al crear/editar expediente en entornos API-only.
3. **Terciario — setting de mapeo:** `FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID = { 1: "administranet92", ... }` para jobs/tests.
4. **Resolver central:** función pura `resolve_base_empresa_for_compras(expediente, request=None) -> str | None` documentada; **una sola** responsabilidad para PASO 4.

**Regla:** si `base_empresa` es `None` **y** el expediente declara CAE a validar (§5.3), entonces `blocking=True` y código `fiscal_afip_not_configured`. Si **no** hay CAE, la fiscal puede quedar en `SKIPPED_NO_CAE` sin necesidad de `base_empresa` para WSFE.

**Alineación AdministraNET:** el pool MySQL ya usa `base_empresa` como nombre de base; cualquier lectura legacy futura para duplicados debe usar el mismo resolvedor.

### 5.3 Alcance mínimo fiscal (v1) — no es “verificación total”

Muchas facturas de compra **no** podrán contrastarse con AFIP (sin CAE, papel, importador, etc.). El servicio **no** debe bloquear la operación en esos casos.

| Condición | Comportamiento |
|-----------|----------------|
| **No hay CAE** en los datos disponibles (`posting_v1.header` / metadata acordada) | `SKIPPED_NO_CAE`, `blocking=False`. No llamar a WSFE por este motivo. |
| **Hay CAE** (y tipo + PV + número suficientes para `consultar_cae_comprobante`) | Llamar AFIP; cruzar CAE devuelto con el capturado; `VALID` o `INVALID`. |
| **Hay CAE** pero falta `base_empresa` o `is_fe_configured` es falso | `INVALID` (o código dedicado interno), **`blocking=True`**, API `fiscal_afip_not_configured` — no aprobar sin poder comprobar un CAE declarado. |
| **AFIP no responde** (error transitorio) | `ERROR_TRANSIENT`, `blocking=True` en modo estricto (§4.5). |

**Resumen regla de negocio:** solo cuando existe CAE explícito se exige consulta exitosa a AFIP; sin CAE, no fricción; sin respuesta AFIP cuando debía validarse, bloqueo en modo estricto.

---

## 6. Persistencia

**Sin migraciones nuevas:** usar solo `ExpedienteFacturaCompra.metadata` (JSON).

**Namespace sugerido:** `metadata["compras_validacion"]` (o `compras.validacion` anidado) para no pisar `posting_v1`.

**Estructura conceptual (versiónada):**

```json
{
  "compras_validacion": {
    "version": 1,
    "updated_at": "ISO-8601",
    "duplicate": {
      "status": "clear|possible|blocked",
      "reason_codes": [],
      "details": {}
    },
    "fiscal": {
      "status": "skipped_no_cae|skipped_non_ar|skipped_no_config|valid|invalid|error_transient",
      "reason_codes": [],
      "details": {}
    }
  }
}
```

### 6.1 Persistencia en bloqueo (orden fijo, sin mezclar con save de éxito)

**Objetivo:** que el operador vea en UI el resultado de la última validación fallida, sin aprobar el expediente y **sin** depender del mismo `save` que setea `estado=aprobado`.

**Secuencia obligatoria cuando `not validation.ok`:**

1. Construir en memoria el dict `compras_validacion` (duplicate + fiscal) y hacer **merge** sobre `expediente.metadata` preservando otras claves.
2. `expediente.save(update_fields=["metadata"])`.
3. `raise TransicionEstadoInvalida(...)`.

**No** usar el `save` del camino exitoso (que incluye `estado`, `legacy_*`, `posting_*`) para el bloqueo.

**Transacciones Django:** un único `transaction.atomic()` que envuelve validación + `save(metadata)` + `raise` hace **rollback de todo** al propagarse la excepción, **incluido** el `save` del metadata. Los **savepoints** siguen perteneciendo a la misma transacción: si el bloque exterior hace rollback, **también** se pierde lo guardado tras `savepoint_commit`.

Para **garantizar** trazabilidad en fallo, el PASO 4 debe usar **una** estrategia que produzca **commit confirmado** antes del `raise`, por ejemplo:

- **Transacción independiente:** helper que abre `atomic()` (o usa conexión default), hace solo `save(update_fields=["metadata"])`, **sale del contexto con éxito** (commit) y **después** se lanza `TransicionEstadoInvalida` **fuera** de ese `atomic`, **o**
- **Reestructurar** el `@transaction.atomic` de `aprobar_expediente_con_stub`: no envolver el tramo “validación + persistir metadata de fallo”; reservar `atomic` solo al bloque `preflight + execute + save` de éxito (evaluar impacto y tests).

Documentar la variante elegida en `docs/compras/` (runbook).

**Camino exitoso:** merge opcional de `compras_validacion` en el `save` final junto con estado/posting, o un solo save intermedio solo si se requiere auditoría previa al `execute` (menos habitual).

**Campos diferidos (futuro):** `duplicate_status`, `fiscal_validation_status` en columnas dedicadas quedan fuera de este PASO; cuando se migren, pueden alimentarse desde el mismo bloque JSON para backfill.

---

## 7. Impacto en API

| Área | Cambio |
|------|--------|
| `POST …/aprobar/` | Mismos códigos HTTP; nuevos `codigo` en `400` (§4.1). |
| `GET/PATCH expediente` | `ExpedienteFacturaCompraSerializer`: exponer lectura de `compras_validacion` (solo lectura, anidado opcional `validacion_compras`) para UI y clientes API. |
| OpenAPI / documentación | Describir códigos de error nuevos en `docs/compras/`. |
| Permisos | Sin cambio; sigue `ExpedienteAprobarPermission`. |
| Throttling | Sin cambio salvo que las validaciones aumenten latencia; monitorear AFIP. |

**Compatibilidad:** clientes que ignoran `metadata` siguen funcionando; clientes que parsean solo `estado` verán que la aprobación falla con nuevo `codigo`.

---

## 8. Casos borde

| Caso | Tratamiento diseñado |
|------|----------------------|
| Empresa no Argentina / comprobante no WSFE | `SKIPPED_NON_AR`, `blocking=False`. |
| Hay CAE pero faltan tipo/PV/número para consultar | `INVALID` o `fiscal_afip_not_configured` según implementación — **bloquear** si hay CAE y no se puede completar la consulta. **Sin CAE:** `SKIPPED_NO_CAE`, no bloquear. |
| CAE en metadata OCR distinto del devuelto por AFIP | `INVALID` / `fiscal_cae_mismatch`, `blocking=True`. |
| Comprobante no encontrado en AFIP | `fiscal_afip_invalid` / código específico `comprobante_not_found`. |
| Dos expedientes mismo proveedor y número, uno ya `aprobado` | DuplicateDetectionService debe considerar estados `aprobado` y posiblemente `error_posting` según política. |
| Mismo expediente reintentando aprobación | Excluir `expediente.id` en consultas Synap. |
| `FACTURA_COMPRA_POSTING_BACKEND=fake` | Las nuevas validaciones **sí** se ejecutan (interceptación antes del adapter); solo el execute sigue siendo simulado. |
| Concurrencia: dos aprobaciones simultáneas | Misma transacción + `select_for_update` del expediente en implementación si hace falta; riesgo de doble posting legacy mitigado en capa Synap por estado. |
| AFIP lento o caído | §4.5: `ERROR_TRANSIENT`, `blocking=True` (estricto) salvo flag §4.4. |
| `base_empresa` incorrecto en metadata | Mismo que no configurado: fallo claro, sin tocar adapter. |
| Lectura legacy duplicados | Solo vía puerto explícito; sin SQL nuevo en posting; auditoría ADR/VB6 previa obligatoria (skill: no inventar comportamiento). |

---

## Relación con PASO 3 (TDD)

Antes de implementar: tests unitarios de `DuplicateDetectionService` y `FiscalInvoiceValidationService` con doubles del puerto legacy y del consultor AFIP; tests de `ApprovalValidationOrchestrator` (orden y prioridad de códigos); tests de flujo en `aprobar_expediente_con_stub` con adapter fake y orquestador mockeado; tests de tabla §4.5 (cada `status` → `blocking` esperado); tests de persistencia §6.1 (metadata tras fallo).

---

## Referencias

- `docs/compras/change_analysis.md`
- `factura_compra_posting/contracts.py` (adapter intocable en este diseño)
- `self_checkout/fe_sync.py`, `self_checkout/fe_config.py`

**Fin PASO 2 — solo diseño.**
