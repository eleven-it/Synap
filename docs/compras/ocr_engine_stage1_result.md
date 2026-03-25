# OCR motor factura compra — Stage 1 (resultado)

## Alcance entregado

- **Preprocesado de imagen (OpenCV):** `preprocesar_imagen_factura` en `factura_compra_captura/ocr/image_preprocess.py` (CLAHE + `fastNlMeansDenoising`). Solo aplica a **JPEG/PNG** antes de Tesseract cuando el modo no es `legacy`. Si OpenCV falla o no está instalado, se usa la **imagen original** y `preprocess.fallback=True`.
- **OCR estructurado (Tesseract TSV):** `construir_ocr_structured_desde_imagen` y `construir_resumen_desde_dict_tsv` en `factura_compra_captura/ocr/tesseract_structured.py` (`image_to_data` con salida DICT, resumen JSON con palabras muestra acotadas).
- **Integración:** `_procesar_imagen_ocr_por_modo` en `heuristic_pdf.py` según `FACTURA_COMPRA_OCR_ENGINE_MODE` (`legacy` | `preprocess_only` | `structured_ocr`). Los datos extra van en `raw["document_engine_v1"]` con `version`, `engine_mode`, `preprocess` y, si aplica, `ocr_structured`.
- **Contrato:** `OcrExtractResult` y `parsear_texto_factura` **sin cambios** de comportamiento; el parser sigue operando solo sobre el texto plano extraído.

## Configuración

| Variable | Valores | Default |
|----------|---------|---------|
| `FACTURA_COMPRA_OCR_ENGINE_MODE` | `legacy`, `preprocess_only`, `structured_ocr` | `legacy` |

Documentado en `.env.example` y `django_project/settings.py`.

## Dependencias

- `opencv-python-headless>=4.8,<5` en `requirements.txt` (imagen Docker: ejecutar `pip install -r requirements.txt` o reconstruir la imagen para incluir OpenCV).

## Pruebas

- Suite `factura_compra_captura`: **48 tests OK** (`docker exec Synap_app python manage.py test factura_compra_captura`).
- Nuevos tests en `factura_compra_captura/tests/test_ocr_stage1.py`:
  - fallback de preprocesado (mock de fallo en OpenCV),
  - resumen desde dict TSV sintético,
  - presencia de `document_engine_v1.ocr_structured` en modo `structured_ocr` (mocks de Tesseract string y OCR estructurado para no depender del binario `tesseract` en CI).

## No incluido (por diseño de Stage 1)

- Refactor de parsers, motor de normalización, motor de validación, cambios de UI.

## Notas de despliegue

- En entornos donde aún no se haya instalado OpenCV tras actualizar `requirements.txt`, el preprocesado hará **fallback** a la imagen original (comportamiento seguro).
- El binario **Tesseract** sigue siendo necesario para OCR real en servidor; los tests de integración del Stage 1 no lo exigen gracias a mocks puntuales.
