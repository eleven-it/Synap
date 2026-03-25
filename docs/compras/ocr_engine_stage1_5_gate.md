# OCR Stage 1.5 — Puerta de salida hacia Stage 2

## Preguntas obligatorias

### 1. ¿Stage 1 es reproducible desde cero?

**Sí**, siempre que el despliegue use el **`Dockerfile`** raíz del proyecto: `requirements.txt` instala `opencv-python-headless`; el mismo `Dockerfile` instala Tesseract y paquetes de idioma `spa`/`eng` vía `apt`. `docker compose build app` materializa ese estado. No debe dependerse de `pip install` manual en contenedores ya arrancados.

### 2. ¿Stage 1 es retrocompatible?

**Sí.** El valor por defecto de `FACTURA_COMPRA_OCR_ENGINE_MODE` es `legacy`, equivalente al flujo previo a preprocesado/TSV. El parser heurístico (`parsear_texto_factura`) no fue refactorizado; `OcrExtractResult` no cambió de forma incompatible.

### 3. ¿Stage 1 es seguro para evolucionar a Stage 2?

**Sí, con matices documentados.** La metadata nueva está acotada bajo `raw.document_engine_v1`; los fallos de OCR estructurado no rompen el texto plano. Conviente en Stage 2 revisar **coste de doble pasada Tesseract** y posibles **límites de páginas/líneas** en JSON si el volumen de datos creciera.

### 4. ¿Qué debe corregirse antes de Stage 2, si algo?

Nada **bloqueante** identificado en esta revisión. Recomendaciones no urgentes:

- Medir tiempos reales con `structured_ocr` en producción o preproducción.
- Si hiciera falta, en Stage 2 o 2.1: opcionalmente unificar o cachear pasadas Tesseract para reducir CPU (no implementado en 1.5).

### 5. Veredicto final

**READY_WITH_RISKS**

- **Motivo:** la reproducibilidad de build y los tests son sólidos; la retrocompatibilidad se mantiene. Los “riesgos” son **operativos y de escala** (doble Tesseract, JSON grande en escenarios extremos), no defectos de seguridad o contrato detectados en esta pasada.

No se usa **NOT_READY**. **READY_FOR_STAGE_2** quedaría reservado a un entorno donde además se hubiera medido el rendimiento en datos reales; con la información actual, **READY_WITH_RISKS** refleja mejor el estado.

---

## Documentos de soporte (Stage 1.5)

| Documento | Contenido |
|-----------|-----------|
| `ocr_engine_stage1_5_build_review.md` | Build, pip, apt, riesgos |
| `ocr_engine_stage1_5_runtime_validation.md` | Comandos y modos |
| `ocr_engine_stage1_5_perf_review.md` | Payload, CPU, salvaguardas propuestas |
| `ocr_engine_stage1_5_code_audit.md` | Auditoría de código |
| `ocr_engine_stage1_5_gate.md` | Este documento |

**Stage 2 no se inicia** hasta nueva instrucción explícita.
