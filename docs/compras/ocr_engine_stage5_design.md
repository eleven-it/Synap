# OCR factura compra — Stage 5 diseño (plantillas proveedor y señales de workflow)

## Objetivo

Especializar el motor documental por **plantilla de proveedor** (reglas declarativas) y exponer **señales** para revisión/analista, sin ML, sin cambiar posting ni validaciones de negocio, y manteniendo el motor **genérico** como base.

## 1. SupplierTemplateMatcher

- **Entradas:** `campos_cabecera` (legacy), `parsed.header` (Stage 2), opcionalmente texto plano.
- **Salida:** `supplier_template_match`: `{ template_id | null, matched_by, confidence }`.
- **Estrategia:** registro ordenado por `priority`; primera plantilla cuyo criterio coincida **gana**. Criterios típicos: CUIT normalizado (11 dígitos), palabras clave en razón social.

## 2. Reglas por proveedor (registry)

- Fichero declarativo: `supplier_template_registry.py` con diccionario `SUPPLIER_TEMPLATES`.
- Campos por plantilla: `label`, `priority`, `match_cuit_digits` (exacto), `extra_header_regex` (p. ej. CAE), `line_supplement_patterns` (lista de regex opcionales para filas adicionales).

## 3. Estrategia de override (template vs genérico)

- **`parsed.header`** y **`parsed.line_items`** del Stage 2–4 **no se modifican** (contrato estable).
- Resultados específicos de plantilla van en **`template_application`**: `header_fields`, `line_items` (vista enriquecida o suplemento), `notes`.
- Consumidores de UI/workflow pueden **preferir** `template_application` cuando `supplier_template_match.template_id` está presente.

## 4. Fallback al motor genérico

- Si no hay match o la plantilla es `generic`: `template_application` puede ser `null` o objeto mínimo con `template_id: "generic"`.
- Extracción genérica (cabecera, líneas, validaciones) **sigue igual** que Stage 4.

## 5. Señales orientadas a workflow (`workflow_signals`)

| Campo | Uso |
|-------|-----|
| `supplier_template_id` | Plantilla activa o `null`. |
| `template_matched` | Booleano. |
| `suggested_review` | Heurística (p. ej. validaciones con warning/error). |
| `blocking_issues` | Reservado; siempre `false` en Stage 5 (sin bloqueo automático). |

## 6. Feedback de analista (`analyst_feedback`)

- Estructura reservada para correcciones posteriores (API/UI), **sin** escribir en tablas de negocio desde el motor OCR.
- `schema_version`, `corrections`: lista vacía por defecto; elementos futuros: `{ path, valor_anterior, valor_nuevo, nota, registrado_en }`.

## 7. Versión `document_engine_v1`

- `version >= 6` cuando existan `supplier_template_match`, `workflow_signals` y el bloque de feedback.

## 8. Limitaciones

- No hay aprendizaje automático ni auto-aprobación.
- Plantillas son reglas mantenidas en código/registry (evolución futura: BD).
