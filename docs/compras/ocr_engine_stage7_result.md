# OCR factura compra — Stage 7 resultado

## Alcance completado

- **API `revision_engine_context`** (solo lectura) en `ExpedienteFacturaCompraSerializer`: deriva de `resultado_ocr.raw.document_engine_v1` del documento fuente más reciente y de `metadata.analyst_feedback` del expediente.
- **Servicio** `build_revision_engine_context_for_ui` en `revision_engine_context.py`: cabecera y líneas con evidencia resumida, métricas, plantilla, `workflow_facing_summary` / señales.
- **PATCH `analyst_feedback_append`**: lista de `{ campo, valor_anterior, valor_nuevo }` fusionada con `append_analyst_correction` en `ExpedienteService.actualizar` → persiste en `expediente.metadata.analyst_feedback`.
- **UI** (`revision_expediente.html`): panel aditivo “Motor de documento” (puntuación, validación, plantilla, detalles de evidencia), sin cambiar botones ni flujo; al guardar borrador se envían correcciones detectadas respecto al snapshot cargado.

## Archivos tocados

| Área | Archivo |
|------|---------|
| Contexto revisión | `factura_compra_captura/services/revision_engine_context.py` |
| Serializer | `factura_compra_captura/api/serializers.py` |
| Servicio expediente | `factura_compra_captura/services/expediente_service.py` |
| Plantilla revisión | `factura_compra_captura/templates/factura_compra_captura/revision_expediente.html` |
| Tests | `factura_compra_captura/tests/test_revision_engine_stage7.py` |
| Diseño / plan | `docs/compras/ocr_engine_stage7_design.md`, `ocr_engine_stage7_test_plan.md` |

## Invariantes

- Sin cambios en posting, aprobación, duplicados ni validación fiscal.
- Sin decisiones bloqueantes en UI; panel informativo.
- `OcrExtractResult` y pipeline OCR sin cambio de contrato.

## Comandos

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_revision_engine_stage7
docker exec Synap_app python manage.py test factura_compra_captura
```

## Nota de diseño

No se ejecutó `teach-impeccable` (no hay `.impeccable.md` en el repo); la UX sigue patrones existentes de la pantalla (`base_app.html`, Tailwind, textos en español).
