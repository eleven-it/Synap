"""Evaluación unificada de crédito en checkout y pre-check."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.services.credito_pedidos.exposicion import calcular_exposicion
from ecom.services.credito_pedidos.politica import resolver_politica
from ecom.services.mayorista_credito import AUTORIZADO, NO_AUTORIZADO, dias_atraso

SEMAFORO_VERDE = "verde"
SEMAFORO_AMBAR = "ambar"
SEMAFORO_ROJO = "rojo"

MOTIVO_MONTO = "monto"
MOTIVO_DIAS = "dias"


@dataclass
class ResultadoCredito:
    autorizacion: str
    motivos: List[str] = field(default_factory=list)
    limite: Decimal = Decimal("0")
    exposicion: Decimal = Decimal("0")
    disponible: Optional[Decimal] = None
    dias_atraso: Optional[int] = None
    capas: Dict[str, Decimal] = field(default_factory=dict)
    semaforo: str = SEMAFORO_VERDE
    evaluacion_id: Optional[int] = None
    sin_tope_monetario: bool = False


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


def _resolver_limite_dias(politica_limite: Optional[int], credito_limite_dias: int) -> int:
    if politica_limite is not None:
        return int(politica_limite)
    return int(credito_limite_dias or 0)


def _calcular_semaforo(
    *,
    autorizacion: str,
    sin_tope: bool,
    limite: Decimal,
    disponible: Optional[Decimal],
    dias_atraso_val: Optional[int],
    limite_dias: int,
) -> str:
    if autorizacion == NO_AUTORIZADO:
        return SEMAFORO_ROJO
    if (
        not sin_tope
        and limite > 0
        and disponible is not None
        and disponible <= (limite * Decimal("0.10"))
    ):
        return SEMAFORO_AMBAR
    if (
        limite_dias > 0
        and dias_atraso_val is not None
        and dias_atraso_val > max(limite_dias - 5, 0)
    ):
        return SEMAFORO_AMBAR
    return SEMAFORO_VERDE


def _persistir_evaluacion(
    cur: Any,
    *,
    codigo_movimiento: int,
    id_cliente: int,
    canal: str,
    resultado: ResultadoCredito,
) -> int:
    capas_json = json.dumps(
        {k: str(v) for k, v in resultado.capas.items()},
        ensure_ascii=False,
    )
    motivos_txt = ",".join(resultado.motivos) if resultado.motivos else "-"
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """
        INSERT INTO ecom_credito_evaluacion (
            codigo_movimiento, id_cliente, canal, autorizacion, motivos,
            limite, exposicion, disponible, dias_atraso, capas_json, semaforo, creado_en
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            codigo_movimiento,
            id_cliente,
            canal,
            resultado.autorizacion,
            motivos_txt,
            resultado.limite if not resultado.sin_tope_monetario else None,
            resultado.exposicion,
            resultado.disponible,
            resultado.dias_atraso,
            capas_json,
            resultado.semaforo,
            ahora,
        ],
    )
    ev_id = getattr(cur, "lastrowid", None)
    return int(to_int_or_none(ev_id) or 0)


def evaluar_pedido(
    cur: Any,
    *,
    id_cliente: int,
    canal: str,
    total_pedido: Decimal,
    credito_cliente: Decimal,
    credito_limite_dias: int,
    es_cliente: bool = False,
    persistir: bool = False,
    codigo_movimiento: Optional[int] = None,
) -> ResultadoCredito:
    """
    Evalúa crédito según política, exposición y mora.
    ``Credito=0`` ⇒ sin tope monetario (solo días/capas no monetarias según política).
    """
    canal_norm = str_or_default(canal, "PED").upper()
    idc = int(to_int_or_none(id_cliente) or 0)
    limite = _dec(credito_cliente)
    sin_tope = limite <= 0

    politica = resolver_politica(cur, idc, canal_norm)
    exp = calcular_exposicion(cur, idc, politica, doc_actual=_dec(total_pedido))

    disponible: Optional[Decimal]
    if sin_tope:
        disponible = None
    else:
        disponible = limite - exp.total

    motivos: List[str] = []
    atraso = dias_atraso(cur, idc) if politica.incluir_mora else None
    limite_dias = _resolver_limite_dias(politica.limite_dias, credito_limite_dias)

    if not sin_tope and exp.total > limite:
        motivos.append(MOTIVO_MONTO)
    if politica.incluir_mora and limite_dias > 0 and atraso is not None and atraso > limite_dias:
        motivos.append(MOTIVO_DIAS)

    autorizacion = AUTORIZADO
    if es_cliente or motivos:
        autorizacion = NO_AUTORIZADO

    semaforo = _calcular_semaforo(
        autorizacion=autorizacion,
        sin_tope=sin_tope,
        limite=limite,
        disponible=disponible,
        dias_atraso_val=atraso,
        limite_dias=limite_dias,
    )

    resultado = ResultadoCredito(
        autorizacion=autorizacion,
        motivos=motivos,
        limite=limite,
        exposicion=exp.total,
        disponible=disponible,
        dias_atraso=atraso,
        capas=dict(exp.capas),
        semaforo=semaforo,
        sin_tope_monetario=sin_tope,
    )

    if persistir:
        cod_mov = to_int_or_none(codigo_movimiento)
        if cod_mov is None:
            raise ValueError("codigo_movimiento es obligatorio para persistir la evaluación.")
        resultado.evaluacion_id = _persistir_evaluacion(
            cur,
            codigo_movimiento=int(cod_mov),
            id_cliente=idc,
            canal=canal_norm,
            resultado=resultado,
        )

    return resultado


def resultado_credito_a_dict(resultado: ResultadoCredito) -> Dict[str, Any]:
    """Serialización JSON-friendly para APIs y relay."""
    return {
        "autorizacion": resultado.autorizacion,
        "motivos": list(resultado.motivos),
        "limite": float(resultado.limite),
        "exposicion": float(resultado.exposicion),
        "disponible": float(resultado.disponible) if resultado.disponible is not None else None,
        "dias_atraso": resultado.dias_atraso,
        "capas": {k: float(v) for k, v in resultado.capas.items()},
        "semaforo": resultado.semaforo,
        "sin_tope_monetario": resultado.sin_tope_monetario,
        "evaluacion_id": resultado.evaluacion_id,
    }
