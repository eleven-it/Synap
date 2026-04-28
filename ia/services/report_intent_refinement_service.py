from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ia.services.llm_gateway import LlmGatewayError, LlmGatewayService
from ia.services.model_selection_service import ModelSelectionService

if TYPE_CHECKING:
    from ia.services.report_tools import InterpretedReportQuery

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class ReportIntentHints:
    """Salida acotada del refinamiento LLM antes de ejecutar SQL determinista."""

    metrica: str  # importes_ventas | cantidad_facturas | desconocido
    desglose_mensual: bool
    desglose_por_punto_venta: bool
    confianza: float


class ReportIntentRefinementService:
    """Refina la intención (métrica, desglose) con un modelo rápido; si falla, no altera el flujo."""

    _SYSTEM_PROMPT = """Sos un clasificador de intención para consultas en español sobre ventas y facturación en Synap.
Respondé con un único objeto JSON (sin texto adicional) con estas claves:
- "metrica": "importes_ventas" si el usuario pide montos en pesos, totales de venta, importes, facturación en dinero, "cuánto vendimos" en plata.
- "metrica": "cantidad_facturas" si pide cuántas facturas/comprobantes (conteo FA–FM), número de comprobantes, no el monto.
- "metrica": "desconocido" si la consulta no es sobre ese tipo de ventas/facturas o no estás seguro.
- "desglose_mensual": true si piden desglose mes a mes, mensual, por mes, evolución por mes, "comprobantes x mes" en sentido de serie temporal por mes.
- "desglose_por_punto_venta": true si piden desglose por punto de venta, PV, caja o terminal.
- "confianza": número entre 0 y 1 (tu certeza).

Ejemplos: "total de ventas por mes en pesos" → importes_ventas, desglose_mensual true. "cuántas facturas por punto de venta" → cantidad_facturas, desglose_por_punto_venta true."""

    @classmethod
    def _empty_usage(cls) -> dict[str, int]:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @classmethod
    def _parse_hints(cls, raw: str) -> ReportIntentHints | None:
        text = (raw or "").strip()
        if not text:
            return None
        candidate = text
        m = _JSON_BLOCK.search(text)
        if m:
            candidate = m.group(1).strip()
        try:
            data: dict[str, Any] = json.loads(candidate)
        except json.JSONDecodeError:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(candidate[start : end + 1])
                except json.JSONDecodeError:
                    return None
            else:
                return None

        metrica = str(data.get("metrica") or "desconocido").strip().lower()
        if metrica not in ("importes_ventas", "cantidad_facturas", "desconocido"):
            metrica = "desconocido"

        conf = data.get("confianza")
        try:
            confianza = float(conf)
        except (TypeError, ValueError):
            confianza = 0.0
        confianza = max(0.0, min(1.0, confianza))

        return ReportIntentHints(
            metrica=metrica,
            desglose_mensual=bool(data.get("desglose_mensual")),
            desglose_por_punto_venta=bool(data.get("desglose_por_punto_venta")),
            confianza=confianza,
        )

    @classmethod
    def _intent_refinement_enabled(cls, agent) -> bool:
        cfg = getattr(agent, "config", None) or {}
        if isinstance(cfg, dict) and cfg.get("report_intent_refinement") is False:
            return False
        provider = getattr(agent, "default_provider", None)
        if not provider or not getattr(provider, "is_active", True):
            return False
        if not getattr(provider, "get_api_key", lambda: None)():
            return False
        return True

    @classmethod
    def try_refine(
        cls,
        *,
        message_text: str,
        conversation_snippet: str | None,
        agent,
        interpreted: InterpretedReportQuery,
    ) -> tuple[ReportIntentHints | None, dict[str, int]]:
        """
        Llama al modelo rápido del agente. Si falla el parseo o el proveedor, devuelve (None, ceros).
        """
        zero = cls._empty_usage()
        if not cls._intent_refinement_enabled(agent):
            return None, zero

        md = interpreted.metadata or {}
        keys_preview = sorted(k for k in md.keys() if not str(k).startswith("_"))[:12]
        user_blob = (
            f"Heurística actual (puede estar mal): intent={interpreted.intent!r}, "
            f"report_slug={interpreted.report_slug!r}, metadata_keys={keys_preview}\n\n"
            f"Consulta del usuario:\n{(message_text or '').strip()}\n\n"
            f"Contexto reciente:\n{(conversation_snippet or '').strip() or '(ninguno)'}\n"
        )

        selected = ModelSelectionService.select(agent, task_type="fast")
        provider = agent.default_provider
        try:
            resp = LlmGatewayService.generate_text(
                provider_config=provider,
                model_name=selected.model_name,
                system_prompt=cls._SYSTEM_PROMPT,
                user_message=user_blob,
                memories=[],
                max_output_tokens=320,
                temperature=0.0,
            )
        except LlmGatewayError as exc:
            logger.debug("Refinamiento de intención omitido: %s", exc)
            return None, zero
        except Exception as exc:  # noqa: BLE001
            logger.warning("Refinamiento de intención falló: %s", exc)
            return None, zero

        hints = cls._parse_hints(resp.get("text") or "")
        usage = cls._empty_usage()
        usage["prompt_tokens"] = int(resp.get("prompt_tokens") or 0)
        usage["completion_tokens"] = int(resp.get("completion_tokens") or 0)
        usage["total_tokens"] = int(resp.get("total_tokens") or 0)

        if not hints or hints.metrica == "desconocido" or hints.confianza <= 0.0:
            return None, usage

        return hints, usage
