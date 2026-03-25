# OCR factura compra — Stage 2.5 diseño (consolidación)

## Objetivo

Formalizar sin romper contratos existentes:

- reglas de confianza por campo y por banda;
- esquema único de evidencia;
- puntuación a nivel documento;
- resumen de campos críticos faltantes;
- comprobaciones de consistencia entre parser **legacy** y cabecera Stage 2;
- límites de **fuente de verdad** entre `campos_cabecera` y `document_engine_v1`.

**Fuera de alcance:** ítems de línea, posting, aprobación, APIs públicas nuevas, cambios en `OcrExtractResult`.

---

## 1. Fuentes de verdad (boundaries)

| Artefacto | Rol | Consumo recomendado |
|-----------|-----|---------------------|
| `resultado_ocr.campos_cabecera` (y derivados en expediente) | **Legacy canónico** para flujos ya existentes: mismas claves que desde siempre (`proveedor_texto`, `nro_comprobante_texto`, `importe_total_texto`, etc.). | Pantallas, validaciones previas y cualquier lógica que ya dependa del parser heurístico único. |
| `resultado_ocr.raw.document_engine_v1` | **Capa analítica enriquecida**: clasificación, cabecera con confianza/evidencia, calidad y consistencia. | Trazabilidad, futuras UX de revisión, métricas, y **no** sustituye al legacy hasta decisión explícita de producto. |

**Regla:** Stage 2/2.5 **no modifica** `campos_cabecera`; solo **lee** `campos_cabecera` para alimentar el modelo de cabecera y para **comparar** con lo extraído en `parsed.header`.

**Conflicto aparente:** si `parsed.header.total` difiere de `importe_total_texto`, la inconsistencia queda registrada en `parsed.header_quality.consistencia_legacy`; la resolución de negocio sigue siendo responsabilidad humana o de una fase posterior, no de este stage.

---

## 2. Confianza por campo (formalización)

### 2.1 Bandas

- **alta:** `confidence >= 0.75`
- **media:** `0.5 <= confidence < 0.75`
- **baja:** `confidence < 0.5`

Cada campo de cabecera incluye `banda` derivada de `confidence` (redondeada a 4 decimales).

### 2.2 Constantes (`confidence_catalog.py`)

Los valores numéricos de confianza por tipo de extracción están centralizados:

- **structured:** línea OCR (`CONF_STRUCTURED_LINEA`, …), token OCR (`CONF_STRUCTURED_TOKEN`), tipo en línea (`CONF_STRUCTURED_TIPO_LINEA`), total en línea (`CONF_STRUCTURED_TOTAL_LINEA`).
- **heuristic:** copia desde `parsear_texto_factura` (`CONF_HEURISTIC_*`).
- **raw:** solo regex sobre texto plano (`CONF_RAW_*`).
- **débil:** CUIT como sustituto de razón social (`CONF_WEAK_CUIT_*`).

Cualquier ajuste futuro debe hacerse en el catálogo y reflejarse en tests.

---

## 3. Evidencia estándar

Toda evidencia bajo `parsed.header.<campo>.evidencia` sigue:

| Clave | Tipo | Significado |
|-------|------|-------------|
| `schema_version` | int | Versión del esquema (actualmente `1`). |
| `page` | int \| null | Página 1-based cuando aplica (OCR / PDF); `null` si solo hay texto plano. |
| `bbox` | objeto \| null | `{left, top, width, height}` en coordenadas de imagen Tesseract; `null` si la evidencia es de línea agregada o texto plano. |
| `raw_text` | string | Fragmento (≤800 caracteres) donde se basó la extracción. |

---

## 4. Puntuación a nivel documento (`document_score`)

`document_engine_v1.document_score` ∈ [0, 1] es una **heurística compuesta** (no probabilidad calibrada):

| Componente | Peso | Descripción |
|--------------|------|-------------|
| Clasificación del documento | 0.15 | `classification.confidence` (invoice_probable vs unknown). |
| Promedio de confianza de campos con valor | 0.55 | Media de `confidence` de los seis campos críticos que tengan `valor`. |
| Completitud de campos críticos | 0.20 | `1 - (faltantes / 6)`. |
| Consistencia legacy ↔ header | 0.10 | `consistencia_legacy.score` (0 si hay checks; proporción de checks OK). |

Si no hay checks comparables (pocos datos en legacy), el score de consistencia se considera 1.0 para no penalizar.

Pesos exportados en `parsed.header_quality.pesos_document_score` y desglose en `componentes_document_score`.

---

## 5. Campos críticos faltantes

`parsed.header_quality.campos_criticos` es un objeto:

- `lista`: nombres de campo entre `proveedor`, `tipo_factura`, `punto_venta`, `numero`, `fecha`, `total` con `valor` nulo en el modelo Stage 2.
- `cantidad` / `total_campos`: conteo.

No sustituye a validaciones de negocio; solo resume **vacíos** en el modelo enriquecido.

---

## 6. Consistencia legacy (`consistencia_legacy`)

Para cada par de valores presentes en **ambos** lados se añade un ítem en `checks`:

- `tipo_factura`
- `fecha_comprobante` (texto normalizado espacialmente)
- `punto_venta` + `numero` vs `nro_comprobante_texto`
- `importe_total` (normalización decimal simple para comparar)

Cada check incluye `ok`, `legacy`, `header`, `detalle`.

`score` = proporción de checks con `ok=True` (si no hay checks, no se penaliza en el documento).

---

## 7. Versión de `document_engine_v1`

- `version >= 3` indica presencia del paquete Stage 2.5 (`document_score`, `parsed.header_quality`, evidencia con `schema_version`, `banda` en campos).

---

## 8. Limitaciones

- No hay modelo ML; `document_score` es **comparativo** entre documentos, no estimación bayesiana.
- Normalización de importes para consistencia es **simple**; casos extremos (múltiples monedas, redondeos) pueden requerir reglas futuras.
