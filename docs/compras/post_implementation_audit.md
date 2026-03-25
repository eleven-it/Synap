# Auditoría post-implementación — duplicados y validación fiscal (Compras)

**Rol:** staff engineer / auditor técnico senior.  
**Alcance:** `DuplicateDetectionService`, `FiscalInvoiceValidationService`, integración en `aprobar_expediente_con_stub`.  
**Excluido:** `LegacyPostingAdapter`, SQL legacy, `posting_contract` (solo verificación de que no se modificaron en este alcance).  
**Fecha:** revisión sobre código del repositorio (estado actual).

**Hardening posterior (cerrado):** transiciones pasan `request` hasta `aprobar_expediente_con_stub`; mensajes `"AFIP no configurado"` / `"pyafipws no instalado"` → `fiscal_afip_not_configured`; tipo **FM** omite consulta WSFE (`fiscal_skip_tipo_fm`); `select_for_update` + revalidación de estado al aprobar; `approval_validation.py` reducido a nota (sin `NotImplementedError`). Ver `desarrollo/fase_validacion_dup_fiscal_result.md`.

---

## 1. Resumen ejecutivo

| Dimensión | Valoración |
|-----------|------------|
| **Correctitud funcional core** | **OK** para el camino principal: duplicados Synap + CAE opcional + `consultar_cae_comprobante`, orden duplicate → fiscal → preflight. |
| **Completitud vs diseño** | **RISK**: no se persiste `compras_validacion` en fallo (§6.1 `change_design.md`); `ApprovalValidationOrchestrator` sigue como stub; `SKIPPED_NON_AR` no se usa. |
| **Placeholders** | **RISK**: `NotImplementedError` en `approval_validation.py` (módulo huérfano si alguien lo invoca). |
| **Producción** | **RISK** (no **BLOCKER** global): asimetría transición vs API, clasificación fiscal de algunos errores AFIP, tipo **FM** vs mapeo WSFE, condición de carrera en duplicados, ausencia de `error_posting` en estados de colisión. |

**Estado general:** **RISK** — apto para entornos controlados y flujos cubiertos por tests; **no** catalogado como “listo producción sin condiciones” hasta cerrar hallazgos importantes según criticidad del negocio.

---

## 2. Hallazgos críticos (BLOCKERS)

*Criterio: impedir uso seguro en producción o incumplir reglas explícitas de gobierno.*

**Ninguno estricto** si se asume:

- Aprobación principal vía `POST …/aprobar/` con sesión `user.base_empresa` o mapeo `FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID` / `metadata.compras.base_empresa`.
- Carga operativa baja/mediana donde la ventana de carrera en duplicados es aceptable.

Si el negocio exige **cero duplicados concurrentes** o **100 % coherencia de códigos API** frente a AFIP no configurado, los ítems de la sección 3 pasan a tratarse como **BLOCKER**.

---

## 3. Hallazgos importantes

### 3.1 Transición `simular_posting_exitoso` sin `request` ni `base_empresa`

- **Archivo:** `factura_compra_captura/services/expediente_service.py` (aprox. L254–256).
- **Hecho:** `aplicar_transicion(..., "simular_posting_exitoso")` llama `aprobar_expediente_con_stub(expediente, actor=actor)` **sin** `request` ni `base_empresa`.
- **Impacto:** Con CAE + `pto_vta_afip` + `nro_cbte_afip` en metadata, `resolve_base_empresa_for_compras` suele devolver `None` (salvo mapeo/metadata). Resultado: **`fiscal_afip_not_configured`** y bloqueo, mientras que el mismo expediente aprobado vía **`ExpedienteAprobarAPIView`** (pasa `request=request`) puede resolverse por sesión.
- **Riesgo:** Dos comportamientos distintos según endpoint (`/transiciones/` vs `/aprobar/`). La UI de revisión usa `/aprobar/` (L383–384 `revision_expediente.html`), lo que **mitiga** el riesgo para ese flujo; clientes API u otros frontends que solo usen `simular_posting_exitoso` quedan expuestos.

### 3.2 Clasificación fiscal: “AFIP no configurado” / `pyafipws no instalado`

- **Archivo:** `factura_compra_captura/services/fiscal_invoice_validation.py` (L135–158).
- **Hecho:** Cualquier `err` de `consultar_cae_comprobante` que **no** coincida con heurística transitoria (`timeout`, `network`, `wsaa`, `wsfe`, `conexión`, `temporal`) se trata como **`fiscal_afip_invalid`**.
- **Impacto:** Mensajes reales de `fe_sync` como `"AFIP no configurado"` o `"pyafipws no instalado"` devuelven código **`fiscal_afip_invalid`**, no **`fiscal_afip_not_configured`** / distinción operativa del diseño (§4.1 `change_design.md`).
- **Riesgo:** Monitoreo, soporte y clientes que bifurcan por `codigo` reciben señal incorrecta.

### 3.3 Tipo comprobante **FM** y `TIPO_CBTE_AFIP`

- **Archivos:** `fiscal_invoice_validation.py` (L122–124); `self_checkout/fe_sync.py` (`TIPO_CBTE_AFIP`, L14; uso L96).
- **Hecho:** El servicio puede pasar `tipo_comprobante="FM"` a `consultar_cae_comprobante`. En `fe_sync`, **`FM` no está en el mapa** y cae al default numérico de **FB (6)**.
- **Impacto:** Consulta AFIP con tipo CBTE potencialmente **incorrecto** para comprobantes FM.
- **Riesgo:** Falsos “no encontrado” o datos inconsistentes en escenarios FM reales.

### 3.4 Condición de carrera en duplicados

- **Archivo:** `duplicate_detection.py` (consulta + bucle L82–102).
- **Hecho:** Dos solicitudes concurrentes, mismo `(empresa, proveedor, tipo, nro_norm)`, ambas en `aprobacion_solicitada`, pueden leer la BD **antes** de que la otra pase a `aprobado` y **ambas** superar la comprobación de duplicados.
- **Impacto:** Dos expedientes **aprobados** Synap con la misma clave lógica (el posting legacy/stub puede ejecutarse dos veces en sentido de negocio).
- **Riesgo:** Medio/alto según concurrencia y política de “una sola factura por clave”.

### 3.5 Estados fuera de la ventana de duplicados

- **Archivo:** `duplicate_detection.py` (`_ESTADOS_DUPLICADO`, L67–70).
- **Hecho:** Solo `aprobado` y `aprobacion_solicitada`. No incluye `error_posting` (ni otros) documentados como posibles en `change_design.md` §8.
- **Impacto:** Tras error de posting, un segundo expediente con la misma clave podría aprobarse sin colisión con el que quedó en `error_posting`.
- **Riesgo:** Depende de si `error_posting` se usa en producción y si la regla de negocio exige bloquear frente a ese estado.

### 3.6 Persistencia `compras_validacion` en fallo no implementada

- **Archivo:** `expediente_service.py` — en bloqueo por duplicado/fiscal solo se hace `raise`, sin merge a `metadata["compras_validacion"]`.
- **Documentado en:** `docs/compras/desarrollo/fase_validacion_dup_fiscal_result.md` como fuera de fase.
- **Impacto:** Tras rechazo por validación, **no** queda huella versionada en metadata para UI/soporte según diseño §6.1.
- **Riesgo:** UX y auditoría interna degradadas; no afecta integridad del posting si la transacción revierte correctamente.

---

## 4. Hallazgos menores

| # | Tema | Ubicación | Nota |
|---|------|-----------|------|
| M1 | Enum `DuplicateCheckStatus` con valores no usados (`POSSIBLE_*`) | `duplicate_detection.py` | Sin lógica “posible duplicado”; solo `CLEAR` / `BLOCKED` en la práctica. |
| M2 | `SKIPPED_NON_AR` nunca retornado | `fiscal_invoice_validation.py` | Coherente con alcance v1; deuda si se internacionaliza o se excluye no-AR explícitamente. |
| M3 | `cmd` en `validate_for_approval` casi no usado salvo `tipo_factura` | `fiscal_invoice_validation.py` | Aceptable; evita divergencia futura si cabecera fiscal se desacopla del comando. |
| M4 | `except Exception` al leer sesión | `fiscal_invoice_validation.py` L60–63 | Amplio pero acotado a `request.session`; riesgo bajo de enmascarar bugs. |
| M5 | Bucle Python sobre candidatos (N filas) | `duplicate_detection.py` | Escalable a mediano volumen; en miles de expedientes por empresa convendría query/índice dedicado (no auditado aquí en schema). |
| M6 | `ApprovalValidationOrchestrator` sin implementar | `approval_validation.py` L36–38 | No referenciado por el flujo actual; confusión para mantenedores. |

---

## 5. Deuda técnica detectada

1. **Orquestador declarado en diseño, no cableado** — `change_design.md` §2.4 vs código en `expediente_service`.
2. **Metadata de validación** — estructura `compras_validacion` no escrita en éxito ni fallo.
3. **Duplicidad de helpers** — `_posting_header_dict` duplicado en `duplicate_detection.py` y `fiscal_invoice_validation.py`.
4. **Heurística “transitorio vs inválido”** — basada en substrings del mensaje de error AFIP; frágil ante cambios de texto en `fe_sync` o AFIP.
5. **Tests de flujo fiscal** — dependen de `base_empresa="base_tdd_fiscal"` explícito (`test_validation_phase3_5.py`); documentado pero no refleja solo “sesión real”.
6. **`FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID`** — dict vacío por defecto; operación real requiere configuración explícita o sesión.

---

## 6. Recomendaciones concretas

1. **Unificar entrada de aprobación:** pasar `request` desde `TransicionSerializer.save` / vista de transiciones hacia `aplicar_transicion` y de ahí a `aprobar_expediente_con_stub`, **o** documentar que `simular_posting_exitoso` no soporta CAE sin `metadata.compras.base_empresa` / mapeo, y deprecar ese camino para aprobación con FE.
2. **Mapeo explícito de errores `fe_sync`:** si `err` contiene `"AFIP no configurado"` / `"pyafipws no instalado"`, devolver `reason_codes` y `codigo` API alineados a `fiscal_afip_not_configured` (o código dedicado).
3. **FM:** alinear con `TIPO_CBTE_AFIP` (ampliar mapa en `fe_sync` compartido o normalizar FM a código AFIP correcto antes de consultar).
4. **Carrera en duplicados:** `select_for_update` del expediente actual y/o índice único parcial en BD (diseño de migración fuera de este informe) o validación única a nivel aplicación con bloqueo.
5. **Estados:** valorar incluir `error_posting` (y definición de negocio) en `_ESTADOS_DUPLICADO`.
6. **Eliminar o implementar** `ApprovalValidationOrchestrator.run` para no dejar `NotImplementedError` en árbol de producción.
7. **Metadata en fallo:** implementar §6.1 con transacción auxiliar o reestructuración de `@atomic` según `change_design.md`.
8. **Tests:** añadir caso `simular_posting_exitoso` con CAE y sesión/mocking de `base_empresa` para fijar contrato del endpoint de transición.

---

## 7. Veredicto final

**No “production-ready” incondicional** — calificación: **condicional / RISK**.

- **Sí** es coherente con las reglas de arquitectura: interceptación **solo** antes de `preflight`, sin tocar adapter legacy ni SQL.
- **Sí** la implementación principal **no** es un placeholder: lógica real en duplicados y fiscal (salvo módulo orquestador huérfano).
- **No** cumple al 100 % el diseño documentado (metadata, orquestador, granularidad de códigos fiscales, FM, carrera).

**Recomendación:** habilitar en producción tras: (a) decisión sobre transición vs `/aprobar/` y CAE; (b) corrección o aceptación explícita de FM y clasificación de errores AFIP; (c) política de concurrencia/duplicados acorde al volumen; (d) retirar o completar `approval_validation.py`.

---

## Anexos de auditoría por paso solicitado

### PASO 1 — Placeholders / TODO / hardcodes

| Archivo | Línea / símbolo | Hallazgo | Impacto |
|---------|-----------------|----------|---------|
| `factura_compra_captura/services/approval_validation.py` | L36–38 | `NotImplementedError` en `ApprovalValidationOrchestrator.run` | Bajo si no se importa; confusión y fallo si se usa. |
| `factura_compra_captura/ocr/factory.py` | L19+ | `NotImplementedError` en factory OCR | Fuera del alcance validación compras; no bloquea esta feature. |
| `fiscal_invoice_validation.py` | Heurística `err_l` | “Hardcode” de palabras clave para transitorio | Frágil ante cambios de mensajes. |
| `django_project/settings.py` | `FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID = {}` | Default vacío | Requiere configuración operativa para CAE + API sin sesión. |

*Búsqueda orientativa:* no se reportan `TODO`/`FIXME` en los tres módulos de validación analizados.

### PASO 2 — Duplicados (checklist)

1. **¿CUIT vs proveedor legacy?** — Sí usa `codigo_proveedor_legacy` / `cmd.header.codigo_proveedor`; **no** usa CUIT en la clave. ✔  
2. **¿Normaliza nro?** — `strip`, mayúsculas, colapso de espacios; **no** elimina guiones ni variantes `0001` vs `1` dentro del string formateado (p. ej. otro patrón de comprobante podría no unificar). Parcialmente ✔ / riesgo de falso negativo en formatos no cubiertos por tests.  
3. **¿Excluye expediente actual?** — Sí (`exclude_expediente_id` con default `expediente.id`). ✔  
4. **¿Variantes de formato?** — Cubiertas por tests (case, espacios laterales). ✔ en ese subconjunto.  
5. **¿Estados?** — `aprobado`, `aprobacion_solicitada` únicamente; ver §3.5.  
6. **¿Falsos positivos/negativos?** — Positivo: clave vacía o proveedor 0 si algún flujo lo permitiera. Negativo: formatos distintos semánticamente iguales no normalizados; carrera concurrente (§3.4).

### PASO 3 — Fiscal (AFIP)

1. **Uso de `consultar_cae_comprobante`** — Firma correcta `(base_empresa, pto_vta, tipo, nro)`; coherente con `fe_sync`. ✔ con reserva FM (§3.3).  
2. **CAE válido / inexistente / caída** — Cubierto por lógica y tests; transitorio por heurística de texto.  
3. **Sin CAE no bloquea** — Sí, retorno `SKIPPED_NO_CAE`, `blocking=False`. ✔  
4. **OCR** — CAE leído de `metadata.posting_v1.header` (misma fuente que edición humana/API); la validación **no** confía solo en OCR sin cruce AFIP: compara con respuesta WSFE. Riesgo residual: usuario introduce CAE incorrecto a propósito → bloqueo por mismatch o inválido (correcto).  
5. **`base_empresa`** — Resolución por metadata, mapping, sesión; ver §3.1.

### PASO 4 — Integración flujo

1. **Después de `validate_posting_command`** — Sí (L169–175 vs L177+). ✔  
2. **Antes de `preflight`** — Sí (L177–207 vs L209+). ✔  
3. **Orden duplicate → fiscal → posting** — Sí. ✔  
4. **`TransicionEstadoInvalida`** — Duplicado: mensaje fijo + `duplicate_factura_synap`. Fiscal: primer `reason_code` o default. ✔ con matiz §3.2.  
5. **Flujo existente** — Sin CAE, comportamiento previo preservado en esencia; con CAE sin base, nuevo bloqueo (esperado por diseño).

### PASO 5 — Transacciones

1. **`@transaction.atomic`** en `aprobar_expediente_con_stub` — Sí; el `raise` tras validación revierte el atomic completo (incl. cualquier save intermedio no hecho). ✔ para consistencia “no aprobar”.  
2. **Metadata en éxito/fallo** — No se actualiza `compras_validacion`; el `save` final solo en camino exitoso. Fallo: sin persistencia de diagnóstico.  
3. **Writes parciales** — No hay save parcial antes del raise en el código actual → no hay estado “a medias” en PostgreSQL por esta ruta.  
4. **Doble posting** — Mitigado por estado y duplicados en caso secuencial; **no** garantizado bajo carrera (§3.4).

### PASO 6 — Metadata estructura

- **`compras_validacion`:** no escrita por el código productivo actual.  
- **Serializers:** `ExpedienteFacturaCompraSerializer` expone `metadata` genérico; no hay campo dedicado ni validación de subesquema `compras_validacion`.  
- **Fragilidad:** baja mientras no se escriba; al implementar, conviene `version` + `updated_at` como en diseño.

### PASO 7 — Tests

- **Suite** `tests/compras/test_validation_phase3_5.py`: duplicados (incl. normalización), fiscal válido/inválido/transitorio, flujo duplicado/fiscal/AFIP caída/sin CAE/válido.  
- **Faltantes sugeridos:** `simular_posting_exitoso` + CAE + resolución `base_empresa`; FM; error “AFIP no configurado” → código esperado; concurrencia (opcional).  
- **Mocks:** `patch` sobre `self_checkout.fe_sync.consultar_cae_comprobante` alineado con el import usado en el servicio ✔.

### PASO 8 — Riesgos producción

- Dependencia de disponibilidad AFIP cuando hay CAE (modo estricto).  
- Falsos duplicados teóricos por normalización insuficiente.  
- Errores no “silenciosos”: se propagan como `TransicionEstadoInvalida` con mensaje/código (salvo mala clasificación §3.2).  
- Puntos críticos: resolución `base_empresa`, heurística transitoria, carrera duplicados, FM.

### PASO 9 — UI/UX

- **`revision_expediente.html`:** aprobación por `POST …/aprobar/`; errores vía `showErr(JSON.stringify(d))` — el usuario ve `detail` y puede ver `codigo` dentro del JSON; **no** hay mensajes dedicados ni panel “estado duplicado / fiscal” como en diseño PASO 5 UI.  
- **No** se rompe el flujo base: sigue PATCH → transiciones → aprobar.  
- Mejora futura: mostrar `d.codigo` y texto amigable para `duplicate_factura_synap` / fiscal (sin rediseño completo).

---

*Fin del informe de auditoría.*
