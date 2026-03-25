# Plan bootstrap — Fase 1 (primer sprint técnico ejecutable)

**Objetivo:** primer incremento **mergeable** con valor: dominio expediente + API + tests, **sin** OCR productivo y **sin** MySQL legacy.  
**DoD:** [definition_of_done_by_phase.md](definition_of_done_by_phase.md) §Fase 1.  
**Contrato futuro:** alinear modelos con [posting_contract.md](posting_contract.md) (mapper en Fase 3 formalizado; en Fase 1 solo campos compatibles).

**No incluye:** SQL real de posting ([posting_sql_spec.md](posting_sql_spec.md)).

---

## 1. Estructura de apps Django (propuesta)

Ubicación bajo paquete del proyecto Synap existente (ajustar nombres si el repo ya tiene `apps/`).

```text
factura_compra_captura/          # workflow + expediente + API
  __init__.py
  apps.py
  models/
    expediente.py
    linea.py
    documento_fuente.py
    evento_auditoria.py
  services/
    expediente_service.py
    transiciones_estado.py
  api/
    serializers.py
    views.py
    urls.py
  tests/
    test_models.py
    test_transiciones.py
    test_api_expediente.py

factura_compra_posting/          # boundary legacy — solo contrato + stub Fase 1
  __init__.py
  apps.py
  contracts.py                   # re-export o mirror de dataclasses / pydantic desde spec
  stub_adapter.py                # NoOp o FakeLegacyPostingAdapter
  tests/
    test_stub_adapter.py
    test_validate_command.py     # si validate_posting_command vive aquí o en captura
```

*Decisión nueva de arquitectura:* coincide con [architecture.md](architecture.md) y ADR-0005; nombres exactos pueden ser `compras_captura` / `compras_posting` si convención del repo lo exige.

**Settings:** registrar ambas apps en `INSTALLED_APPS`.

---

## 2. Modelos mínimos (campos conceptuales)

### `ExpedienteFacturaCompra`

- `id` (UUID PK recomendado)
- `empresa` / `sucursal` (FK a modelos Synap existentes si hay)
- `estado` (CharField con choices alineados a PRD: `borrador`, `ocr_completado`, `en_revision`, …)
- `origen_datos` (enum Manual/REMITO/OC/VALE — alineado [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md))
- `codigo_proveedor_legacy` (IntegerField nullable hasta completar revisión)
- `metadata` JSON opcional (flags contexto posting futuro)
- `posting_status` (`not_attempted` | `in_progress` | `posted` | `failed`) para idempotencia futura
- `posting_attempt`, `idempotency_key_last`, `legacy_codigo_movimiento` (nullable)
- `creado_por`, timestamps

### `LineaExpedienteCompra`

- FK expediente
- `orden`, cantidades, precios, `id_art_legacy`, referencias OC/remito opcionales (nullable ints)
- JSON o campos planos según complejidad; debe poder mapearse a `StockLineCommand`

### `DocumentoFuente` (opcional en sprint 1)

- FK expediente, `archivo` FileField o path storage, `mime`, `hash`, `estado_procesamiento`

### `EventoAuditoriaInterno`

- FK expediente, actor, tipo evento, payload JSON, timestamp

*Confirmado por auditoría:* no hay tabla Synap en VB6; es *decisión nueva*.

---

## 3. Migraciones

- Migración inicial por app con índices `(estado, empresa)`, `(expediente_id, orden)` en líneas.
- **Sin** migraciones en MySQL legacy.

---

## 4. Tests iniciales (orden TDD sugerido)

1. `test_transicion_borrador_a_en_revision_requiere_datos_minimos`
2. `test_transicion_invalida_lanza_error`
3. `test_api_crear_expediente_201`
4. `test_api_listar_filtrado_por_estado`
5. `test_stub_posting_no_llama_mysql` (mock connection)

Referencias casos: [posting_tests.md](posting_tests.md) UT-CMD solo si `validate_posting_command` se implementa ya; si no, posponer a Fase 3.

---

## 5. Primeros endpoints (REST)

| Método | Ruta | Uso |
|--------|------|-----|
| POST | `/api/compras/expedientes/` | Crear borrador |
| GET | `/api/compras/expedientes/` | Lista + filtros |
| GET | `/api/compras/expedientes/{id}/` | Detalle |
| PATCH | `/api/compras/expedientes/{id}/` | Actualizar datos editables |
| POST | `/api/compras/expedientes/{id}/transiciones/` | Body: `{ "accion": "enviar_revision" }` etc. |

Autenticación: misma que resto Synap (*inferencia* estándar proyecto).

---

## 6. Primeros servicios

- `ExpedienteService.crear()`, `actualizar()`, `aplicar_transicion(expediente, accion, actor)`.
- `TransicionesEstado` tabla explícita (dict) documentada en código; tests de matriz.

**No implementar:** `LegacyPostingAdapter.execute` real.

---

## 7. Stub posting (Fase 1)

- Clase `FakeLegacyPostingAdapter` que implementa interfaz del [posting_contract.md](posting_contract.md) (`execute` → resultado fake o `NotImplementedError` si endpoint aprobar aún no existe).
- Si existe botón aprobar en API de Fase 1 (opcional): debe **no** abrir conexión MySQL.

---

## 8. Primer incremento usable sin MySQL legacy

**Demo:** crear expediente desde API o admin Django → agregar líneas vía API → pasar a `en_revision` → `rechazado` con motivo.

**Criterio:** analista técnico valida en Postman o UI mínima Django admin (temporal).

---

## 9. Registro en `settings` / feature flags (sugerido)

```python
FACTURA_COMPRA_POSTING_BACKEND = "noop"  # noop | fake | legacy
```

---

## 10. Documentación a tocar en el mismo PR

- Actualizar [README.md](README.md) con enlace a «implementación Fase 1 en curso» o changelog corto en `docs/compras/CHANGELOG_CAPTURA.md` (*opcional*, solo si el equipo lo usa).

---

## 11. Siguiente sprint (puente a Fase 2)

- Añadir `DocumentoFuente` + upload + cola vacía que marca `ocr_pendiente`.

---

## Referencias

- [master_execution_plan.md](master_execution_plan.md)
- [implementation_plan.md](implementation_plan.md)
- [domain_model.md](domain_model.md)
