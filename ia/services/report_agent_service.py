from __future__ import annotations

import calendar
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from ia.services.date_range_service import DateRangeService
from ia.services.llm_gateway import LlmGatewayError, LlmGatewayService
from ia.services.mpr_kardex_tools import execute_kardex_articulo
from ia.services.report_intent_refinement_service import ReportIntentRefinementService
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

    _FACTURA_LETRAS_ORDEN = ("FA", "FB", "FC", "FE", "FM")
    _NOMBRES_MES_ES = (
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    )

    @staticmethod
    def _format_date_for_locale(iso_date: str, locale: str) -> str:
        """Formato de fecha acorde al idioma del usuario (sesión); por defecto día/mes/año."""
        if not iso_date:
            return ""
        d = date.fromisoformat(iso_date)
        loc = (locale or "es").lower().replace("_", "-")
        if loc.startswith("en") and loc not in ("en-gb", "en-au", "en-nz", "en-ie"):
            return d.strftime("%m/%d/%Y")
        return d.strftime("%d/%m/%Y")

    @classmethod
    def _titulo_mes_calendario(cls, ym: str, locale: str) -> str:
        y, m = map(int, ym.split("-"))
        loc = (locale or "es").lower().split("-")[0]
        if loc == "en":
            return f"{calendar.month_name[m]} {y}"
        return f"{cls._NOMBRES_MES_ES[m]} {y}"

    @classmethod
    def _lineas_punto_venta_desde_filas(cls, rows: list[dict]) -> list[str]:
        """Bloques «Punto de venta …» y letras FA…FM (solo las que tienen cantidad)."""
        if not rows:
            return []
        by_pv: dict = {}
        orden_pv: list = []
        for r in rows:
            id_pv = r.get("id_punto_venta")
            clave = id_pv if id_pv is not None else "__sin_pv__"
            if clave not in by_pv:
                by_pv[clave] = {"id_pv": id_pv, "nro": r.get("nro_punto_venta"), "tipos": {}}
                orden_pv.append(clave)
            tipo = (r.get("tipo_comprobante") or "").strip()
            cant = int(r.get("cantidad") or 0)
            if cant > 0 and tipo:
                by_pv[clave]["tipos"][tipo] = cant
        lines: list[str] = []
        for clave in orden_pv:
            data = by_pv[clave]
            nro = data.get("nro")
            id_pv = data.get("id_pv")
            if nro is not None:
                titulo_pv = f"Punto de venta {nro}"
            elif id_pv is None:
                titulo_pv = "Sin punto de venta"
            else:
                titulo_pv = f"Punto de venta {id_pv}"
            lines.append(f"{titulo_pv}:")
            for letra in cls._FACTURA_LETRAS_ORDEN:
                c = data["tipos"].get(letra)
                if c:
                    lines.append(f"{letra}: {c}")
            lines.append("")
        return lines

    @classmethod
    def _texto_facturas_por_punto_venta(
        cls,
        rows: list[dict],
        *,
        start_iso: str,
        end_iso: str,
        sucursal_label: str | None,
        locale: str,
        used_default_month: bool,
    ) -> str:
        if not rows:
            return "No hay facturas para los filtros que pediste."
        d1 = cls._format_date_for_locale(start_iso, locale)
        d2 = cls._format_date_for_locale(end_iso, locale)
        lines: list[str] = ["Facturas de ventas", "", f"Del {d1} al {d2}"]
        if sucursal_label and sucursal_label.strip():
            lines.append(f"Sucursal: {sucursal_label.strip()}")
        lines.append("")
        lines.extend(cls._lineas_punto_venta_desde_filas(rows))
        texto = "\n".join(lines).rstrip()
        if used_default_month:
            texto += "\n\nComo no indicaste el período, se usó el mes calendario en curso."
        return texto

    @classmethod
    def _texto_facturas_por_punto_venta_mensual(
        cls,
        rows: list[dict],
        *,
        sucursal_label: str | None,
        locale: str,
        used_default_month: bool,
    ) -> str:
        if not rows:
            return "No hay facturas para los filtros que pediste."
        by_mes: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            ym = r.get("anio_mes") or ""
            ym = str(ym).strip()[:7]
            if len(ym) == 7 and ym[4] == "-":
                by_mes[ym].append(r)
        orden = sorted(by_mes.keys())
        lines: list[str] = ["Facturas de ventas", ""]
        if sucursal_label and sucursal_label.strip():
            lines.append(f"Sucursal: {sucursal_label.strip()}")
            lines.append("")
        for ym in orden:
            y, mo = map(int, ym.split("-"))
            ultimo = calendar.monthrange(y, mo)[1]
            d_ini = f"{y:04d}-{mo:02d}-01"
            d_fin = f"{y:04d}-{mo:02d}-{ultimo:02d}"
            ds = cls._format_date_for_locale(d_ini, locale)
            de = cls._format_date_for_locale(d_fin, locale)
            lines.append(cls._titulo_mes_calendario(ym, locale))
            lines.append(f"Del {ds} al {de}")
            lines.append("")
            lines.extend(cls._lineas_punto_venta_desde_filas(by_mes[ym]))
        texto = "\n".join(lines).rstrip()
        if used_default_month:
            texto += "\n\nComo no indicaste el período, se usó el mes calendario en curso."
        return texto

    @classmethod
    def _texto_facturas_mensual_por_tipo(
        cls,
        rows: list[dict],
        *,
        sucursal_label: str | None,
        locale: str,
        used_default_month: bool,
    ) -> str:
        """Mes a mes con letras FA…FM, sin punto de venta."""
        if not rows:
            return "No hay facturas para los filtros que pediste."
        by_mes: dict[str, dict[str, int]] = defaultdict(dict)
        for r in rows:
            ym = str(r.get("anio_mes") or "").strip()[:7]
            if len(ym) != 7 or ym[4] != "-":
                continue
            tipo = (r.get("tipo_comprobante") or "").strip()
            if not tipo:
                continue
            by_mes[ym][tipo] = int(r.get("cantidad") or 0)
        orden = sorted(by_mes.keys())
        lines: list[str] = ["Facturas de ventas", ""]
        if sucursal_label and sucursal_label.strip():
            lines.append(f"Sucursal: {sucursal_label.strip()}")
            lines.append("")
        for ym in orden:
            y, mo = map(int, ym.split("-"))
            ultimo = calendar.monthrange(y, mo)[1]
            d_ini = f"{y:04d}-{mo:02d}-01"
            d_fin = f"{y:04d}-{mo:02d}-{ultimo:02d}"
            ds = cls._format_date_for_locale(d_ini, locale)
            de = cls._format_date_for_locale(d_fin, locale)
            lines.append(cls._titulo_mes_calendario(ym, locale))
            lines.append(f"Del {ds} al {de}")
            lines.append("")
            tipos_mes = by_mes[ym]
            for letra in cls._FACTURA_LETRAS_ORDEN:
                c = tipos_mes.get(letra)
                if c:
                    lines.append(f"{letra}: {c}")
            lines.append("")
        texto = "\n".join(lines).rstrip()
        if used_default_month:
            texto += "\n\nComo no indicaste el período, se usó el mes calendario en curso."
        return texto

    @staticmethod
    def _rollup_ventas_netas_monthly(rows: list) -> list[dict]:
        """Consolida filas del reporte (mes × sucursal × PV) en un total por mes y ordena por ventas_netas descendente."""
        by_month: dict[str, dict] = {}
        for r in rows or []:
            m = r.get("mes")
            if not m:
                continue
            if m not in by_month:
                by_month[m] = {
                    "mes": m,
                    "mes_formato": r.get("mes_formato") or m,
                    "ventas_netas": 0.0,
                    "ventas_brutas": 0.0,
                    "notas_credito": 0.0,
                }
            entry = by_month[m]
            entry["ventas_netas"] += float(r.get("ventas_netas", 0) or 0)
            entry["ventas_brutas"] += float(r.get("ventas_brutas", 0) or 0)
            entry["notas_credito"] += float(r.get("notas_credito", 0) or 0)
        out = list(by_month.values())
        out.sort(key=lambda x: x["ventas_netas"], reverse=True)
        return out

    def __init__(self, *, agent, policy_context, selected_model):
        self.agent = agent
        self.policy_context = policy_context
        self.selected_model = selected_model

    @staticmethod
    def _merge_report_token_usage(*parts: dict | None) -> dict:
        out = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for p in parts:
            if not p:
                continue
            out["prompt_tokens"] += int(p.get("prompt_tokens") or 0)
            out["completion_tokens"] += int(p.get("completion_tokens") or 0)
            out["total_tokens"] += int(p.get("total_tokens") or 0)
        return out

    def handle_query(self, message_text: str, conversation_snippet: str | None = None) -> ReportAgentResult:
        interpreted = ReportToolsService.interpret_query(
            message_text,
            self.policy_context,
            conversation_snippet=conversation_snippet,
        )
        refinement_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        if not interpreted.metadata.get("general_chat"):
            hints, refinement_usage = ReportIntentRefinementService.try_refine(
                message_text=message_text,
                conversation_snippet=conversation_snippet,
                agent=self.agent,
                interpreted=interpreted,
            )
            if hints:
                interpreted = ReportToolsService.apply_llm_intent_hints(interpreted, hints)
        if interpreted.metadata.get("general_chat"):
            return self._handle_general_chat(message_text)
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
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="partial",
                used_report_slug=interpreted.report_slug,
            )

        requires_period = interpreted.report_slug in {"sales_summary", "ventas_netas", "uninvoiced_remitos", "pedidos-pendientes"}
        if interpreted.metadata.get("invoice_count_fa_fm") or interpreted.metadata.get("ventas_por_tipo_comprobante"):
            requires_period = False

        combined_for_dates = "\n".join(x for x in [conversation_snippet or "", message_text] if x).strip()
        # Mismo criterio que interpret_query (canon): el período puede venir solo en turnos anteriores («Incluye PUIG» tras un informe con fechas).
        date_range = DateRangeService.resolve_from_text(combined_for_dates, require_period=requires_period)
        used_default_month_for_invoices = False
        used_default_month_for_tipo = False
        if interpreted.metadata.get("invoice_count_fa_fm"):
            if date_range.requires_clarification or not date_range.start_date or not date_range.end_date:
                dr_full = DateRangeService.resolve_from_text(combined_for_dates, require_period=False)
                if dr_full.start_date and dr_full.end_date and not dr_full.requires_clarification:
                    date_range = dr_full
                else:
                    date_range = DateRangeService.resolve_from_text("ventas este mes", require_period=False)
                    used_default_month_for_invoices = True
        elif interpreted.metadata.get("ventas_por_tipo_comprobante"):
            if date_range.requires_clarification or not date_range.start_date or not date_range.end_date:
                dr_full = DateRangeService.resolve_from_text(combined_for_dates, require_period=False)
                if dr_full.start_date and dr_full.end_date and not dr_full.requires_clarification:
                    date_range = dr_full
                else:
                    date_range = DateRangeService.resolve_from_text("este mes", require_period=False)
                    used_default_month_for_tipo = True
        elif date_range.requires_clarification or not date_range.start_date or not date_range.end_date:
            dr_relax = DateRangeService.resolve_from_text(combined_for_dates, require_period=False)
            if dr_relax.start_date and dr_relax.end_date and not dr_relax.requires_clarification:
                date_range = dr_relax
            elif interpreted.report_slug == "comprobantes-rutas" or (
                interpreted.report_slug and interpreted.report_slug.startswith("mpr-")
            ):
                # Listado logístico y reportes MPR (incl. kardex artículo): período opcional.
                pass
            else:
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
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=interpreted.report_slug,
                )

        if interpreted.report_slug == "mpr-kardex-articulo" or interpreted.metadata.get(
            "mpr_kardex_articulo"
        ):
            exec_filters = dict(interpreted.filters or {})
            if interpreted.metadata.get("deposito_hint_semi"):
                exec_filters.setdefault("deposito_hint_semi", True)
            if date_range.start_date and date_range.end_date:
                exec_filters["fecha_desde"] = date_range.start_date
                exec_filters["fecha_hasta"] = date_range.end_date
            kardex_result = execute_kardex_articulo(self.policy_context, exec_filters)
            if kardex_result.get("requires_clarification"):
                return ReportAgentResult(
                    answer=kardex_result.get("clarification_question")
                    or "Necesito una aclaración para consultar el kardex.",
                    response_payload={
                        "phase": "clarification",
                        "query_spec": {
                            "intent": interpreted.intent,
                            "report_slug": interpreted.report_slug,
                            "filters": interpreted.filters,
                            "metadata": interpreted.metadata,
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug="mpr-kardex-articulo",
                )
            return ReportAgentResult(
                answer=kardex_result.get("answer") or "",
                response_payload={
                    "phase": "mpr_kardex_articulo",
                    "report_slug": "mpr-kardex-articulo",
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
                        "kardex_payload": kardex_result.get("payload"),
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status=kardex_result.get("status") or "success",
                used_report_slug="mpr-kardex-articulo",
            )

        actual_report_slug = ReportToolsService.resolve_actual_report_slug(
            interpreted.report_slug,
            self.policy_context,
        )
        if not actual_report_slug:
            return ReportAgentResult(
                answer="No encontré un reporte operativo disponible para esa consulta en esta instalación. Puedo ayudarte si consultamos ventas, pedidos, remitos o stock con un reporte habilitado.",
                response_payload={
                    "phase": "missing_report_definition",
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": interpreted.metadata,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="partial",
                used_report_slug=interpreted.report_slug,
            )

        report = ReportToolsService.get_report_definition(actual_report_slug)
        ReportToolsService.validate_report_permissions(report, self.policy_context.user)
        schema = ReportToolsService.get_report_schema(report)

        if interpreted.metadata.get("invoice_count_fa_fm_mensual") and report.slug in ("ventas_netas", "ventas-netas"):
            suc_raw = interpreted.filters.get("sucursales") or []
            suc_ids = [int(x) for x in suc_raw] if suc_raw else None
            rows_m, err = ReportToolsService.count_facturas_emitidas_fa_fm_por_mes_y_tipo(
                base_empresa=self.policy_context.base_empresa or "",
                fecha_inicio=date_range.start_date or "",
                fecha_fin=date_range.end_date or "",
                sucursal_ids=suc_ids,
            )
            if err or rows_m is None:
                return ReportAgentResult(
                    answer=f"No pude obtener el conteo de facturas por mes. {err or 'Error desconocido.'}",
                    response_payload={
                        "phase": "invoice_fa_fm_mensual_error",
                        "report_slug": report.slug,
                        "report_name": report.name,
                        "query_spec": {
                            "intent": interpreted.intent,
                            "report_slug": interpreted.report_slug,
                            "filters": interpreted.filters,
                            "metadata": {
                                **interpreted.metadata,
                                "used_default_month": used_default_month_for_invoices,
                            },
                            "date_range": {
                                "type": date_range.range_type,
                                "start_date": date_range.start_date,
                                "end_date": date_range.end_date,
                            },
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=report.slug,
                )
            suc_label = interpreted.metadata.get("sucursal_match")
            answer = self._texto_facturas_mensual_por_tipo(
                rows_m or [],
                sucursal_label=suc_label,
                locale=self.policy_context.locale or "es",
                used_default_month=used_default_month_for_invoices,
            )
            return ReportAgentResult(
                answer=answer,
                response_payload={
                    "phase": "invoice_count_fa_fm_mensual",
                    "report_slug": report.slug,
                    "report_name": report.name,
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": {
                            **interpreted.metadata,
                            "used_default_month": used_default_month_for_invoices,
                        },
                        "date_range": {
                            "type": date_range.range_type,
                            "start_date": date_range.start_date,
                            "end_date": date_range.end_date,
                        },
                        "invoice_count_fa_fm_mensual": rows_m,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="success",
                used_report_slug=report.slug,
            )

        if interpreted.metadata.get("invoice_count_by_punto_venta_mensual") and report.slug in (
            "ventas_netas",
            "ventas-netas",
        ):
            suc_raw = interpreted.filters.get("sucursales") or []
            suc_ids = [int(x) for x in suc_raw] if suc_raw else None
            rows_pv, err = ReportToolsService.count_facturas_emitidas_fa_fm_by_punto_venta_mensual(
                base_empresa=self.policy_context.base_empresa or "",
                fecha_inicio=date_range.start_date or "",
                fecha_fin=date_range.end_date or "",
                sucursal_ids=suc_ids,
            )
            if err or rows_pv is None:
                return ReportAgentResult(
                    answer=f"No pude obtener el conteo de facturas por punto de venta y mes. {err or 'Error desconocido.'}",
                    response_payload={
                        "phase": "invoice_count_by_pv_mensual_error",
                        "report_slug": report.slug,
                        "report_name": report.name,
                        "query_spec": {
                            "intent": interpreted.intent,
                            "report_slug": interpreted.report_slug,
                            "filters": interpreted.filters,
                            "metadata": {
                                **interpreted.metadata,
                                "used_default_month": used_default_month_for_invoices,
                            },
                            "date_range": {
                                "type": date_range.range_type,
                                "start_date": date_range.start_date,
                                "end_date": date_range.end_date,
                            },
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=report.slug,
                )
            suc_label = interpreted.metadata.get("sucursal_match")
            answer = self._texto_facturas_por_punto_venta_mensual(
                rows_pv or [],
                sucursal_label=suc_label,
                locale=self.policy_context.locale or "es",
                used_default_month=used_default_month_for_invoices,
            )
            return ReportAgentResult(
                answer=answer,
                response_payload={
                    "phase": "invoice_count_by_punto_venta_mensual",
                    "report_slug": report.slug,
                    "report_name": report.name,
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": {
                            **interpreted.metadata,
                            "used_default_month": used_default_month_for_invoices,
                        },
                        "date_range": {
                            "type": date_range.range_type,
                            "start_date": date_range.start_date,
                            "end_date": date_range.end_date,
                        },
                        "invoice_count_by_punto_venta_mensual": rows_pv,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="success",
                used_report_slug=report.slug,
            )

        if interpreted.metadata.get("invoice_count_by_punto_venta") and report.slug in ("ventas_netas", "ventas-netas"):
            suc_raw = interpreted.filters.get("sucursales") or []
            suc_ids = [int(x) for x in suc_raw] if suc_raw else None
            rows_pv, err = ReportToolsService.count_facturas_emitidas_fa_fm_by_punto_venta(
                base_empresa=self.policy_context.base_empresa or "",
                fecha_inicio=date_range.start_date or "",
                fecha_fin=date_range.end_date or "",
                sucursal_ids=suc_ids,
            )
            if err or rows_pv is None:
                return ReportAgentResult(
                    answer=f"No pude obtener el conteo de facturas por punto de venta. {err or 'Error desconocido.'}",
                    response_payload={
                        "phase": "invoice_count_by_pv_error",
                        "report_slug": report.slug,
                        "report_name": report.name,
                        "query_spec": {
                            "intent": interpreted.intent,
                            "report_slug": interpreted.report_slug,
                            "filters": interpreted.filters,
                            "metadata": {
                                **interpreted.metadata,
                                "used_default_month": used_default_month_for_invoices,
                            },
                            "date_range": {
                                "type": date_range.range_type,
                                "start_date": date_range.start_date,
                                "end_date": date_range.end_date,
                            },
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=report.slug,
                )
            suc_label = interpreted.metadata.get("sucursal_match")
            answer = self._texto_facturas_por_punto_venta(
                rows_pv or [],
                start_iso=date_range.start_date or "",
                end_iso=date_range.end_date or "",
                sucursal_label=suc_label,
                locale=self.policy_context.locale or "es",
                used_default_month=used_default_month_for_invoices,
            )
            return ReportAgentResult(
                answer=answer,
                response_payload={
                    "phase": "invoice_count_by_punto_venta",
                    "report_slug": report.slug,
                    "report_name": report.name,
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": {
                            **interpreted.metadata,
                            "used_default_month": used_default_month_for_invoices,
                        },
                        "date_range": {
                            "type": date_range.range_type,
                            "start_date": date_range.start_date,
                            "end_date": date_range.end_date,
                        },
                        "invoice_count_by_punto_venta": rows_pv,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="success",
                used_report_slug=report.slug,
            )

        if interpreted.metadata.get("invoice_count_fa_fm") and report.slug in ("ventas_netas", "ventas-netas"):
            suc_raw = interpreted.filters.get("sucursales") or []
            suc_ids = [int(x) for x in suc_raw] if suc_raw else None
            count, err = ReportToolsService.count_facturas_emitidas_fa_fm(
                base_empresa=self.policy_context.base_empresa or "",
                fecha_inicio=date_range.start_date or "",
                fecha_fin=date_range.end_date or "",
                sucursal_ids=suc_ids,
            )
            if err or count is None:
                return ReportAgentResult(
                    answer=f"No pude obtener el conteo de facturas. {err or 'Error desconocido.'}",
                    response_payload={
                        "phase": "invoice_count_error",
                        "report_slug": report.slug,
                        "report_name": report.name,
                        "query_spec": {
                            "intent": interpreted.intent,
                            "report_slug": interpreted.report_slug,
                            "filters": interpreted.filters,
                            "metadata": {
                                **interpreted.metadata,
                                "used_default_month": used_default_month_for_invoices,
                            },
                            "date_range": {
                                "type": date_range.range_type,
                                "start_date": date_range.start_date,
                                "end_date": date_range.end_date,
                            },
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=report.slug,
                )
            suc_label = interpreted.metadata.get("sucursal_match") or "las sucursales del filtro"
            d1 = self._format_date_for_locale(date_range.start_date or "", self.policy_context.locale or "es")
            d2 = self._format_date_for_locale(date_range.end_date or "", self.policy_context.locale or "es")
            period_note = (
                " Como no indicaste el período, se usó el mes calendario en curso."
                if used_default_month_for_invoices
                else ""
            )
            answer = (
                f"Del {d1} al {d2}, en {suc_label}, se registraron {count} facturas de venta.{period_note}"
            )
            return ReportAgentResult(
                answer=answer,
                response_payload={
                    "phase": "invoice_count",
                    "report_slug": report.slug,
                    "report_name": report.name,
                    "query_spec": {
                        "intent": interpreted.intent,
                        "report_slug": interpreted.report_slug,
                        "filters": interpreted.filters,
                        "metadata": {
                            **interpreted.metadata,
                            "used_default_month": used_default_month_for_invoices,
                        },
                        "date_range": {
                            "type": date_range.range_type,
                            "start_date": date_range.start_date,
                            "end_date": date_range.end_date,
                        },
                        "invoice_count": count,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="success",
                used_report_slug=report.slug,
            )

        if interpreted.metadata.get("ventas_por_tipo_comprobante") and report.slug in ("ventas_netas", "ventas-netas"):
            suc_raw = interpreted.filters.get("sucursales") or []
            suc_ids = [int(x) for x in suc_raw] if suc_raw else None
            rows, err = ReportToolsService.aggregate_movimientos_por_tipo_comprobante(
                base_empresa=self.policy_context.base_empresa or "",
                fecha_inicio=date_range.start_date or "",
                fecha_fin=date_range.end_date or "",
                sucursal_ids=suc_ids,
            )
            if err or rows is None:
                return ReportAgentResult(
                    answer=f"No pude obtener el desglose por tipo de comprobante. {err or ''}".strip(),
                    response_payload={
                        "phase": "ventas_por_tipo_error",
                        "report_slug": report.slug,
                        "report_name": report.name,
                        "query_spec": {
                            "intent": interpreted.intent,
                            "filters": interpreted.filters,
                            "metadata": {
                                **interpreted.metadata,
                                "used_default_month": used_default_month_for_tipo,
                            },
                            "date_range": {
                                "type": date_range.range_type,
                                "start_date": date_range.start_date,
                                "end_date": date_range.end_date,
                            },
                        },
                    },
                    token_usage=self._merge_report_token_usage(refinement_usage),
                    execution_status="partial",
                    used_report_slug=report.slug,
                )
            suc_label = interpreted.metadata.get("sucursal_match") or "todas las sucursales del filtro"
            period_note = (
                "Como no indicaste el período, se usó el mes calendario en curso."
                if used_default_month_for_tipo
                else ""
            )
            d1 = self._format_date_for_locale(date_range.start_date or "", self.policy_context.locale or "es")
            d2 = self._format_date_for_locale(date_range.end_date or "", self.policy_context.locale or "es")
            lines = [
                f"Facturas de venta (FA a FM) entre el {d1} y el {d2} ({suc_label}), por tipo:",
                period_note,
            ]
            lines = [x for x in lines if x]
            n = 1
            for row in rows or []:
                tipo = row.get("tipo_comprobante") or "—"
                cant = int(row.get("cantidad", 0) or 0)
                if cant <= 0:
                    continue
                tot = float(row.get("total_subtotal", 0) or 0)
                lines.append(f"{n}. {tipo}: {cant} comprobantes, subtotal ${tot:,.2f}")
                n += 1
            answer = "\n".join(lines)
            return ReportAgentResult(
                answer=answer,
                response_payload={
                    "phase": "ventas_por_tipo_comprobante",
                    "report_slug": report.slug,
                    "report_name": report.name,
                    "query_spec": {
                        "intent": interpreted.intent,
                        "filters": interpreted.filters,
                        "metadata": {
                            **interpreted.metadata,
                            "used_default_month": used_default_month_for_tipo,
                        },
                        "date_range": {
                            "type": date_range.range_type,
                            "start_date": date_range.start_date,
                            "end_date": date_range.end_date,
                        },
                        "rows": rows,
                    },
                },
                token_usage=self._merge_report_token_usage(refinement_usage),
                execution_status="success",
                used_report_slug=report.slug,
            )

        query_limit = 200
        if interpreted.metadata.get("ventas_netas_monthly_company_totals") and report.slug in (
            "ventas_netas",
            "ventas-netas",
        ):
            query_limit = 8000

        payload = ReportToolsService.build_payload(
            report_slug=report.slug,
            base_filters=interpreted.filters,
            policy_context=self.policy_context,
            date_range=date_range,
            limit=query_limit,
        )
        result = ReportToolsService.run_report_query(report, payload, self.policy_context.user)
        previous_payload = None
        previous_result = None
        if (
            interpreted.metadata.get("compare_previous_period")
            and not interpreted.metadata.get("ventas_netas_monthly_company_totals")
            and not interpreted.metadata.get("ventas_por_tipo_comprobante")
            and date_range.start_date
            and date_range.end_date
        ):
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

        monthly_rollup = None
        if interpreted.metadata.get("ventas_netas_monthly_company_totals") and report.slug in (
            "ventas_netas",
            "ventas-netas",
        ):
            monthly_rollup = self._rollup_ventas_netas_monthly(result.data or [])

        deterministic_answer = self._build_deterministic_answer(
            message_text=message_text,
            report=report,
            result=result,
            interpreted=interpreted,
            date_range=date_range,
            previous_result=previous_result,
            previous_payload=previous_payload,
            monthly_rollup=monthly_rollup,
        )
        llm_answer, token_usage, status = self._try_llm_summary(
            message_text=message_text,
            report=report,
            result=result,
            schema=schema,
            interpreted=interpreted,
            fallback_answer=deterministic_answer,
            previous_result=previous_result,
            summary_rows=monthly_rollup,
        )

        effective_row_count = len(monthly_rollup) if monthly_rollup is not None else len(result.data or [])
        effective_totals = result.totals or {}
        if monthly_rollup is not None:
            effective_totals = {
                "ventas_netas": sum(float(r.get("ventas_netas", 0) or 0) for r in monthly_rollup),
                "ventas_brutas": sum(float(r.get("ventas_brutas", 0) or 0) for r in monthly_rollup),
                "notas_credito": sum(float(r.get("notas_credito", 0) or 0) for r in monthly_rollup),
            }

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
                "row_count": effective_row_count,
                "notes": result.notes,
                "totals": effective_totals,
                "previous_period_totals": previous_result.totals if previous_result else {},
            },
            token_usage=self._merge_report_token_usage(refinement_usage, token_usage),
            execution_status=status,
            used_report_slug=report.slug,
        )

    def _handle_general_chat(self, message_text: str) -> ReportAgentResult:
        fallback = (
            "Soy el Asistente de Reportes de Synap. Puedo ayudarte con consultas de ventas, pedidos, remitos y stock. "
            "Por ejemplo: '¿Cuánto vendimos este mes?' o '¿Qué pedidos pendientes tenemos hoy?'."
        )
        provider = self.agent.default_provider
        if not provider or not provider.is_configured or not self.selected_model.model_name:
            return ReportAgentResult(
                answer=fallback,
                response_payload={"phase": "general_chat_fallback"},
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                execution_status="success",
            )
        try:
            llm_response = LlmGatewayService.generate_text(
                provider_config=provider,
                model_name=self.selected_model.model_name,
                system_prompt=(
                    "Sos el Asistente de Reportes de Synap. Respondé siempre en español, "
                    "con tono claro, cordial y profesional. Si el usuario saluda o pregunta de forma general, "
                    "presentate brevemente y explicá en una oración qué tipo de consultas de negocio podés resolver."
                ),
                user_message=message_text,
                memories=[],
                max_output_tokens=min(self.agent.max_output_tokens, 300),
                temperature=0.2,
            )
            text = (llm_response.get("text") or "").strip() or fallback
            return ReportAgentResult(
                answer=text,
                response_payload={"phase": "general_chat_runtime"},
                token_usage={
                    "prompt_tokens": llm_response.get("prompt_tokens", 0),
                    "completion_tokens": llm_response.get("completion_tokens", 0),
                    "total_tokens": llm_response.get("total_tokens", 0),
                },
                execution_status="success",
            )
        except LlmGatewayError:
            return ReportAgentResult(
                answer=fallback,
                response_payload={"phase": "general_chat_fallback"},
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                execution_status="partial",
            )

    def _build_deterministic_answer(
        self,
        *,
        message_text: str,
        report,
        result,
        interpreted,
        date_range,
        previous_result=None,
        previous_payload=None,
        monthly_rollup: list | None = None,
    ) -> str:
        if result.notes and not result.data and not result.totals:
            return "\n".join(result.notes)

        loc = self.policy_context.locale or "es"

        if report.slug == "sales_summary":
            totals = result.totals or {}
            d_per_a = self._format_date_for_locale(date_range.start_date or "", loc)
            d_per_b = self._format_date_for_locale(date_range.end_date or "", loc)
            answer = (
                f"En el período {d_per_a} al {d_per_b}, el resumen de ventas registró "
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

        if report.slug in ("ventas_netas", "ventas-netas"):
            if monthly_rollup is not None:
                d_ini = self._format_date_for_locale(date_range.start_date or "", loc)
                d_fin = self._format_date_for_locale(date_range.end_date or "", loc)
                if not monthly_rollup:
                    return (
                        f"No encontré movimientos agregables por mes entre {d_ini} y {d_fin}. "
                        "Si el período o los filtros de sucursal son correctos, puede no haber comprobantes en ese rango."
                    )
                sucursal_label = (interpreted.metadata or {}).get("sucursal_match")
                if sucursal_label and str(sucursal_label).strip():
                    alcance = f"(sucursal: {str(sucursal_label).strip()})"
                else:
                    alcance = "(total empresa)"
                header = f"Ventas netas por mes calendario {alcance}, entre {d_ini} y {d_fin}:"
                lines: list[str] = [header, ""]
                for i, row in enumerate(monthly_rollup, 1):
                    label = row.get("mes_formato") or row.get("mes") or "—"
                    monto = float(row.get("ventas_netas", 0) or 0)
                    lines.append(f"{i}. {label}: ${monto:,.2f}")
                total = sum(float(r.get("ventas_netas", 0) or 0) for r in monthly_rollup)
                lines.append("")
                lines.append(f"Total: ${total:,.2f}.")
                return "\n".join(lines)

            totals = result.totals or {}
            value = totals.get("ventas_netas", 0)
            d_ini = self._format_date_for_locale(date_range.start_date or "", loc)
            d_fin = self._format_date_for_locale(date_range.end_date or "", loc)
            answer = (
                f"Las ventas netas entre {d_ini} y {d_fin} fueron de "
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
            d1 = self._format_date_for_locale(date_range.start_date or "", loc)
            d2 = self._format_date_for_locale(date_range.end_date or "", loc)
            return (
                f"Encontré {len(result.data or [])} pedidos pendientes entre {d1} y {d2}, "
                f"por un total de ${total_amount:,.2f}."
            )

        if report.slug == "mpr-pedidos-estado":
            rows = result.data or []
            pendiente_n = 0
            otros: list[str] = []
            for r in rows:
                est = (r.get("estado") or "").strip()
                cant = int(r.get("cantidad") or 0)
                if est == "Pendiente":
                    pendiente_n = cant
                else:
                    otros.append(f"{est}: {cant}")
            partes = [
                f"En MPR hay {pendiente_n} pedidos en estado Pendiente "
                "(conteo por estado_pedido_opt; no incluye pedidos PED en depósito)."
            ]
            if otros:
                partes.append("Otros estados: " + ", ".join(otros) + ".")
            return " ".join(partes)

        if report.slug in ("comprobantes-rutas", "mayoristapp-lista-comprobantes-rutas"):
            n = len(result.data or [])
            solo_pend = bool((interpreted.filters or {}).get("logistica_estado_entrega") == "No")
            alcance = "solo remitos aún no entregados" if solo_pend else "según filtros del listado"
            if date_range.start_date and date_range.end_date:
                d1 = self._format_date_for_locale(date_range.start_date, loc)
                d2 = self._format_date_for_locale(date_range.end_date, loc)
                periodo = f"entre {d1} y {d2}"
            else:
                periodo = "sin acotar por fechas en el filtro"
            return (
                f"Logística ({alcance}), {periodo}: {n} comprobantes en ruta con los criterios aplicados."
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
            d1 = self._format_date_for_locale(date_range.start_date or "", loc)
            d2 = self._format_date_for_locale(date_range.end_date or "", loc)
            return (
                f"Encontré {len(result.data or [])} remitos no facturados entre {d1} y {d2}, "
                f"por un total de ${total:,.2f}."
            )

        return (
            f"El reporte {report.name} devolvió {len(result.data or [])} registros."
            + (f" Notas: {' | '.join(result.notes)}" if result.notes else "")
        )

    def _try_llm_summary(
        self,
        *,
        message_text: str,
        report,
        result,
        schema: dict,
        interpreted,
        fallback_answer: str,
        previous_result=None,
        summary_rows: list | None = None,
    ):
        provider = self.agent.default_provider
        if not provider or not provider.is_configured or not self.selected_model.model_name:
            return fallback_answer, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "success"

        rows_for_summary = summary_rows if summary_rows is not None else (result.data or [])
        totals_for_summary = result.totals or {}
        if summary_rows is not None:
            totals_for_summary = {
                "ventas_netas": sum(float(r.get("ventas_netas", 0) or 0) for r in summary_rows),
                "ventas_brutas": sum(float(r.get("ventas_brutas", 0) or 0) for r in summary_rows),
                "notas_credito": sum(float(r.get("notas_credito", 0) or 0) for r in summary_rows),
            }

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
                "totals": totals_for_summary,
                "notes": result.notes,
                "sample_rows": rows_for_summary[:40],
                "row_count": len(rows_for_summary),
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
                    "Las fechas en español deben mostrarse como dd/MM/yyyy (no uses ISO yyyy-MM-dd). "
                    "Separá con una línea en blanco el encabezado contextual, la lista numerada y el total final cuando haya listado. "
                    "Incluí período y filtros relevantes si están disponibles. "
                    "Si sample_rows es un ranking mensual por monto, respetá ese orden (mayor a menor) y no lo reordenes cronológicamente."
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
