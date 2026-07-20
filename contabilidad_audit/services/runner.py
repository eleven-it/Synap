"""Orquestación de corridas de auditoría contable (solo lectura)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from core.mysql_pool import get_mysql_pool

from contabilidad_audit.models import CorridaAuditoria
from contabilidad_audit.services.politicas import calcular_config_hash, resolver_politica
from contabilidad_audit.services.registry import CHECKS, CHECK_IDS_DEFAULT
from contabilidad_audit.services.resultados import AuditResult, CorridaContexto

logger = logging.getLogger(__name__)


def _audit_result_a_dict(result: AuditResult) -> dict[str, Any]:
    return {
        "check_id": result.check_id,
        "titulo": result.titulo,
        "severidad": result.severidad,
        "ok": result.ok,
        "total_evaluado": result.total_evaluado,
        "total_diferencias": result.total_diferencias,
        "error": result.error,
        "resumen": result.resumen,
        "config_hash": result.config_hash,
        "corrida_id": result.corrida_id,
        "fecha_corrida": result.fecha_corrida,
        "diferencias": [
            {
                "id_pc": d.id_pc,
                "cod_pc": d.cod_pc,
                "id_ejercicio": d.id_ejercicio,
                "id_periodo": d.id_periodo,
                "codigo_movimiento": d.codigo_movimiento,
                "nro_asiento": d.nro_asiento,
                "valor_esperado": str(d.valor_esperado) if d.valor_esperado is not None else None,
                "valor_actual": str(d.valor_actual) if d.valor_actual is not None else None,
                "delta": str(d.delta) if d.delta is not None else None,
                "referencia_hallazgo": d.referencia_hallazgo,
                "detalle": d.detalle,
            }
            for d in result.diferencias
        ],
    }


def ejecutar_corrida(
    base_empresa: str,
    filtros: dict,
    check_ids: Optional[list[str]] = None,
    usuario: str = "",
) -> dict[str, Any]:
    """
    Ejecuta checks read-only contra MySQL legacy y persiste resumen en Postgres.
    Una sola conexión por corrida; aislamiento de errores por check.
    """
    if not base_empresa:
        raise ValueError("base_empresa es obligatorio")
    if not filtros.get("id_ejercicio"):
        raise ValueError("id_ejercicio es obligatorio")

    politica = resolver_politica(base_empresa)
    config_hash = calcular_config_hash(politica)
    ids = check_ids or CHECK_IDS_DEFAULT
    desconocidos = [cid for cid in ids if cid not in CHECKS]
    if desconocidos:
        raise ValueError(f"Checks desconocidos: {', '.join(desconocidos)}")

    corrida = CorridaAuditoria.objects.create(
        base_empresa=base_empresa,
        filtros={**filtros, "check_ids": ids},
        config_hash=config_hash,
        ejecutada_por=usuario or "sistema",
    )

    resultados: list[AuditResult] = []
    resumen_corrida: dict[str, Any] = {}

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        contexto = CorridaContexto(
            cursor=cursor,
            corrida_id=str(corrida.corrida_id),
            config_hash=config_hash,
            fecha_corrida=corrida.fecha_corrida,
        )
        for check_id in ids:
            fn = CHECKS[check_id]
            try:
                result = fn(base_empresa, filtros, politica, contexto)
            except Exception as exc:
                logger.exception("Fallo check %s en corrida %s", check_id, corrida.corrida_id)
                from contabilidad_audit.services.resultados import audit_result_error

                result = audit_result_error(
                    check_id=check_id,
                    titulo=getattr(fn, "titulo", check_id),
                    severidad=getattr(fn, "severidad", "medio"),
                    contexto=contexto,
                    mensaje=str(exc),
                )
            resultados.append(result)
            resumen_corrida[check_id] = {
                "ok": result.ok,
                "total_evaluado": result.total_evaluado,
                "total_diferencias": result.total_diferencias,
                "error": result.error,
            }

    corrida.resumen = resumen_corrida
    corrida.save(update_fields=["resumen"])

    return {
        "corrida_id": str(corrida.corrida_id),
        "base_empresa": base_empresa,
        "config_hash": config_hash,
        "filtros": corrida.filtros,
        "fecha_corrida": resultados[0].fecha_corrida if resultados else "",
        "checks": [_audit_result_a_dict(r) for r in resultados],
    }
