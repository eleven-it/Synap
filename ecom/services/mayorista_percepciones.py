"""
Percepciones de Ingresos Brutos (IIBB) — checkout mayorista (Fase P4).

Réplica del cálculo legacy de `administraNET-ecom/mayoristapp/jcart/jcart.php`
(líneas 1093–1171) y del INSERT en `alta_pedido_confirmado.php` (407–421).

Opción **configurable por implementación**: se activa cuando la sucursal del
cliente es agente de percepción (`sucursales.agente_percep = 'Si'`). Si no lo es,
no se calcula nada (`total_percep = 0`, sin filas `percep_cli`).

Todas las lecturas usan el **cursor de la transacción abierta** por el checkout
(no abre conexión propia) para que el cálculo y las escrituras sean atómicos.
SQL parametrizado y normalización de tipos con `core.utils.administranet_types`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Tuple

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

Q2 = Decimal("0.01")


def _q2(v: Any) -> Decimal:
    d = v if isinstance(v, Decimal) else Decimal(str(v))
    return d.quantize(Q2, rounding=ROUND_HALF_UP)


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


class PercepcionesSinConfig(Exception):
    """La sucursal es agente de percepción pero el cliente no tiene tipos configurados."""


@dataclass
class PercepcionCalculada:
    id_percep_cli_tipo: int
    nombre: str
    alicuota: Decimal
    importe: Decimal
    cod_afip: int | None


def es_agente_percepcion(agente_percep: Any) -> bool:
    """Normaliza el flag legacy `sucursales.agente_percep` ('Si'/'No')."""
    return str(agente_percep or "").strip().lower() == "si"


def calcular_percepciones(
    cur,
    id_cliente: int,
    base_imponible: Any,
    agente_percep: Any,
) -> Tuple[List[PercepcionCalculada], Decimal]:
    """Calcula las percepciones IIBB del comprobante (paridad jcart.php).

    - Si la sucursal no es agente de percepción → ([], 0).
    - Si lo es: lee ``percep_cli_param`` del cliente y ``percep_cli_tipo`` por tipo,
      calcula ``importe = base * alicuota / 100`` (sin ``importe_minimo``), agrupa por
      tipo y devuelve el detalle + total.
    - Si es agente pero el cliente no tiene tipos configurados → ``PercepcionesSinConfig``.

    Usa el cursor de la transacción del checkout (lecturas dentro del mismo BEGIN).
    """
    if not es_agente_percepcion(agente_percep):
        return [], Decimal("0")

    base = _dec(base_imponible)

    cur.execute(
        "SELECT id_percep_cli_tipo FROM percep_cli_param WHERE id_cliente = %s",
        [int(id_cliente)],
    )
    filas_param = cur.fetchall() or []
    tipos_ids = [
        t for t in (to_int_or_none(_row_val(f, "id_percep_cli_tipo")) for f in filas_param)
        if t is not None
    ]
    if not tipos_ids:
        raise PercepcionesSinConfig(
            "El cliente no tiene percepciones de Ingresos Brutos configuradas "
            "y su sucursal es agente de percepción. Configure percep_cli_param "
            "o desactive agente_percep para la sucursal."
        )

    detalle: dict[int, PercepcionCalculada] = {}
    for id_tipo in tipos_ids:
        cur.execute(
            """
            SELECT id_percep_cli_tipo, nombre_percep_cli_tipo,
                   alicuota_percep_cli_tipo, cod_afip
            FROM percep_cli_tipo
            WHERE id_percep_cli_tipo = %s
            LIMIT 1
            """,
            [int(id_tipo)],
        )
        rec = cur.fetchone()
        if not rec:
            continue
        alic = _dec(_row_val(rec, "alicuota_percep_cli_tipo"))
        importe = _q2(base * alic / Decimal("100"))
        if id_tipo in detalle:
            detalle[id_tipo].importe = _q2(detalle[id_tipo].importe + importe)
        else:
            detalle[id_tipo] = PercepcionCalculada(
                id_percep_cli_tipo=int(id_tipo),
                nombre=str(_row_val(rec, "nombre_percep_cli_tipo") or ""),
                alicuota=alic,
                importe=importe,
                cod_afip=to_int_or_none(_row_val(rec, "cod_afip")),
            )

    items = list(detalle.values())
    total = _q2(sum((p.importe for p in items), Decimal("0")))
    return items, total


def _row_val(row: Any, key: str) -> Any:
    """Acceso a valor por clave soportando DictCursor (dict) o tupla."""
    if isinstance(row, dict):
        return row.get(key)
    return None
