# OCR motor factura compra — Stage 2 (resultado)

## Objetivo

Añadir **comprensión de documento** (clasificación + cabecera con confianza y evidencia) de forma **aditiva**, sin alterar el contrato `OcrExtractResult`, ni el parser heurístico principal, ni el flujo de posting/validación.

## Componentes nuevos

| Módulo | Rol |
|--------|-----|
| `factura_compra_captura/services/document_classifier.py` | Clasifica `invoice_probable` vs `unknown` con heurísticas de palabras clave (factura, CAE, CUIT, total, AFIP, etc.), densidad de texto y, si existe, texto extraído del OCR estructurado. |
| `factura_compra_captura/services/header_parser.py` | Extrae cabecera con seis campos: `proveedor`, `tipo_factura`, `punto_venta`, `numero`, `fecha`, `total`. Prioriza coincidencias en **líneas del OCR estructurado**, luego **campos del parser heurístico** (`parsear_texto_factura`), luego **regex sobre texto plano**. |

## Integración en `raw`

Tras el análisis (PDF o imagen con OCR habilitado), `raw["document_engine_v1"]` incluye:

- `version`: al menos **2** cuando hay datos Stage 2.
- `engine_mode`: solo en **imágenes** (valores `legacy` | `preprocess_only` | `structured_ocr` según Stage 1).
- `preprocess` / `ocr_structured`: sin cambios respecto a Stage 1 cuando aplican.
- **`classification`**: `tipo_documento`, `confidence`, `detalle` (scores auxiliares).
- **`parsed.header`**: objeto con los seis campos; cada uno con:
  - `valor`
  - `confidence` (0..1, heurística)
  - `source`: `structured` | `heuristic` | `raw`
  - `evidencia`: `page`, `bbox` (dict o `null`), `raw_text` (fragmento)

Los campos **`campos_cabecera`** y **`lineas_sugeridas`** del resultado principal siguen igual que antes (solo salida de `parsear_texto_factura`).

## Cómo se calcula la confianza

Reglas **heurísticas** (no ML):

- Coincidencia en **línea OCR estructurada** con patrón claro → confianza **alta** (~0,78–0,85 según campo).
- Valor tomado del **diccionario heurístico** (`parsear_texto_factura`) → **media** (~0,58–0,62).
- Solo **regex sobre texto plano** → **media-baja** (~0,55–0,72).
- **Varias coincidencias** en clasificador: ligera penalización al score de keywords (`detalle.keyword_hits` alto).
- Texto plano muy corto pero **OCR estructurado** con keywords: el clasificador usa también caracteres del bloque estructurado para no clasificar como “vacío”.

## Cambio menor en Stage 1 (TSV)

En `palabras_muestra` de `tesseract_structured.py` se añade el campo **`page`** por palabra para poder rellenar `evidencia.page` en cabecera.

## Limitaciones

- No hay modelo de ML; la clase `unknown` puede aparecer en facturas atípicas o muy ruidosas.
- Regex de cabecera están alineadas al layout AR típico; formatos muy distintos pueden dar `source: raw` y confianza baja.
- **Ítems de línea**, motor de validación y UI **no** forman parte de este stage.
- El **doble paso** Tesseract en `structured_ocr` (Stage 1) sigue aplicando; Stage 2 solo consume el resumen ya calculado.

## Pruebas

- `factura_compra_captura/tests/test_ocr_stage2.py`: clasificador, cabecera con/sin OCR estructurado, integración PDF en `document_engine_v1`.
- Tests Stage 1 actualizados para exigir `classification` y `parsed` donde corresponde.
- Suite completa del módulo: `docker exec Synap_app python manage.py test factura_compra_captura`.
