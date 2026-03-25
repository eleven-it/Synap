# Diseño — Arquitectura incremental del motor de documentos (in-house)

**Contexto:** evolución del pipeline existente en `factura_compra_captura` sin servicios OCR en la nube ni reemplazo del flujo de aprobación/posting.

**Principio:** el **HeuristicOcrAdapter** y el parser por regex **permanecen**; un **motor interno** se introduce como capas opcionales detrás de flags y/o un adapter hermano.

---

## Visión general de capas

```
Archivo (PDF/imagen)
    → DocumentClassifier
    → [opcional] ImagePreprocessor
    → Extracción texto / OCR (plano o estructurado)
    → StructuralParsers (cabecera / tabla / fiscal)
    → SemanticNormalizer
    → ValidationEngine (evidencias, no bloqueo por defecto en borrador)
    → OcrExtractResult (compatible) + raw enriquecido
```

La **API** hacia `DocumentoFuente.resultado_ocr` conserva las claves actuales; las extensiones viven en `raw` y, si aplica, subclaves versionadas (`raw.document_engine_v1`).

---

## A. DocumentClassifier

**Objetivo:** etiquetar el documento para enrutar el pipeline sin romper el flujo único actual.

**Salida sugerida (dataclass / dict):**

| Campo | Valores |
|-------|---------|
| `tipo_archivo` | `pdf_texto_embebido` \| `pdf_probable_escaneo` \| `imagen_camara` \| `imagen_escaneo` \| `desconocido` |
| `probable_factura` | `bool` + `motivo` (palabras clave AFIP, layout) |
| `metricas` | `ratio_texto_caracteres`, `paginas`, `puede_tener_texto_nativo` |

**Heurísticas iniciales (sin ML externo):**

- PDF: si `pypdf` devuelve > N caracteres por página → `pdf_texto_embebido`; si pocas páginas y muy poco texto → `pdf_probable_escaneo` (futuro: rasterizar página y OCR).
- Imagen: EXIF / dimensiones / relación aspecto → hint `imagen_camara` vs `imagen_escaneo` (suave).

**Integración:** el clasificador **no** sustituye la rama MIME actual; informa `raw.clasificacion` para el motor y para logs.

---

## B. ImagePreprocessor

**Objetivo:** mejorar legibilidad antes de Tesseract **solo con herramientas locales** (OpenCV, Pillow).

**Pipeline configurable (orden sugerido):**

1. Conversión a escala de grises / RGB estable
2. **DPI / tamaño:** normalizar lado largo (similar a la lógica ya existente de resize en `heuristic_pdf`, pero centralizada)
3. **Deskew:** estimación de ángulo (Hough / minAreaRect) + rotación
4. **Orientación:** detección 0/90/180/270° (proyección de proyección o Tesseract `osd` si se habilita)
5. **Crop:** máscara de contenido (opcional) para márgenes excesivos
6. **Perspective:** solo si hay contorno de documento claro (evitar falsos positivos en fotos casuales)
7. **Denoise:** bilateral / NLMeans (parametrizado)
8. **Binarización adaptativa** (Otsu / adaptive) para Tesseract en escenas de bajo contraste

**Salida:** imagen PIL/ndarray + metadatos `preprocesado_aplicado[]` en `raw` para explicabilidad.

**Restricción:** si el preproceso falla, **fallback** a la imagen original (comportamiento actual).

---

## C. Layout / extracción OCR estructurada

**Objetivo:** pasar de un único string a **estructura** reutilizable para parsers y validación.

### Opciones Tesseract (solo en servidor)

| Formato | Pros | Contras |
|---------|------|---------|
| **TSV** | Fácil de parsear en Python; incluye `conf`, `left`, `top`, `width`, `height`, `text`, `page_num`; bien soportado por pytesseract | Requiere reconstrucción de líneas/bloques |
| **hOCR** | XML estándar; buenos visores | Más pesado de parsear |
| **ALTO** | Similar a hOCR | Menos habitual en scripts rápidos |

**Recomendación:** **TSV** como formato **primario** v1 para Synap: integración simple, confidence por palabra, y reconstrucción de líneas agrupando por `page_num` + coordenada Y (con tolerancia).

**Contrato interno sugerido:**

```text
StructuredOcrPage { page_num, lines: [{ text, y0, y1, words: [{text, conf, bbox}], ...}] } 
```

Estructura guardada en `raw.ocr_structured` (o `raw.document_engine_v1.ocr`) con **tamaño acotado** (no almacenar TSV completo de 50 páginas sin límite).

**PDF con texto nativo:** no hace falta TSV; se puede sintetizar “líneas” desde el texto por `\n` con `conf` sintético alto (para unificar interfaz al parser).

---

## D. Structural parsers (separados)

1. **HeaderParser** — CUIT, razón social, punto de venta, nro, fechas, totales, COD AFIP  
   - Entrada: texto plano **y/o** líneas estructuradas  
   - Salida: `campos_cabecera` + `campos_cabecera_confidence` (opcional)

2. **LineItemParser** — tabla de ítems  
   - Entrada: líneas con coordenadas para agrupar columnas (mejor con TSV)  
   - Salida: `lineas_sugeridas` + `lineas_sugeridas_evidencia` (referencias a líneas/bbox)

3. **FiscalFieldParser** — letra, código AFIP, CAE, tipo comprobante  
   - Puede compartir regex con el heurístico actual; extraído a módulo para testear aislado

**Regla:** el parser heurístico **actual** puede seguir siendo el **único** que rellena `campos_cabecera` en v1; los parsers nuevos rellenan solo `raw` hasta validación.

---

## E. SemanticNormalizer

**Objetivo:** una capa única de normalización **después** de extracción, **antes** de validación y de mezcla con UI.

**Entidades:** fechas (ISO / DD/MM/YYYY), montos (ARS, separadores), CUIT (11 dígitos + formato), nro comprobante (PV-secuencia), moneda, cantidades, alícuotas.

**Referencias:** alineación con `core.utils.administranet_types` y documentación de tipos AdministraNET.

**Salida:** `campos_normalizados` + flags `ambiguo`/`requiere_revision`.

---

## F. ValidationEngine

**Objetivo:** evidencias **no bloqueantes** en borrador (salvo política explícita futura).

**Comprobaciones:**

- Σ (cantidad × precio línea) vs subtotal / total declarado (tolerancia)
- Subtotal + impuestos vs total (si el texto aporta desglose)
- Consistencia de identidad: mismo CUIT/nro en cabecera
- Coherencia fiscal: letra vs COD AFIP (si ambos presentes)
- Integración con **duplicate_detection** existente (solo señal; duplicado real sigue reglas de negocio actuales)

**Salida:** `raw.validaciones: [{ codigo, severidad, mensaje, evidencia}]` — `severidad` info | warning | error (error no bloquea OCR por defecto).

---

## G. Bucle de feedback del analista

**Objetivo:** mejorar heurísticas con datos sin ML cloud.

**Captura sugerida (metadata en expediente o tabla futura):**

- Campos **corregidos** respecto a la sugerencia OCR (diff campo a campo)
- `documento_fuente_id` + versión de motor (`raw.motor_version`)
- Opcional: hash de archivo para agrupar plantillas

**Uso:** análisis offline (scripts), ajuste de regex, plantillas por proveedor; **no** en el camino crítico de la primera versión del motor.

---

## Integración con adapters y flags

| Mecanismo | Descripción |
|-----------|-------------|
| `FACTURA_COMPRA_OCR_ADAPTER` | Mantener `heuristic`; añadir `internal_v1` o similar cuando exista |
| `FACTURA_COMPRA_OCR_ENGINE_MODE` (nuevo) | `legacy` \| `preprocess_only` \| `structured_ocr` \| `full_v1` |
| `HeuristicOcrAdapter` | Envolver: preproceso → Tesseract TSV → merge con heurístico; **fallback** siempre al comportamiento actual |

**Contrato:** `OcrExtractResult` inmutable en campos obligatorios; enriquecimiento solo en `raw` y, si se acuerda, campos opcionales nuevos en `campos_cabecera` (p. ej. `_meta` evitado en favor de `raw`).

---

## Tecnologías (in-house)

- **OpenCV** (`opencv-python-headless` recomendado en servidor)
- **Pillow** (ya en uso)
- **pytesseract** + **Tesseract** (ya en uso)
- **pypdf** (ya en uso)

**No** se introducen servicios de pago ni APIs de inferencia en la nube en esta arquitectura.
