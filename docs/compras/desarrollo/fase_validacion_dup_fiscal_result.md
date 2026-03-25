# Resultado — validación duplicados y fiscal (PASO 4)

**Referencia:** [change_design.md](../change_design.md), tests `tests/compras/test_validation_phase3_5.py`.

## Implementado

1. **`DuplicateDetectionService`** (`factura_compra_captura/services/duplicate_detection.py`): clave empresa + `codigo_proveedor_legacy` + `tipo_factura` + `nro_comprobante_formateado` normalizado (trim, mayúsculas, espacios colapsados). Colisión con otro expediente en estado `aprobado` o `aprobacion_solicitada`, excluyendo el propio PK. `reason_codes` incluye `duplicate_factura_synap` si bloquea.

2. **`FiscalInvoiceValidationService`** (`factura_compra_captura/services/fiscal_invoice_validation.py`): sin CAE en `posting_v1.header` → `SKIPPED_NO_CAE`, no bloquea. Con CAE y tipo **FM** → `SKIPPED_NON_AR` / `fiscal_skip_tipo_fm`, no consulta WSFE (evita mapear FM a FB). Con CAE FA/FB/FC → `consultar_cae_comprobante` (`self_checkout.fe_sync`). Mensajes que indican entorno sin AFIP (`"AFIP no configurado"`, `"pyafipws no instalado"`) → `fiscal_afip_not_configured`. Errores transitorios (timeout, conexión, WSAA/WSFE en mensaje) → `fiscal_afip_unavailable`; resto de errores AFIP → `fiscal_afip_invalid`; sin `base_empresa` o sin pto/nro → `fiscal_afip_not_configured`. CAE devuelto distinto al declarado → `fiscal_cae_mismatch`.

3. **`resolve_base_empresa_for_compras`:** `metadata["compras"]["base_empresa"]`, `settings.FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID`, sesión `user.base_empresa`.

4. **`ExpedienteService.aprobar_expediente_con_stub`:** tras `validate_posting_command`, antes de `adapter.preflight`: bloqueo pesimista de **la fila del expediente que se aprueba** (`select_for_update` + revalidación de estado; mitiga doble envío sobre el mismo PK), duplicados → fiscal. Dos expedientes distintos con la misma clave lógica en alta concurrencia siguen siendo un tema de negocio / índice único si se exige garantía absoluta. Parámetros opcionales `base_empresa`, `request` para resolver base en tests y API.

5. **API de aprobación:** **`POST …/expedientes/<pk>/aprobar/`** es el endpoint explícito recomendado para UI. `ExpedienteAprobarAPIView` pasa `request` para resolver `base_empresa` desde sesión. La transición `simular_posting_exitoso` (`POST …/transiciones/`) usa la misma ruta interna y recibe `request` desde `TransicionSerializer.save` / `ExpedienteTransicionAPIView`, alineando resolución de base con `/aprobar/`.

6. **`settings.FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID`:** dict vacío por defecto; mapeo opcional por `empresa_id` Synap.

7. **`approval_validation.py`:** solo nota de diseño; la orquestación vive en `ExpedienteService` (sin `NotImplementedError`).

## No incluido en esta fase

- Persistencia de `metadata["compras_validacion"]` en bloqueo (§6.1 del diseño): los tests no la exigen; se puede añadir con transacción independiente en iteración posterior.

## Corrección de tests

- `test_api_expediente.py`: import faltante de `ExpedienteFacturaCompra`.
