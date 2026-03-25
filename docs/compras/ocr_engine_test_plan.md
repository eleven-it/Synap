# Plan de pruebas (TDD) — Motor de documentos / OCR incremental

**Propósito:** definir tests **antes** de implementar cada etapa, asegurando compatibilidad con el flujo heurístico actual.

**Herramientas:** `SimpleTestCase` / `TestCase` según DB; tests sin red; mocks de adapter donde ya existe patrón en `test_ocr_pipeline.py`.

---

## 1. Clasificación

| ID | Caso | Entrada | Esperado |
|----|------|---------|----------|
| CLF-01 | PDF con texto embebido | PDF generado con reportlab/texto | `tipo_archivo` indica texto nativo o métrica de chars/página > umbral |
| CLF-02 | PDF sin texto (simulado) | Mock pypdf devuelve vacío o fixture mínimo | `pdf_probable_escaneo` o equivalente; no lanzar excepción |
| CLF-03 | Imagen JPEG/PNG | Fixture existente `_mini_jpeg_bytes` o similar | Clasificación `imagen_*` |
| CLF-04 | Documento no factura | Texto sin patrones AFIP | `probable_factura=False` o baja confianza; pipeline no rompe |

---

## 2. Preprocesado de imagen

| ID | Caso | Esperado |
|----|------|----------|
| PRE-01 | Imagen rotada 90° | Tras deskew/orientación, Tesseract mejora o se registra transformación en `raw` |
| PRE-02 | Imagen con skew leve | Ángulo corregido dentro de tolerancia o fallback sin crash |
| PRE-03 | Bajo contraste | Binarización adaptativa mejora longitud de texto reconocido vs baseline (métrica opcional) |
| PRE-04 | Fallo OpenCV | Fallback a imagen original; mismo contrato que hoy (`OcrExtractResult`) |

---

## 3. OCR estructurado (TSV)

| ID | Caso | Esperado |
|----|------|----------|
| OCR-01 | `image_to_data` / TSV | Presencia de `conf` por palabra; bbox parseable |
| OCR-02 | Reconstrucción de líneas | Agrupación Y → líneas coherentes con el texto plano |
| OCR-03 | Confianza media por línea | Valor 0–100 o 0–1 documentado; almacenado en `raw` |
| OCR-04 | Límite de tamaño | PDF/imagen grande no explota memoria (truncar o muestrear páginas en tests de estrés) |

---

## 4. Parsers estructurales

| ID | Caso | Esperado |
|----|------|----------|
| PAR-H-01 | HeaderParser con texto AFIP sintético | Mismos campos que `parsear_texto_factura` para fixture canónico |
| PAR-L-01 | LineItemParser | `lineas_sugeridas` equivalentes al heurístico para una tabla simple |
| PAR-F-01 | FiscalFieldParser | COD 011 → FC; duplicado de lógica cubierto por tests compartidos con `test_heuristic_pdf` |

---

## 5. Normalización semántica

| ID | Caso | Esperado |
|----|------|----------|
| NORM-01 | Fecha DD/MM/YYYY | ISO y validación de día/mes |
| NORM-02 | Montos AR | Punto decimal interno coherente con `administranet_types` |
| NORM-03 | CUIT con/sin guiones | 11 dígitos normalizados |
| NORM-04 | Nro comprobante | Formato PV-######## |

---

## 6. Validación

| ID | Caso | Esperado |
|----|------|----------|
| VAL-01 | Suma líneas = total | `validaciones` vacío o severidad info |
| VAL-02 | Suma líneas ≠ total | warning con delta |
| VAL-03 | Faltan campos críticos | warning listando campos (no bloquear OCR) |
| VAL-04 | Estructura inválida (0 líneas y total > 0) | warning documentado |

---

## 7. Compatibilidad hacia atrás

| ID | Caso | Esperado |
|----|------|----------|
| BC-01 | `FACTURA_COMPRA_OCR_ADAPTER=heuristic` | Mismos tests actuales `test_heuristic_pdf`, `test_ocr_pipeline` pasan |
| BC-02 | `ejecutar_pipeline_ocr` | Estructura de `resultado_ocr` con claves `texto_plano`, `campos_cabecera`, `lineas_sugeridas`, `raw` |
| BC-03 | API documento upload | Sin cambio de contrato JSON público de expediente (campos nuevos solo adicionales en `raw`) |

---

## 8. Orden sugerido de escritura de tests (TDD)

1. BC-01 / BC-02 (regresión existente)
2. CLF-01–04 (clasificador puro, sin I/O pesado)
3. PRE-04 (contrato fallback)
4. OCR-01–02 (TSV + líneas)
5. VAL-01–02 (validación sobre dicts sintéticos)
6. Integración ligera adapter mock

---

## Notas

- Los tests **no** deben depender de Tesseract en CI si se desactiva con `FACTURA_COMPRA_OCR_TESSERACT_ENABLED=False`; usar mocks o fixtures de texto ya extraído.
- Mantener **docker exec Synap_app** para ejecución según reglas del proyecto.
