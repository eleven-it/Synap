# OCR Stage 1.5 — Auditoría de código (Stage 1)

## Alcance

Archivos principales: `factura_compra_captura/ocr/image_preprocess.py`, `tesseract_structured.py`, `heuristic_pdf.py` (`_procesar_imagen_ocr_por_modo`, `analizar_archivo_factura`), `heuristic_adapter.py`; contrato `OcrExtractResult` en `ocr/base.py`.

## 1. Placeholders ocultos

No se encontraron cadenas tipo `TODO` / `FIXME` / valores mágicos sin documentar en los módulos Stage 1 revisados.

## 2. Imports frágiles si falta OpenCV

- `image_preprocess.py` importa `cv2` y `numpy` **dentro** de un `try`; ante `ImportError` devuelve la imagen original y metadata con `motivo` y `fallback=True`.
- No se asume `cv2` a nivel de import del módulo.

## 3. Fallback explícito y seguro

- Preprocesado: cualquier excepción en el pipeline OpenCV devuelve PIL original + `fallback=True` y `motivo`.
- OCR estructurado: excepciones en `construir_ocr_structured_desde_imagen` se capturan; el resultado incluye `error` acotado y **no** impide devolver el texto plano ya obtenido con `image_to_string`.

## 4. Feature flag determinista

- `engine_mode` se normaliza con `.strip().lower()`.
- Valores fuera de `legacy` | `preprocess_only` | `structured_ocr` se tratan como **`legacy`** (sin `document_engine_v1`).
- Comportamiento cubierto por test `test_engine_mode_desconocido_equivale_legacy_sin_document_engine_v1`.

## 5. Contrato `OcrExtractResult`

- `OcrExtractResult` permanece como dataclass con los mismos campos; el enriquecimiento es solo vía `raw` (dict), compatible con el pipeline que copia `resultado.raw` a `resultado_ocr`.
- No hay cambios de tipo ni campos nuevos en el dataclass.

## 6. Fallos silenciosos

- Antes de esta pasada, el fallo del TSV estructurado solo quedaba en `ocr_structured.error`.
- **Ajuste aplicado (bajo riesgo):** `logger.warning` al capturar la excepción en `structured_ocr`, con mensaje acotado, para observabilidad en logs sin cambiar el contrato de salida.

## 7. Cobertura de tests (Stage 1.5)

Archivo `factura_compra_captura/tests/test_ocr_stage1.py`:

| Área | Cobertura |
|------|-----------|
| Fallback OpenCV | `test_preprocesar_factura_usa_original_si_opencv_falla` (requiere `cv2` en imagen) |
| TSV sintético | `test_construir_resumen_desde_dict_tsv_agrupa_lineas` |
| `legacy` sin `document_engine_v1` | `test_legacy_sin_document_engine_v1_en_raw` |
| `preprocess_only` | `test_preprocess_only_incluye_preprocess_sin_ocr_structured` |
| `structured_ocr` + `ocr_structured` | `test_structured_ocr_incluye_ocr_structured_en_raw` (mocks) |
| Modo desconocido → legacy | `test_engine_mode_desconocido_equivale_legacy_sin_document_engine_v1` |

Brechas aceptables para Stage 2 (no bloqueantes): prueba **end-to-end** con Tesseract real opcional en CI; tamaño máximo de JSON no automatizado (revisión manual/perf).

## Resumen

El diseño Stage 1 es **defensivo** ante ausencia de OpenCV y fallos de TSV estructurado. La bandera de motor es **predecible**. El único endurecimiento de código realizado en esta auditoría es el **log de warning** en el `except` del OCR estructurado.
