# OCR factura compra — Stage 7 diseño: revisión UI y flujo analista

## Objetivo

Integrar salidas del motor documental (`document_engine_v1`, métricas Stage 6) en la **pantalla de revisión** existente (`revision_expediente.html`, `base_app.html`), sin rediseño global, sin tocar posting ni validaciones fiscales/duplicados, sin decisiones bloqueantes.

## Contexto de diseño (Synap / AdministraNET)

- No había `.impeccable.md` en el repositorio; no se ejecutó el flujo teach-impeccable. Criterios inferidos del propio módulo (`base_app.html`, Tailwind, copy en español).

- **Usuarios:** analistas de compras y supervisores en contexto ERP (escritorio y tablet).
- **Tono:** utilitario, legible, coherente con Tailwind y patrones ya usados en la plantilla (bordes `rounded-xl`, `border-gray-200`, acentos `indigo`/`emerald`).
- **No** aplicar estética “hero/cards genéricas”: paneles **aditivos** bajo el bloque “Datos del comprobante”, tipografía existente (`text-sm`, `text-xs`), sin nuevas familias de fuentes obligatorias.

Referencias de skills: layout en rejilla ya establecida (`lg:grid-cols-[...]`); evidencia como texto secundario; progresivo (panel motor colapsable).

## 1. Paneles de calidad documental

- Bloque **“Motor de documento”** (nuevo): puntuación global (`document_score`), salud de validaciones (`validation_summary`), mensaje de `workflow_facing_summary.headline`, indicador no bloqueante de revisión sugerida.
- Ubicación: debajo de `ocr_hint` / encima de “Datos del comprobante”, o inmediatamente después del subtítulo según densidad; **no** sustituye el formulario.

## 2. Confianza y evidencia por campo (cabecera)

- Datos desde `parsed.header` del último `resultado_ocr.raw.document_engine_v1`: por campo estructura `{ valor, confidence, banda, source, evidencia }`.
- UI: badges `text-xs` con confianza/banda y `title` o `<details>` con recorte de `evidencia.raw_text` (máx. ~200 caracteres en servidor si hace falta).

## 3. Evidencia por línea

- Desde `parsed.line_items[]`: por cada ítem, mostrar confianza resumida de descripción/cantidad/precio (y tooltip o fila expandible con snippet de evidencia).
- Tabla existente: añadir columnas opcionales **“Conf.”** / icono informativo para no ensanchar de más en móvil (priorizar columnas en `sm+`).

## 4. Panel plantilla / rendimiento

- Subsección dentro del panel motor: `template_performance` (match, `template_id`, conteos de campos suplementarios) y texto breve si `template_application.active`.

## 5. Captura de correcciones de analista

- Estado persistido en **`expediente.metadata.analyst_feedback`** (lista `corrections`), alineado a Stage 5/6.
- **PATCH** puede enviar `analyst_feedback_append`: lista de `{ campo, valor_anterior, valor_nuevo }` que el servidor fusiona con `append_analyst_correction` (no reemplaza posting).
- Alternativa: el cliente envía `metadata` completo con `analyst_feedback` ya fusionado (documentado como compatible).

## 6. Integración API y plantilla

- **`ExpedienteFacturaCompraSerializer`**: nuevo campo de solo lectura `revision_engine_context` (subconjunto estable para UI + cabecera/líneas con evidencia para render).
- **Vista web** `RevisionExpedienteView`: opcionalmente pasa bandera `mostrar_panel_motor` o JSON mínimo para hidratar sin duplicar lógica (la carga principal sigue siendo `GET /api/compras/expedientes/:id/` desde JS).

## 7. Límites

- Sin auto-aprobación, sin ML, sin bloquear botones según el motor.
- `OcrExtractResult` y pipeline OCR sin cambios de contrato.
