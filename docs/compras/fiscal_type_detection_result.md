# Resultado: detección de tipo fiscal en facturas de compra

## 1. Problema corregido

- La pantalla de revisión podía mostrar **FA** por defecto (`tipoOcr || tipoGuardado || 'FA'`) aunque el documento no lo indicara.
- Combinaciones claras como **letra C** + **COD. 011** no siempre se reflejaban de forma estable en la cabecera parseada o en el desplegable.

## 2. Estrategia de detección

Servicio dedicado: `factura_compra_captura/services/fiscal_type_detector.py` (`detectar_tipo_fiscal`).

Prioridad conceptual (alineada al diseño en `fiscal_type_detection_design.md`):

1. **Fusión letra + código AFIP** cuando ambos existen; si discrepan, **prevalece el código AFIP** (`consistency_status: inconsistent`, confianza menor).
2. **Solo código AFIP** (p. ej. `COD. 011`, `Cbte Tipo: 011`, variantes ruidosas).
3. **Línea OCR estructurada** página 1 (`FACTURA C`, etc.).
4. **Texto plano** (`FACTURA C`, letra aislada cerca de FACTURA).
5. **Heurístico de cabecera** `tipo_factura` solo si ya es **FA/FB/FC/FM** explícito (no inventa tipo).

**No** hay fallback silencioso a FA en el detector.

## 3. Normalización de código AFIP

- Función `normalizar_codigo_cbte_afip`: elimina no dígitos y convierte a entero (`011`, `11`, `0011` → `11`).
- Patrones admitidos incluyen `COD.`, `Cód.`, `Código`, `Cbte Tipo`, y variante ruidosa tipo `COD.. 011`.

## 4. Mapeo a AdministraNET

Fuente documental: `docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md` (tabla CbteTipo → uso en proyecto).

Tabla aplicada en código (`MAP_CBTE_ADMINNET`):

| CbteTipo | AdministraNET (`tipo_factura`) |
|----------|--------------------------------|
| 1        | FA                             |
| 6        | FB                             |
| 11       | FC                             |
| 51       | FM (MiPyME, alineado a heurísticos existentes) |

El resultado incluye `adminnet_mapping.doc_ref` apuntando al documento de referencia.

## 5. Integración en el motor y cabecera

- `document_engine_v1.fiscal_type_detection`: resultado completo del detector (aditivo).
- `parsear_cabecera_documento` usa el detector **antes** que línea OCR duplicada, heurística de cabecera, regex texto y `COD` ARCA legacy.
- `_enriquecer_raw_document_engine_stage2` en `heuristic_pdf.py` rellena `fiscal_type_detection` en el `document_engine_v1` expuesto en `raw`.

## 6. Revisión (UI)

- `revision_engine_context.fiscal_type_detection` expone el mismo bloque para el front.
- El `<select>` de letra fiscal incluye opción vacía **— Sin seleccionar —**.
- Valor inicial: `tipoOcr || tipoGuardado || sugerencia del detector || ''` (sin `|| 'FA'`).

## 7. Comportamiento ante tipo desconocido

- Cabecera: `tipo_factura.valor` puede ser `None`.
- Detector: `adminnet_tipo_factura` `None`, `source: unknown`.
- UI: selección vacía hasta que el usuario elija.

## 8. Limitaciones

- Solo se mapean códigos AFIP presentes en `MAP_CBTE_ADMINNET`; otros códigos no generan `adminnet_tipo_factura` automático (evita inventar semántica).
- OCR muy degradado puede impedir coincidencia de líneas estructuradas.
- La validación fiscal de negocio y el posting **no** fueron modificados; otros módulos pueden seguir usando valores por defecto internos para flujos distintos (p. ej. duplicados) según su código histórico.
