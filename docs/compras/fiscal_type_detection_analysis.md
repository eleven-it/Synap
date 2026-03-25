# Análisis: detección de letra / tipo fiscal (factura compra)

## 1. Dónde se extrae hoy la letra fiscal

| Etapa | Ubicación | Comportamiento |
|-------|-----------|----------------|
| Heurístico PDF/imagen | `factura_compra_captura/ocr/heuristic_pdf.py` → `parsear_texto_factura` → `_tipo_factura_desde_texto` | Orden: `FACTURA [A-D]` en línea; `COD.\s*(\d+)` / `Cód.`; `tipo de comprobante` numérico; letra suelta A/B/C cerca de FACTURA. Mapeo numérico: `_MAP_CBTE_AFIP_A_LETRA` = `{1: FA, 6: FB, 11: FC, 51: FM}`. |
| Cabecera enriquecida (Stage 2) | `factura_compra_captura/services/header_parser.py` → `parsear_cabecera_documento` | Orden actual: (1) línea OCR con `_RE_FACTURA_LETRA`; (2) `campos_heuristicos.tipo_factura` desde `parsear_texto_factura`; (3) regex en texto plano `_RE_FACTURA_LETRA`; (4) `_RE_COD_ARCA` sobre `texto` completo. `_MAP_CBTE` = `{1,6,11,51}` → FA/FB/FC/FM. |
| Motor documental | `raw.document_engine_v1.parsed.header.tipo_factura` | Copia del resultado de `parsear_cabecera_documento`. |

## 2. Origen en pantalla de revisión

- **GET expediente** → `metadata.posting_v1.header.tipo_factura` (borrador guardado).
- **Último documento** → `resultado_ocr.campos_cabecera.tipo_factura` (heurístico al subir archivo).
- **UI** (`revision_expediente.html`): tras cargar, `tipoOcr = cab.tipo_factura`, `tipoGuardado = h.tipo_factura`, y se asigna:

```javascript
document.getElementById('tipo_fiscal').value = tipoOcr || tipoGuardado || 'FA';
```

Ese **`|| 'FA'`** fuerza **FA** cuando OCR y borrador no traen valor, aunque el PDF muestre C + COD.011 (si la cadena anterior falló o quedó vacía).

- El `<select id="tipo_fiscal">` tiene **primera opción FA** sin opción vacía explícita; el navegador no “elige solo FA”, pero el JS sí inyecta `'FA'` como fallback.

## 3. Dónde aparece FA como implícito

| Sitio | Notas |
|-------|--------|
| Revisión web | Fallback `tipoOcr \|\| tipoGuardado \|\| 'FA'` (ver arriba). |
| `factura_compra_captura/services/fiscal_invoice_validation.py` | `tipo_factura or "FA"` en un camino de comando (no tocado en esta evolución salvo coordinación). |
| `duplicate_detection.py` | Default `"FA"` en claves; **no modificado** por requisito de alcance. |
| Tests API | Algunos payloads usan `"tipo_factura": "FA"` como dato de prueba. |

## 4. Mapeo AdministraNET / AFIP en el proyecto

- **`docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md`**: tabla **CbteTipo** — `1=FA`, `6=FB`, `11=FC` (y el código usa también **51 → FM** alineado a heurísticos existentes).
- **`docs/compras/OCR_HEURISTICO_PDF.md`**: describe el mismo criterio heurístico (COD. 011 → FC, etc.).

No hay en el repo una tabla distinta de “tipo interno AdministraNET” distinta de **FA / FB / FC / FM** para estas facturas; el posting v1 ya consume `tipo_factura` en ese vocabulario.

## 5. Problema observado (síntesis)

- **Letra aislada “C” + “COD. 011”**: el heurístico en muchos casos **sí** resuelve FC, pero la **prioridad en `header_parser`** puede dejar pasar primero una línea OCR mal interpretada (`FACTURA …` con otra letra) o dejar `tipo_factura` vacío si el orden de reglas no alinea con el layout ARCA.
- **UI**: con valor vacío, el fallback a **FA** es incorrecto; debe quedar **sin selección forzada** o mostrar estado explícito “no detectado”.

## 6. Conclusión para la evolución

- Introducir un **detector dedicado** con prioridad clara (estructura + código AFIP + consistencia), invocado **antes** de cerrar el campo `tipo_factura` en `parsear_cabecera_documento`.
- Publicar resultado en **`document_engine_v1.fiscal_type_detection`** (aditivo).
- Ajustar **solo la revisión** (fallback JS + opción vacía en el `<select>`), sin tocar posting ni duplicados.
