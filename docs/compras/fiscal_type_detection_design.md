# Diseño: detector fiscal y mapeo AdministraNET (factura compra)

## Fuente de verdad AFIP / AdministraNET

- **`docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md`**: CbteTipo `1→FA`, `6→FB`, `11→FC`.
- Código existente alinea **51→FM** (Factura MiPyME); se mantiene para no romper heurísticos previos.

Ampliaciones de texto (`COD.`, `Código`, `Cbte Tipo`) son **solo patrones de extracción**, no nuevos códigos de negocio.

## Servicio `fiscal_type_detector.py`

**Función principal:** `detectar_tipo_fiscal(texto, ocr_structured=None, campos_heuristicos=None) -> dict`

### Salida (schema_version 1)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `schema_version` | int | 1 |
| `adminnet_tipo_factura` | str \| null | `FA` / `FB` / `FC` / `FM` o `null` si no resolvible |
| `fiscal_letter` | str \| null | `A`/`B`/`C`/`M` si aplica |
| `afip_cbte_code` | int \| null | Código numérico AFIP (p. ej. 11), no string con ceros |
| `afip_cbte_code_raw` | str \| null | Fragmento capturado (p. ej. `011`) |
| `document_kind` | str | `FACTURA` \| `NOTA_CREDITO` \| `NOTA_DEBITO` \| `UNKNOWN` |
| `confidence` | float | 0..1 |
| `source` | str | `structured_ocr_line` \| `afip_code_text` \| `factura_letra_text` \| `isolated_letter_near_factura` \| `heuristic_campos` \| `merged` \| `unknown` |
| `consistency_status` | str | `consistent` \| `inconsistent` \| `unknown` |
| `evidence` | dict | `raw_text`, `page` (opcional), `bbox` (opcional) |
| `adminnet_mapping` | dict | `afip_cbte_code`, `adminnet_tipo_factura`, `doc_ref` (ruta doc) |

### Prioridad de detección

1. **Líneas OCR página 1** (o primera página): `FACTURA [A-M]` + variantes NOTA; líneas con `COD.`/`Código`/`Cbte Tipo`; letra aislada en línea `^[ABC]$` en ventana de líneas cerca de `FACTURA`.
2. **Texto compacto** (misma lógica que `_compactar_espacios_pdf`) para unir `COD.` + `011`.
3. **Códigos AFIP** en texto completo (orden de aparición: primero `Cbte Tipo` explícito, luego `COD.`).
4. **Campos heurísticos** (`campos_heuristicos.tipo_factura`) como apoyo con confianza media.
5. **Letra aislada** cerca de FACTURA (multilínea, no compacto).
6. Si no hay señal: **`adminnet_tipo_factura: null`**, `source: unknown` — **nunca** inventar FA.

### Consistencia

- Si letra y código existen y mapean a distinto tipo AdministraNET → `inconsistent` + `confidence` menor; **regla de fusión documentada**: prevalece **código AFIP** (comportamiento ARCA típico cuando la letra impresa es ambigua).

## Integración `header_parser`

Orden de resolución del campo `tipo_factura`:

1. Resultado del detector con `adminnet_tipo_factura` no nulo y `confidence >= umbral` (p. ej. 0.45).
2. Reglas actuales (OCR línea, heurístico cab, texto, COD) como respaldo.

El detector se llama **una vez** en `parsear_cabecera_documento` (o se pasa desde `heuristic_pdf` para evitar duplicar).

## Integración `document_engine_v1`

- `de["fiscal_type_detection"] = ` resultado del detector (copia o referencia).

## Integración revisión

- **Sin default FA**: si no hay `tipoOcr` ni `tipoGuardado`, valor `''` y primera opción “— Seleccionar —”.
- Exponer en `revision_engine_context` el bloque `fiscal_type_detection` si existe.

## Alcance explícito no modificado

- Posting, `LegacyPostingAdapter`, duplicados, validación fiscal de negocio, contrato `OcrExtractResult`.
