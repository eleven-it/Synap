# Módulo IA: modelos LLM y rangos de fecha

## OpenAI Chat Completions: límite de salida

En `ia/services/llm_gateway.py`, las llamadas a `/v1/chat/completions` usan **`max_completion_tokens`** para modelos de la familia **gpt-5** (y series **o1/o3/o4**), y **`max_tokens`** para el resto. Si la API responde 400 pidiendo `max_completion_tokens`, se reintenta una vez con ese parámetro.

## Modelos OpenAI (preset)

En `ia/services/provider_presets.py`, la lista `available_models` del preset OpenAI incluye **`gpt-5.4`** para pruebas. El modelo recomendado por defecto sigue siendo `gpt-4.1` hasta validar costos y disponibilidad en la API.

Para usar `gpt-5.4` en un agente: configuración del proveedor en Synap (o `LlmProviderConfig`) con ese nombre en modelos disponibles y selección como modelo principal del agente.

## Rangos de fecha en lenguaje natural

Si el usuario indica solo un **mes nominal sin año** («en abril», «mes de marzo»), se resuelve el **mes calendario completo del año en curso** (`calendar_month_named_implicit_year`), p. ej. abril de 2026 si hoy es 2026. Si el mes va con año explícito («abril 2025»), prevalece ese año.

**Importante:** frases del tipo **«entre abril de 2025 y hoy»** o **«desde abril de 2025 y hoy»** deben resolverse como rango **desde el 1/4/2025 hasta la fecha actual** (`since_month_until_today`), no como el solo mes de abril de 2025. El patrón acepta `desde` o `entre` y el enlace al día de hoy con **y**, **a** o **hasta**.

En el **asistente de reportes**, `ReportAgentService.handle_query` resuelve fechas con el **mismo texto canónico que `interpret_query`** (transcript + mensaje actual). Así, un seguimiento del tipo «Incluye PUIG» o «sin excluir al cliente X» mantiene el período acordado en el hilo y solo cambian filtros (p. ej. quitar `clientes_excluidos`).

**MPR y logística (enrutamiento):** Las preguntas que mencionan **MPR** junto con pedidos/pendientes/producción se resuelven al reporte **`mpr-pedidos-estado`** (resumen por `estado_pedido_opt`), no al reporte **`pedidos-pendientes`** (PED en preparación en depósito). Las preguntas sobre **logística** y **entregas** / **rutas** / **pendientes de entrega** se resuelven al listado **`comprobantes-rutas`**, usando palabras clave del **mensaje actual** para no confundir la intención con un turno previo de ventas. Esos reportes pueden ejecutarse **sin período obligatorio**; si el texto trae fechas, se aplican como filtro opcional al listado logístico.

`DateRangeService` reconoce entre otros:

- **Entre dos meses con año:** «entre enero 2025 y febrero 2026», «de marzo 2025 a junio 2025», «desde enero 2025 hasta febrero 2026» → tipo `calendar_month_range_named`, del primer día del mes inicial al último día del mes final.
- **Entre dos meses con un solo año al final:** «entre enero y diciembre de 2025», «de enero a diciembre de 2025», «desde enero hasta diciembre de 2025» → tipo `calendar_month_range_same_year` (evita que solo se tome el último mes nominal, p. ej. diciembre).

## Sucursal en conversación

En `interpret_query`, el matching de sucursal usa el **texto canónico** (snippet + mensaje actual), no solo el último turno, para que un seguimiento del tipo «dame el listado mes a mes» siga aplicando la sucursal mencionada antes.

## Exclusión de cliente por nombre (asistente de reportes)

Si el usuario pide no incluir / excluir / excepto **cliente** «X», `interpret_query` busca en la tabla `cliente` por subcadena en `nombre_cliente`. **Una** coincidencia → se envía `clientes_excluidos` al payload. **Ninguna** → aclaración. **Varias** → mensaje con lista numerada (código y nombre) para que el usuario indique cuál excluir en un turno siguiente (respuesta más precisa o número).

## Desglose por tipo de comprobante (consultas de ventas)

`aggregate_movimientos_por_tipo_comprobante` solo incluye **FA, FB, FC, FE y FM** (facturas de venta), alineado a los conteos FA–FM del asistente. No lista recibos (REC), ajustes (AJ) ni notas de crédito (NCA, NCB, …).

## Facturas mes a mes sin punto de venta

Si el usuario pide **cantidad** de facturas con frases como **«comprobantes x mes»** (sin mencionar punto de venta), se activa el desglose **mensual por tipo de letra** (FA…FM), no el total único del período.

## Total de ventas e importes (vs cantidad de comprobantes)

Si la pregunta habla de **total de ventas**, **importe**, **monto**, **pesos**, etc., y además un desglose **mes a mes** / **comprobantes x mes**, la intención se dirige al reporte **ventas netas** con totales mensuales de negocio (importes), no al conteo SQL de facturas FA–FM.

El **asistente de reportes** resuelve primero la intención con reglas fijas en código (`interpret_query`). Opcionalmente, si el agente tiene proveedor con API key activa, puede ejecutarse un paso **`ReportIntentRefinementService`**: un modelo **rápido** (`ModelSelectionService`, `task_type="fast"`, típicamente `fast_model_name`) devuelve **solo JSON acotado** (métrica: importes vs cantidad de facturas, desglose mensual, desglose por punto de venta, confianza). Ese resultado se fusiona con `apply_llm_intent_hints` para corregir desvíos frecuentes (p. ej. conteo de facturas vs totales de ventas mensuales) **sin sustituir** toda la heurística. Si el refinamiento falla o está desactivado (`agent.config["report_intent_refinement"] = false`), el flujo sigue igual que antes.

El modelo LLM **no arma SQL**; la ejecución sigue siendo determinista. Puede usarse además para **redactar** el resumen a partir de los datos ya obtenidos (`_try_llm_summary`), según configuración y fase del flujo.

## Formato de salida (respuestas deterministas del asistente de reportes)

En `_build_deterministic_answer`, los períodos mostrados al usuario usan **dd/MM/yyyy** según `policy_context.locale` (incluye **pedidos pendientes**, **resumen de ventas**, **remitos no facturados** y ventas netas). El bloque por mes de ventas netas añade líneas en blanco entre encabezado, lista y **`Total:`**; con sucursal detectada el encabezado indica `(sucursal: …)` en lugar de `(total empresa)`.

## Aprendizaje desde el chat y export para fine-tuning

Captura opcional de turnos en `AgentLearningExample`, revisión por API y exportación JSONL: ver **`docs/general/APRENDIZAJE_IA_CHAT_Y_FINETUNING.md`**.
