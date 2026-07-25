"""Plantillas de aviso/cobranza y encolado con anti-ruido SLA."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_int_or_none

from ecom.models import EcomMailQueue
from ecom.services.ecom_config_mysql import credito_aviso_sla_horas, credito_pedidos_activo

logger = logging.getLogger(__name__)

TIPO_PEDIDO_BLOQUEADO = "pedido_bloqueado"
TIPO_COBRANZA = "cobranza"

_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def renderizar_plantilla(
    asunto: str,
    cuerpo: str,
    variables: Dict[str, Any],
) -> Tuple[str, str]:
    """Sustituye ``{{clave}}`` en asunto y cuerpo."""

    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, ""))

    return (
        _VAR_PATTERN.sub(_repl, asunto or ""),
        _VAR_PATTERN.sub(_repl, cuerpo or ""),
    )


def _resolver_plantilla(
    cursor,
    *,
    id_cliente: int,
    canal: str,
    tipo_aviso: str,
) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT asunto, cuerpo, activo
        FROM ecom_credito_plantilla_aviso
        WHERE tipo_aviso = %s AND canal = %s
          AND (id_cliente = %s OR id_cliente IS NULL)
          AND activo = 'Si'
        ORDER BY id_cliente IS NULL ASC
        LIMIT 1
        """,
        (tipo_aviso, canal, id_cliente),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return row
    return {"asunto": row[0], "cuerpo": row[1], "activo": row[2]}


def debe_encolar_aviso(
    cursor,
    base_empresa: str,
    *,
    id_cliente: int,
    tipo_aviso: str,
    canal: str,
    codigo_movimiento: Optional[int] = None,
) -> bool:
    """
    True si corresponde encolar (no hay dedup activo).
    ``pedido_bloqueado``: 1× por CodigoMovimiento; resto: ventana SLA horas.
    """
    if not credito_pedidos_activo(base_empresa):
        return False

    tipo = str_or_default(tipo_aviso, "-")
    if tipo == TIPO_PEDIDO_BLOQUEADO and codigo_movimiento is not None:
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt FROM ecom_credito_aviso_log
            WHERE codigo_movimiento = %s AND tipo_aviso = %s
            """,
            (codigo_movimiento, tipo),
        )
        row = cursor.fetchone()
        cnt = row.get("cnt") if isinstance(row, dict) else row[0]
        return int(cnt or 0) == 0

    horas = credito_aviso_sla_horas(base_empresa)
    desde = datetime.now() - timedelta(hours=horas)
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt FROM ecom_credito_aviso_log
        WHERE id_cliente = %s AND tipo_aviso = %s AND canal = %s
          AND enviado_en >= %s
        """,
        (id_cliente, tipo, canal, desde),
    )
    row = cursor.fetchone()
    cnt = row.get("cnt") if isinstance(row, dict) else row[0]
    return int(cnt or 0) == 0


def _registrar_aviso_log(
    cursor,
    *,
    id_cliente: int,
    tipo_aviso: str,
    canal: str,
    codigo_movimiento: Optional[int],
) -> None:
    cursor.execute(
        """
        INSERT INTO ecom_credito_aviso_log
            (id_cliente, tipo_aviso, canal, codigo_movimiento, enviado_en)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (id_cliente, tipo_aviso, canal, codigo_movimiento, datetime.now()),
    )


def encolar_aviso_credito(
    *,
    base_empresa: str,
    to_email: str,
    asunto: str,
    cuerpo: str,
    payload: Optional[Dict[str, Any]] = None,
) -> EcomMailQueue:
    """Encola mail en ``EcomMailQueue`` (patrón comprobante_mail_async)."""
    return EcomMailQueue.objects.create(
        base_empresa=base_empresa,
        to_email=to_email,
        subject=asunto[:255],
        body_text=cuerpo,
        body_html=f"<p>{cuerpo.replace(chr(10), '<br>')}</p>",
        payload_json=payload or {},
    )


def disparar_aviso_pedido_bloqueado(
    cursor,
    base_empresa: str,
    *,
    cod_mov: int,
    id_cliente: int,
    canal: str,
    to_email: str,
    variables: Dict[str, Any],
) -> bool:
    """
    Dispara aviso ``pedido_bloqueado`` si hay plantilla y no aplica dedup.
    Devuelve True si se encoló.
    """
    if not debe_encolar_aviso(
        cursor,
        base_empresa,
        id_cliente=id_cliente,
        tipo_aviso=TIPO_PEDIDO_BLOQUEADO,
        canal=canal,
        codigo_movimiento=cod_mov,
    ):
        return False

    plantilla = _resolver_plantilla(
        cursor,
        id_cliente=id_cliente,
        canal=canal,
        tipo_aviso=TIPO_PEDIDO_BLOQUEADO,
    )
    if not plantilla:
        return False

    asunto, cuerpo = renderizar_plantilla(
        plantilla.get("asunto") or "Pedido retenido por crédito",
        plantilla.get("cuerpo") or "Su pedido {{nro_comprobante}} requiere aprobación Finanzas.",
        variables,
    )
    encolar_aviso_credito(
        base_empresa=base_empresa,
        to_email=to_email,
        asunto=asunto,
        cuerpo=cuerpo,
        payload={"codigo_movimiento": cod_mov, "tipo_aviso": TIPO_PEDIDO_BLOQUEADO},
    )
    _registrar_aviso_log(
        cursor,
        id_cliente=id_cliente,
        tipo_aviso=TIPO_PEDIDO_BLOQUEADO,
        canal=canal,
        codigo_movimiento=cod_mov,
    )
    return True
