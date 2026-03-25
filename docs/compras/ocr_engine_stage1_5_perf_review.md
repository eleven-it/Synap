# OCR Stage 1.5 — Rendimiento y tamaño de payload

## Dónde crece el JSON

El pipeline persiste en `DocumentoFuente.resultado_ocr` (JSON) la estructura:

- `texto_plano`, `confianza_global`, `campos_cabecera`, `lineas_sugeridas`, **`raw`**.

En modos distintos de `legacy` (solo imágenes), `raw` puede incluir `document_engine_v1` con:

- `preprocess`: metadatos pequeños (pasos, `fallback`, `motivo` opcional).
- `ocr_structured`: resumen derivado del dict Tesseract, **no** el TSV completo.

## Acotaciones ya presentes (Stage 1)

En `tesseract_structured.py`:

- **`palabras_muestra`:** como máximo **500** palabras con texto, confianza y caja; evita explosión en documentos largos.
- **Texto por línea** en el resumen de páginas: truncado a **500** caracteres por entrada de línea.
- **Texto por palabra** en muestra: **200** caracteres.

No hay cap explícito al número de **páginas** ni de **líneas** en el array `pages`; en facturas típicas (1–2 páginas) el impacto es bajo. Un PDF exportado a imagen muy largo o un escaneo multipágina podría incrementar el tamaño del JSON de forma acorde al contenido.

## Coste CPU / tiempo

| Modo | Trabajo extra respecto a legacy |
|------|----------------------------------|
| `legacy` | Ninguno (baseline). |
| `preprocess_only` | OpenCV (CLAHE + denoise) sobre la imagen ya escalada por PIL; coste usualmente modesto frente a Tesseract. |
| `structured_ocr` | Preprocesado + **`image_to_string`** (texto plano) + **`image_to_data`** (TSV). Son **dos** pasadas Tesseract sobre la misma imagen procesada. |

Para Stage 2 conviene medir en entorno real con fotos representativas; no se aplicó optimización agresiva en esta revisión.

## Riesgo de almacenamiento

- `resultado_ocr` completo vive en PostgreSQL (campo JSON). Con `structured_ocr` y facturas normales, el incremento debería ser **acotado** por límites de muestra y truncados de texto.
- Si en el futuro el volumen de `pages[].lines` fuera problemático, candidatos de salvaguarda (sin implementar aún):
  - limitar líneas totales o páginas en el resumen;
  - almacenar solo estadísticas agregadas + muestra más pequeña;
  - opcional: no persistir `document_engine_v1` completo y guardarlo en almacenamiento objeto aparte (cambio de diseño, no hecho en Stage 1.5).

## Logging

Los fallos del bloque TSV estructurado generan un **warning** en el logger del módulo (`heuristic_pdf`), con mensaje truncado, sin volcar trazas completas por defecto.

## Conclusión

No se detectó un problema crítico de tamaño o CPU para el caso de uso factura compra típico. El punto a vigilar para evolución es la **doble pasada Tesseract** en `structured_ocr` y el crecimiento potencial del JSON en documentos **muy** largos si se usa el mismo motor sin límites de página.
