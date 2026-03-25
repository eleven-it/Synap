# Análisis — Evolución del motor OCR / parsing (factura_compra_captura)

**Modo:** evolución incremental sobre sistema **ya implementado** (no greenfield).  
**Metodología:** ANALYZE → DESIGN CHANGE → TDD → PATCH → HARDEN (compatible con *adminnet-module-migration*, modo evolución).

**Alcance:** pipeline captura → OCR → parsing; **sin** sustituir flujo de aprobación/posting ni integración legacy en esta fase documental.

---

## 1. Puntos de entrada del pipeline OCR

| Punto | Ubicación | Comportamiento |
|-------|-----------|----------------|
| Alta de documento | `factura_compra_captura/services/documento_fuente_service.py` | Tras persistir `DocumentoFuente`, llama `programar_ocr_documento(doc.pk)` |
| Orquestación sync/async | `factura_compra_captura/ocr/jobs.py` | `FACTURA_COMPRA_OCR_DEFER` / `FACTURA_COMPRA_OCR_SYNC` deciden hilo vs inline vs `on_commit` |
| Ejecución | `factura_compra_captura/ocr/pipeline.py` → `ejecutar_pipeline_ocr` | Resuelve ruta local del archivo, `get_ocr_adapter()`, `adapter.extract(ruta_archivo=..., mime_type=...)` |
| Selección de motor | `factura_compra_captura/ocr/factory.py` → `get_ocr_adapter()` | `FACTURA_COMPRA_OCR_ADAPTER`: `heuristic` (default) u `http` |

**APIs:** la subida de archivos pasa por el servicio de documentos; el contrato de salida hacia el modelo no cambia si se extiende el adapter o el resultado interno.

---

## 2. Estructura actual del adapter

- **Protocolo:** `factura_compra_captura/ocr/base.py` — `OcrAdapter` con `extract(...) -> OcrExtractResult`
- **`OcrExtractResult`:** `texto_plano`, `confianza_global` (float), `campos_cabecera` (dict), `lineas_sugeridas` (list), `raw` (dict)
- **Implementaciones:**
  - **`HeuristicOcrAdapter`** (`ocr/heuristic_adapter.py`): delega en `analizar_archivo_factura` (`heuristic_pdf.py`)
  - **`HttpOcrAdapter`** (`ocr/http_adapter.py`): motor externo HTTP (opcional; fuera del alcance de “solo in-house”)

**Implicación:** cualquier “motor interno” nuevo puede coexistir como **otro adapter** o como **envoltorio** dentro de un adapter único con feature flag, manteniendo el mismo `OcrExtractResult` o extendiendo `raw`/`campos_cabecera` sin romper contratos si se versiona.

---

## 3. Componentes del parser heurístico actual

**Archivo principal:** `factura_compra_captura/ocr/heuristic_pdf.py`

- **PDF:** `extraer_texto_pdf` (pypdf) — texto por página concatenado con `\n`
- **Imagen:** `extraer_texto_imagen_tesseract` — Pillow + pytesseract `image_to_string` (PSM `--psm 3`, OEM `--oem 1`)
- **Parsing:** `parsear_texto_factura` — regex sobre un único string de texto (cabecera: CUIT, nro, fechas, totales, razón social, tipo factura/COD, etc.; ítems por patrones de línea; deduplicación de líneas repetidas)
- **Análisis unificado:** `analizar_archivo_factura` — ramifica por `MIME_IMAGEN_OCR` vs `application/pdf`; devuelve dict con `texto_plano`, `confianza_global`, `campos_cabecera`, `lineas_sugeridas`, `raw` (motor, extracción, advertencias, métricas)

**No existe** hoy separación formal de “clasificador” ni “parser de layout” ni “normalizador semántico” independientes; todo está en funciones y regex en el mismo módulo.

---

## 4. Dónde se persiste la salida OCR

- **Modelo:** `factura_compra_captura/models/documento_fuente.py` — campo **`resultado_ocr`** (`JSONField`, default `{}`)
- **Escritura:** `ejecutar_pipeline_ocr` en `pipeline.py` asigna:
  - `texto_plano`, `confianza_global`, `campos_cabecera`, `lineas_sugeridas`, `raw`
- **Expediente:** `metadata` (p. ej. `ocr_confianza_global`, `ocr_ultimo_documento_id`, errores de OCR)

**Extensión segura:** ampliar el JSON de `resultado_ocr` (p. ej. `raw.engine_v2`, `evidencias`, `validaciones`) sin migración obligatoria si el campo es JSON flexible; documentar claves nuevas.

---

## 5. Dónde se normalizan campos extraídos

- **Dentro del heurístico:** `_monto_a_texto_plano`, fechas `dd/mm/yyyy`, deduplicación de líneas, normalización de CUIT en texto
- **Post-OCR en UI/API:** revisión de expediente (`revision_expediente.html`) combina `metadata.posting_v1`, `proveedor_synap` y `resultado_ocr.campos_cabecera`
- **Legacy / dominio:** `core.utils.administranet_types` y servicios de expediente/posting al **guardar** o **aprobar** — **no** en el pipeline OCR en sí

**Brecha:** la normalización fiscal/negocio (FA/FC, importes, CUIT) está repartida entre heurístico, formulario y reglas de negocio posteriores; no hay una capa única “SemanticNormalizer” trazable.

---

## 6. Dónde falta confianza o validación

| Aspecto | Estado actual |
|---------|----------------|
| Confianza global | Un float heurístico (`confianza_global`); sin desglose por campo |
| Confianza por campo | En general **ausente** (salvo lógica implícita en el score de `parsear_texto_factura`) |
| Validación cruzada ítems vs total | **No** en pipeline OCR; riesgo operativo mitigado en UI manualmente |
| Coherencia fiscal automática | `fiscal_invoice_validation.py` y duplicados (`duplicate_detection.py`) actúan en **aprobación** / posting, no sobre el OCR crudo |
| Calidad de imagen/PDF | Sin métricas previas (deskew, DPI, “¿texto escaneado?”) antes de Tesseract |
| Explainability | Parcial: `raw.advertencia`, `lineas_repetidas_omitidas` en cabecera; sin trazabilidad “campo X ← regex Y / bloque Z” |

---

## 7. Extensiones incrementales para un motor nuevo

1. **Factory:** `get_ocr_adapter()` — añadir `internal` / `document_engine_v1` o envolver `HeuristicOcrAdapter` tras pre/post procesamiento
2. **`OcrExtractResult.raw`:** almacenar salida estructurada (TSV/hOCR), clasificación, validaciones sin romper `campos_cabecera` existentes
3. **`pipeline.py`:** mismo punto de entrada; opcionalmente bifurcar internamente según `settings.FACTURA_COMPRA_OCR_ENGINE_MODE` (ej. `heuristic_only` | `hybrid` | `structured_v1`)
4. **Tests:** `tests/test_ocr_pipeline.py`, `test_heuristic_pdf.py` — patrón de mock del adapter; mantener compatibilidad
5. **Jobs:** sin cambio obligatorio si el adapter sigue siendo síncrono respecto a `extract`

---

## Clasificación MIME y ramificación

- **En `heuristic_pdf.analizar_archivo_factura`:**  
  - `image/jpeg`, `image/png` → Tesseract (si habilitado)  
  - `application/pdf` → pypdf  
  - Otro MIME → respuesta con advertencia de tipo no soportado (no OCR)
- **Lista permitida:** `FACTURA_COMPRA_DOCUMENTO_MIME_PERMITIDOS` en `settings.py`

**No hay** hoy distinción explícita “PDF nativo vs PDF escaneado” en código: todo PDF pasa por extracción de texto; si no hay capa de texto, el resultado puede quedar vacío o pobre.

---

## Tesseract: texto plano vs estructurado

- **Actual:** solo **texto plano** (`image_to_string`), configuración fija `--oem 1 --psm 3`
- **No se usa** TSV, hOCR, ALTO ni box-level confidence en el pipeline productivo

---

## Comprobaciones de calidad de documento existentes

- **Tesseract deshabilitado:** mensaje en `raw` / advertencia
- **Imagen no legible:** `OCR_IMAGEN_NO_VALIDA`
- **PDF ilegible:** error propagado como `ValueError` / `OcrAdapterError`
- **No** hay preprocesamiento OpenCV (deskew, binarización) ni estimación de DPI antes del OCR

---

## Conclusión para el diseño

El sistema es **adecuado para evolución por capas**: adapter estable, persistencia JSON flexible, punto único de ejecución (`ejecutar_pipeline_ocr`). Los huecos principales son **estructura** (layout), **confianza por campo**, **validación cruzada** temprana y **observabilidad** — sin obligar a reescribir el heurístico en el primer paso.
