# Análisis de cambio — duplicados y validación fiscal AFIP/ARCA (Compras)

**Alcance:** módulo factura de compra (`factura_compra_captura`, `factura_compra_posting`).  
**Paso:** solo análisis (PASO 1). Sin implementación.  
**Fecha de referencia:** estado del repositorio al momento del análisis.

---

## 1. Dónde ocurre la aprobación

| Punto | Archivo / símbolo | Comportamiento |
|-------|-------------------|----------------|
| Servicio único de negocio | `factura_compra_captura.services.expediente_service.ExpedienteService.aprobar_expediente_con_stub` | Única función que concentra la aprobación con posting (hoy stub/fake). Exige `estado == aprobacion_solicitada`. |
| API REST dedicada | `factura_compra_captura.api.views.ExpedienteAprobarAPIView.post` | `POST /api/compras/expedientes/<uuid>/aprobar/` → llama a `aprobar_expediente_con_stub`; errores → `400` con `codigo`. |
| API por transición | `ExpedienteService.aplicar_transicion` con `accion == "simular_posting_exitoso"` | Misma ruta de aprobación interna; luego registra evento `transicion_estado`. |
| URL | `factura_compra_captura.api.urls` | Rutas bajo prefijo `api/compras/` (montaje en `django_project/urls.py`). |

**Conclusión:** cualquier validación previa a “posting” debe insertarse **dentro o inmediatamente antes** de `aprobar_expediente_con_stub` (o en un único orquestador llamado desde ahí), para cubrir tanto `POST …/aprobar/` como la transición `simular_posting_exitoso`.

---

## 2. Dónde se ejecuta el posting

| Componente | Ubicación | Estado en código |
|------------|-----------|------------------|
| Selección de adapter | `factura_compra_posting.stub_adapter.get_posting_adapter` | `FACTURA_COMPRA_POSTING_BACKEND`: `fake` (default), `noop`, o `legacy` (hoy **lanza `RuntimeError`** — no hay adapter MySQL real cableado aquí). |
| Adapter activo por defecto | `FakeLegacyPostingAdapter` | `preflight` → siempre `PreflightResult(ok=True)`; `execute` → resultado fijo (`FAKE_CODMOV`, `FAKE_NRO`). |
| Adapter de prueba de orden SQL | `factura_compra_posting.recording_mysql_adapter` | Solo tests / simulación de fases P1–P9; **no** está en el flujo de aprobación productivo. |
| Contrato | `factura_compra_posting.contracts` | `LegacyPostingAdapter` (Protocol), `LegacyPostingResult`, `PreflightResult`. |

**Conclusión:** en el árbol analizado, el “posting” que corre en aprobación es el **stub**. No se observa `LegacyPostingAdapter` real ejecutando SQL legacy desde Compras. Si en otro entorno/rama existe un adapter legacy, el **punto de enganche sigue siendo** `get_posting_adapter()` + `aprobar_expediente_con_stub`, sin tocar el SQL del adapter si la política es solo interceptar antes.

---

## 3. Validaciones actuales (antes y durante aprobación)

### 3.1 Por transición de workflow

**Archivo:** `factura_compra_captura.services.transiciones_estado`

- `validar_precondiciones`:
  - `enviar_revision`: `codigo_proveedor_legacy`, al menos una línea, cada línea con `id_art_legacy` y `cantidad > 0`.
  - `rechazar`: `motivo` no vacío.
- No hay ramas para `simular_posting_exitoso` ni validación de duplicados ni fiscal.

### 3.2 Al aprobar (servicio)

**Archivo:** `ExpedienteService.aprobar_expediente_con_stub`

Orden actual:

1. Estado debe ser `aprobacion_solicitada`.
2. Backend distinto de `noop`.
3. `map_expediente_to_command_v1(expediente, idempotency_key=…)` → `LegacyPostingCommandV1`.
4. `validate_posting_command(cmd)` (`factura_compra_posting.legacy_posting_command_v1`) → reglas V-* (líneas, importe, origen REMITO/OC/VALE, lote, cabecera, etc.).
5. `adapter.preflight(cmd)` → hoy **no-op útil** con fake (siempre OK).
6. `adapter.execute(cmd)` → resultado stub.
7. Persistencia expediente (`estado`, `legacy_*`, `posting_status`, `posting_attempt`, evento + log estructurado).

### 3.3 Captura / OCR / documentos

- `factura_compra_captura.services.documento_fuente_service`: MIME, tamaño, estados OCR; **no** duplicados de factura ni AFIP.

### 3.4 Preflight “de diseño” no integrado

- `factura_compra_posting.preflight_legacy.PreflightLegacyPostingService`: modelo mental de período fiscal + conteo duplicado vía callables; **cubierto por tests** (`test_ut_pre.py`) pero **no invocado** desde `aprobar_expediente_con_stub` ni desde el adapter fake.

---

## 4. Mecanismo de duplicados hoy

- **En `factura_compra_captura`:** no hay referencias a duplicados (búsqueda en el paquete sin coincidencias).
- **En aprobación:** no se compara contra otros expedientes ni contra tablas legacy para “misma factura”.
- **En posting stub:** no aplica.
- **Documentación normativa:** duplicados y política FM están descritos en `docs/compras/posting_tests.md` / ADR-0004; la clase `PreflightLegacyPostingService` es un **esqueleto** alineado a UT-PRE, pendiente de cablear a datos reales.

---

## 5. Integración PyAfipWs en el módulo Compras

- **No hay** imports de `pyafipws` en `factura_compra_captura` ni en `factura_compra_posting`.
- **Sí hay** uso consolidado en otros módulos del monorepo, reutilizable como referencia o capa compartida:
  - `self_checkout/fe_sync.py`: `get_ultimo_autorizado_afip`, `consultar_cae_comprobante` (WSAA + WSFEv1, `CompConsultar` / `ConsultarComprobante`).
  - `self_checkout/fe_config.py` + `get_fe_config` / `is_fe_configured`: configuración por `base_empresa` (string), certificados, URLs homo/prod.
  - `self_checkout.services.invoice_service`: emisión CAE/CAEA (`CrearFactura`, `CAESolicitar`, etc.) — flujo **venta** self-checkout, no compra.
  - `self_checkout/views.py`: generación de datos/URL de **QR** verificación (RG 4291) para comprobantes emitidos — orientado a ticket emitido, no a parseo de QR de factura de proveedor escaneada.
  - `fe_afip`: modelos y servicios CAEA/config.

**Implicancia:** la validación fiscal para **factura de compra** deberá **delegar** en funciones ya existentes (p. ej. `consultar_cae_comprobante` + mapping PV/tipo/número desde `posting_v1` / metadata) o en un adapter fino que las llame, evitando duplicar conexión WSAA/WSFE.

**Gap explícito:** Compras usa `ExpedienteFacturaCompra.empresa` (FK Synap). `fe_sync` espera `base_empresa` (nombre de base AdministraNET). Hace falta **mapeo documentado** (settings, campo en Empresa, o convención ya existente en el proyecto) para PASO 2.

---

## 6. Flujo real de ejecución (endpoint → servicio → adapter)

```text
POST /api/compras/expedientes/<uuid>/aprobar/
  → ExpedienteAprobarAPIView.post
  → ExpedienteService.aprobar_expediente_con_stub(expediente, actor)
       → map_expediente_to_command_v1
       → validate_posting_command
       → adapter = get_posting_adapter()
       → adapter.preflight(cmd)
       → adapter.execute(cmd)
       → guardar expediente + EventoAuditoriaInterno + log_factura_compra_event

POST /api/compras/expedientes/<uuid>/transiciones/  { "accion": "simular_posting_exitoso" }
  → ExpedienteTransicionAPIView → TransicionSerializer.save
  → ExpedienteService.aplicar_transicion
       → validar_precondiciones (no añade checks para esta acción)
       → aprobar_expediente_con_stub (mismo núcleo que arriba)
       → evento transicion_estado
```

**UI:** `compras/revision/<uuid>/` (TemplateView + JS que pega a la misma API).

---

## 7. Puntos de extensión recomendados (sin implementar)

1. **`aprobar_expediente_con_stub`**  
   - Tras `validate_posting_command` y **antes** de `adapter.preflight` / `execute`, o antes de `preflight` si se quiere fallar antes de cualquier llamada al adapter:  
     - servicio de duplicados (Synap + opcional lectura legacy read-only si se acuerda);  
     - servicio fiscal (wrapper sobre `fe_sync` / pyafipws).  
   - Ventaja: un solo lugar para ambos entrypoints API.

2. **`PreflightLegacyPostingService`**  
   - Podría alimentarse con implementaciones reales de `query_duplicate_count` / `query_period_open` y llamarse desde el punto anterior, **sin** cambiar el Protocol `LegacyPostingAdapter` si no se desea.

3. **`FakeLegacyPostingAdapter.preflight`**  
   - Opción alternativa: enriquecer preflight del stub cuando backend es fake (menos deseable si luego el adapter real no replica la misma semántica).

4. **Modelo `metadata` JSON**  
   - Ya existe `metadata` y `posting_v1.header` / `context`; permite guardar resultado de validación fiscal/duplicado **sin migración**, hasta decidir campos dedicados en PASO 2.

5. **Serializers / API**  
   - Exponer estados de validación en `ExpedienteFacturaCompraSerializer` cuando existan campos o claves en `metadata`.

6. **UI revisión**  
   - `templates/factura_compra_captura/revision_expediente.html`: ampliar panel de estado leyendo nuevos campos o `metadata.validacion_*`.

---

## 8. Riesgos y supuestos detectados

| Riesgo | Detalle |
|--------|---------|
| Adapter `legacy` no presente en este snapshot | Si el producto asume posting MySQL ya desplegado, puede vivir en otra rama; el análisis refleja el código actual del repo. |
| Doble fuente de verdad duplicados | Synap (expedientes) vs MySQL legacy: la regla de negocio debe definir si “duplicado” es solo interno o coincide con `Validacion_Comp` VB6. |
| Fiscal compra vs fiscal venta | `invoice_service` y `fe_sync` están orientados a emisión/consulta de comprobantes de **venta**; compras puede requerir solo **consulta** CAE / consistencia con datos de cabecera, o flujos distintos (importador, crédito fiscal). |
| QR de proveedor | No hay en Compras parser de QR AFIP; si el requisito es “QR escaneado”, habrá que ubicar librería/flujo o reutilizar lógica si existe en otro módulo (fuera del grep rápido actual). |

---

## 9. Entregable PASO 1

Este documento cumple el PASO 1: mapa de aprobación, posting, validaciones, ausencia de duplicados integrados, preflight stub vs `PreflightLegacyPostingService` desconectado, ausencia de PyAfipWs en Compras con referencias a reutilización en `self_checkout`/`fe_afip`, y puntos de extensión candidatos.

**Siguiente paso (PASO 2):** diseño en `docs/compras/change_design.md` — no implementar hasta entonces.
