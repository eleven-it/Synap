# OCR Stage 1.5 — Validación en runtime

## Comandos de rebuild y prueba (referencia)

Desde la raíz del repo (con Docker disponible):

```bash
# Reconstruir imagen de la app (recomendable tras cambios en requirements.txt o Dockerfile)
docker compose build app

# Rebuild estrictamente limpio (más lento; valida que no quede caché oculta)
docker compose build --no-cache app

docker compose up -d app

# Comprobar import de OpenCV y presencia de Tesseract en el contenedor
docker exec Synap_app python -c "import cv2; print('cv2', cv2.__version__)"
docker exec Synap_app tesseract --version
docker exec Synap_app python -c "import pytesseract; print('pytesseract ok')"

# Suite OCR / factura compra captura
docker exec Synap_app python manage.py test factura_compra_captura
```

Variables relevantes en `.env` (ver `.env.example`):

- `FACTURA_COMPRA_OCR_ENGINE_MODE` — `legacy` | `preprocess_only` | `structured_ocr`
- `FACTURA_COMPRA_OCR_TESSERACT_ENABLED` — debe ser `true` para OCR real en imágenes
- `FACTURA_COMPRA_OCR_TESSERACT_LANG` — por defecto `spa+eng` (coherente con paquetes apt `tesseract-ocr-spa` y `tesseract-ocr-eng`)

## Comportamiento por modo (confirmación)

### `ENGINE_MODE=legacy` (default)

- **Imágenes:** mismo flujo histórico: carga PIL, escala, `pytesseract.image_to_string` sin bloque `document_engine_v1`.
- **Tests:** `test_legacy_sin_document_engine_v1_en_raw`, `test_engine_mode_desconocido_equivale_legacy_sin_document_engine_v1` (modo desconocido se normaliza a legacy).

### `ENGINE_MODE=preprocess_only`

- **Imágenes:** preprocesado OpenCV (o fallback a original) y luego el mismo string OCR que antes; en `raw` aparece `document_engine_v1` con `preprocess` y `ocr_structured: null`.
- **Tests:** `test_preprocess_only_incluye_preprocess_sin_ocr_structured`.

### `ENGINE_MODE=structured_ocr`

- **Imágenes:** igual que preprocess + ejecución de `image_to_data` (TSV vía DICT) y resumen en `raw.document_engine_v1.ocr_structured` (nombre JSON: clave `ocr_structured` dentro de `document_engine_v1`).
- Si el TSV falla, el error queda en `ocr_structured` como dict con `error` y `fuente`, y se registra un **warning** en logs (no se interrumpe el flujo).
- **Tests:** `test_structured_ocr_incluye_ocr_structured_en_raw` (con mocks para no depender del binario en todos los entornos).

### PDF

- Sin cambios de motor Stage 1: solo capa pypdf + heurísticas; `FACTURA_COMPRA_OCR_ENGINE_MODE` no aplica a PDF en la implementación actual.

## Validación manual opcional (imagen real + Tesseract)

Con `FACTURA_COMPRA_OCR_TESSERACT_ENABLED=true` y un JPEG de factura:

1. `legacy`: comprobar que el resultado es equivalente al esperado antes del Stage 1 (campos/heurística).
2. `structured_ocr`: inspeccionar en BD o API el JSON `resultado_ocr.raw.document_engine_v1.ocr_structured` (tras pipeline que persiste el documento).

Los tests automatizados cubren contrato y ramas; la validación visual/calidad OCR sigue siendo responsabilidad de negocio.
