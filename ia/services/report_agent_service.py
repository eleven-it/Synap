from __future__ import annotations

import json
from dataclasses import dataclass

from ia.services.date_range_service import DateRangeService
from ia.services.llm_gateway import LlmGatewayError, LlmGatewayService
from ia.services.report_tools import ReportToolsService


@dataclass
class ReportAgentResult:
    answer: str
    response_payload: dict
    token_usage: dict
    execution_status: str
    used_report_slug: str | None = None


class ReportAgentService:
    """Primera implementación útil del Asistente de Reportes sobre `reports`."""

    def __init__(self, *, agent, policy_context, selected_model):
        self.agent = agent
        self.policy_context = policy_context
        self.selected_model = selected_model

    def handle_query(self, message_text: str) -> ReportAgentResult:
        interpreted = ReportToolsService.interpret_query(message_text, self.policy_context)
        if interpreted.requires_clarification:
            return ReportAgentResult(
                answer=interpreted.clarification_question or "Necesito una aclaración para responder con precisión.",
                response_payload={
                    "phase": "clarification",
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": interpreted.metadata,
                    },
                },
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                execution_status="partial",
                used_report_slug=interpreted.report_slug,
            )

        requires_period = interpreted.report_slug in {"sales_summary", "ventas_netas", "uninvoiced_remitos", "pedidos-pendientes"}
        date_range = DateRangeService.resolve_from_text(message_text, require_period=requires_period)
        if date_range.requires_clarification:
            return ReportAgentResult(
                answer=date_range.clarification_question or "Necesito que me indiques el período.",
                response_payload={
                    "phase": "clarification",
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": interpreted.metadata,
                    },
                },
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                execution_status="partial",
                used_report_slug=interpreted.report_slug,
            )

        report = ReportToolsService.get_report_definition(interpreted.report_slug)
        ReportToolsService.validate_report_permissions(report, self.policy_context.user)
        schema = ReportToolsService.get_report_schema(report)

        payload = ReportToolsService.build_payload(
            report_slug=report.slug,
            base_filters=interpreted.filters,
            policy_context=self.policy_context,
            date_range=date_range,
            limit=200,
        )
        result = ReportToolsService.run_report_query(report, payload, self.policy_context.user)
        previous_payload = None
        previous_result = None
        if interpreted.metadata.get("compare_previous_period") and date_range.start_date and date_range.end_date:
            previous_range = DateRangeService.previous_equivalent(
                date_range.range_type,
                date_range.start_date,
                date_range.end_date,
            )
            if previous_range:
                previous_payload = ReportToolsService.build_payload(
                    report_slug=report.slug,
                    base_filters=interpreted.filters,
                    policy_context=self.policy_context,
                    date_range=previous_range,
                    limit=200,
                )
                previous_result = ReportToolsService.run_report_query(report, previous_payload, self.policy_context.user)

        deterministic_answer = self._build_deterministic_answer(
            message_text=message_text,
            report=report,
            result=result,
            interpreted=interpreted,
            date_range=date_range,
            previous_result=previous_result,
            previous_payload=previous_payload,
        )
        llm_answer, token_usage, status = self._try_llm_summary(
            message_text=message_text,
            report=report,
            result=result,
            schema=schema,
            interpreted=interpreted,
            fallback_answer=deterministic_answer,
            previous_result=previous_result,
        )

        return ReportAgentResult(
            answer=llm_answer,
            response_payload={
                "phase": "report_runtime",
                "report_slug": report.slug,
                "report_name": report.name,
                "query_spec": {
                    "intent": interpreted.intent,
                    "report_slug": interpreted.report_slug,
                    "filters": interpreted.filters,
                    "metadata": interpreted.metadata,
                    "date_range": {
                        "type": date_range.range_type,
                        "start_date": date_range.start_date,
                        "end_date": date_range.end_date,
                    },
                },
                "row_count": len(result.data or []),
                "notes": result.notes,
                "totals": result.totals,
                "previous_period_totals": previous_result.totals if previous_result else {},
            },
            token_usage=token_usage,
            execution_status=status,
            used_report_slug=report.slug,
        )

    def _build_deterministic_answer(self, *, message_text: str, report, result, interpreted, date_range, previous_result=None, previous_payload=None) -> str:
        if result.notes and not result.data and not result.totals:
            return "\n".join(result.notes)

        if report.slug == "sales_summary":
            totals = result.totals or {}
            answer = (
                f"En el período {date_range.start_date} al {date_range.end_date}, el resumen de ventas registró "
                f"ventas netas por ${totals.get('ventas_netas', 0):,.2f}, remitos no facturados por "
                f"${totals.get('remitos_no_facturados', 0):,.2f} y pedidos pendientes por "
                f"${totals.get('pedidos_pendientes', 0):,.2f}. "
                f"El total consolidado fue de ${totals.get('total_consolidado', 0):,.2f}."
            )
            if previous_result and previous_result.totals:
                prev_total = previous_result.totals.get("total_consolidado", 0)
                curr_total = totals.get("total_consolidado", 0)
                delta = curr_total - prev_total
                answer += f" Frente al período anterior, la variación del total consolidado fue de ${delta:,.2f}."
            return answer

        if report.slug == "ventas_netas":
            totals = result.totals or {}
            value = totals.get("ventas_netas", 0)
            answer = (
                f"Las ventas netas entre {date_range.start_date} y {date_range.end_date} fueron de "
                f"${value:,.2f}. Registros devueltos: {len(result.data or [])}."
            )
            if previous_result and previous_result.totals:
                prev_value = previous_result.totals.get("ventas_netas", 0)
                delta = value - prev_value
                answer += f" La variación contra el período anterior fue de ${delta:,.2f}."
            return answer

        if report.slug == "pedidos-pendientes":
            totals = result.totals or {}
            total_amount = totals.get("total_subtotal_desc", 0)
            return (
                f"Encontré {len(result.data or [])} pedidos pendientes entre {date_range.start_date} y {date_range.end_date}, "
                f"por un total de ${total_amount:,.2f}."
            )

        if report.slug == "stock-existencias":
            row_count = len(result.data or [])
            sample = result.data[:3] if result.data else []
            sample_lines = []
            for item in sample:
                nombre = item.get("nombre") or item.get("id_manual") or "Artículo"
                disponible = item.get("disponible", 0)
                deposito = item.get("deposito_nombre", "Depósito")
                sample_lines.append(f"- {nombre}: {disponible} disponible en {deposito}")
            sample_block = "\n".join(sample_lines)
            return (
                f"Encontré {row_count} registros de stock/existencias con los filtros aplicados."
                + (f"\n{sample_block}" if sample_block else "")
            )

        if report.slug == "uninvoiced_remitos":
            total = result.totals.get("total_subtotal_desc", 0) if result.totals else 0
            return (
                f"Encontré {len(result.data or [])} remitos no facturados entre {date_range.start_date} y {date_range.end_date}, "
                f"por un total de ${total:,.2f}."
            )

        return (
            f"El reporte {report.name} devolvió {len(result.data or [])} registros."
            + (f" Notas: {' | '.join(result.notes)}" if result.notes else "")
        )

    def _try_llm_summary(self, *, message_text: str, report, result, schema: dict, interpreted, fallback_answer: str, previous_result=None):
        provider = self.agent.default_provider
        if not provider or not provider.is_configured or not self.selected_model.model_name:
            return fallback_answer, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "success"

        summary_payload = {
            "consulta_usuario": message_text,
            "reporte": {
                "slug": report.slug,
                "nombre": report.name,
                "schema": {
                    "metrics": [item.get("name") for item in schema.get("metrics", [])][:10],
                    "dimensions": [item.get("name") for item in schema.get("dimensions", [])][:10],
                },
            },
            "interpretacion": {
                "intent": interpreted.intent,
                "filters": interpreted.filters,
                "metadata": interpreted.metadata,
            },
            "resultado": {
                "totals": result.totals,
                "notes": result.notes,
                "sample_rows": (result.data or [])[:5],
                "row_count": len(result.data or []),
                "previous_period_totals": previous_result.totals if previous_result else {},
            },
        }
        try:
            llm_response = LlmGatewayService.generate_text(
                provider_config=provider,
                model_name=self.selected_model.model_name,
                system_prompt=(
                    "Sos el Asistente de Reportes de Synap. "
                    "Respondé siempre en español, con tono ejecutivo, claro y sobrio. "
                    "Usá solo la información suministrada. No inventes datos. "
                    "Incluí período y filtros relevantes si están disponibles."
                ),
                user_message=(
                    "Redactá una respuesta final breve y útil para el usuario a partir de este resultado validado:\n"
                    + json.dumps(summary_payload, ensure_ascii=False, default=str)
                ),
                memories=[],
                max_output_tokens=min(self.agent.max_output_tokens, 600),
                temperature=0.1,
            )
            text = (llm_response.get("text") or "").strip()
            if not text:
                raise LlmGatewayError("El proveedor no devolvió texto útil para el resumen.")
            return text, {
                "prompt_tokens": llm_response.get("prompt_tokens", 0),
                "completion_tokens": llm_response.get("completion_tokens", 0),
                "total_tokens": llm_response.get("total_tokens", 0),
            }, "success"
        except LlmGatewayError:
            return fallback_answer, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "partial"
