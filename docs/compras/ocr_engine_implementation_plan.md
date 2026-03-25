# Plan de implementación incremental — Motor de documentos (OCR/parsing)

**Estado:** planificación **posterior** a análisis y diseño (`ocr_engine_change_analysis.md`, `ocr_engine_change_design.md`) y plan de tests (`ocr_engine_test_plan.md`).

**Regla:** cada etapa es **reversible** por flag y no elimina el comportamiento anterior.

---

## Stage 0 — Preparación (sin cambio de comportamiento)

**Objetivo:** preparar extensiones sin activar motor nuevo.

| Acción | Detalle |
|--------|---------|
| Settings | Documentar variables futuras: `FACTURA_COMPRA_OCR_ENGINE_MODE` (default `legacy`) |
| `raw` | Documentar convención `raw.document_engine_v1` reservada |
| Dependencias | Evaluar `opencv-python-headless` en `requirements` (solo cuando Stage 1 arranque) |

**Tests:** ninguno obligatorio; solo regresión existente.

**Riesgo:** bajo.

**Rollback:** N/A.

---

## Stage 1 — Preprocesado de imagen + OCR estructurado (TSV)

**Objetivo:** primera entrega “segura”: mejorar entrada a Tesseract y guardar evidencia estructurada **sin** cambiar campos obligatorios del contrato.

### Cambios de código (propuesta)

- Nuevo módulo p. ej. `factura_compra_captura/ocr/preprocess/` o `ocr/image_preprocess.py` con funciones puras + fallback.
- Nuevo módulo `ocr/tesseract_structured.py`: `extraer_tsv` → parse a líneas/palabras con confianza.
- **`HeuristicOcrAdapter`** (o wrapper interno): si `ENGINE_MODE` ≥ `preprocess_only` o `structured_ocr`, aplicar preproceso en JPEG/PNG y/o llamar `image_to_data`; **rellenar** `raw.ocr_structured` (resumen) y **mantener** `texto_plano` desde TSV reconstruido o `image_to_string` como hoy si flag `legacy_fallback`.
- **No** cambiar `pipeline.py` salvo pasar settings adicionales al adapter si hiciera falta.

### Tests (TDD)

- PRE-04, OCR-01, OCR-02, BC-01.

### Riesgos

- OpenCV aumenta tamaño de imagen Docker y tiempo CPU.
- Preproceso agresivo puede empeorar algunas fotos → **fallback** obligatorio.

### Rollback

- `FACTURA_COMPRA_OCR_ENGINE_MODE=legacy` o no instalar OpenCV hasta estabilizar.

---

## Stage 2 — DocumentClassifier + HeaderParser con confianza por campo

**Objetivo:** clasificación explícita y desglose de confianza en cabecera; sigue alimentando `campos_cabecera` con compatibilidad.

### Cambios

- `DocumentClassifier` como función pura sobre métricas de archivo + snippet de texto.
- `HeaderParser` refactor **incremental** desde regex de `heuristic_pdf` (copiar/mover por partes, no big-bang).
- `campos_cabecera_confidence` opcional dentro de `raw` o subdict acordado.

### Tests

- CLF-01–03, PAR-H-01, BC-02.

### Riesgos

- Divergencia temporal entre parser nuevo y heurístico → feature flag por campo.

### Rollback

- Flag desactiva parser nuevo; solo heurístico.

---

## Stage 3 — LineItemParser con layout (tabla)

**Objetivo:** ítems desde agrupación TSV por columnas cuando sea posible; deduplicación multicopia reutilizable.

### Cambios

- `LineItemParser` usando coordenadas; mantener `_dedupe_lineas_misma_factura` como post-proceso común.
- Evidencias en `raw.lineas_evidencia` (opcional).

### Tests

- PAR-L-01, dedupe + fixtures multipágina.

### Riesgos

- Facturas con tablas no rectangulares → fallback a regex actual.

### Rollback

- Usar solo rama regex.

---

## Stage 4 — SemanticNormalizer + ValidationEngine + almacenamiento de evidencias

**Objetivo:** normalización central y validaciones cruzadas en `raw.validaciones`.

### Cambios

- Módulo `normalization.py` / `validation_engine.py` llamados desde adapter o pipeline **después** de parse.
- **No** modificar `LegacyPostingAdapter` ni posting; validaciones **no** bloquean borrador por defecto.

### Tests

- NORM-*, VAL-*, integración con dict sintético.

### Riesgos

- Falsos positivos de warning → afinar umbrales.

### Rollback

- Desactivar `ValidationEngine` por flag.

---

## Stage 5 — Rollout por feature flag y observabilidad

**Objetivo:** activar en entornos controlados; métricas y logs.

### Cambios

- Settings por entorno; logs estructurados (`logger.info` con `documento_id`, `engine_mode`, duración).
- Opcional: contador de correcciones analista (Stage siguiente o mismo).

### Tests

- BC-03; smoke test API.

### Riesgos

- Configuración errónea en producción → documentar valores default seguros.

### Rollback

- `ENGINE_MODE=legacy` global.

---

## Resumen de dependencias entre stages

```
Stage 1 (preprocess + TSV)
    → Stage 2 (classifier + header conf)
    → Stage 3 (line items layout)
    → Stage 4 (normalize + validate)
    → Stage 5 (rollout)
```

## Qué NO hace este plan

- No reemplaza `HeuristicOcrAdapter` de un golpe.
- No añade servicios cloud OCR.
- No altera migraciones de negocio críticas sin necesidad (JSON flexible preferido).
- No toca UI de revisión salvo mostrar `raw.validaciones` cuando exista (opcional en Stage 4+).

---

## Próximo paso operativo

Implementar **solo Stage 1** cuando el equipo apruebe, siguiendo `ocr_engine_test_plan.md` y manteniendo **fallback** al comportamiento actual al 100% con `ENGINE_MODE=legacy` (default hasta validación).
