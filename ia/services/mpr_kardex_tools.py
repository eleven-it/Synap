from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ia.services.policy_gate import PolicyContext, PolicyGate
from mpr.services import construir_kardex_articulo, get_deposito_semi_elaborado_mpr
from mpr.services_maquina_linea import buscar_articulos

KARDEX_REPORT_SLUG = "mpr-kardex-articulo"
MAX_MOVIMIENTOS_LLM = 20
_MPR_KARDEX_PERMISSIONS = frozenset({"mpr.ver", "mpr.reportes"})


def _has_mpr_kardex_permission(policy_context: PolicyContext) -> bool:
    if PolicyGate.is_full_access_user(policy_context.user):
        return True
    perms = policy_context.permissions or set()
    return bool(_MPR_KARDEX_PERMISSIONS & perms)


def _format_fecha_display(iso_date: str) -> str:
    if not iso_date:
        return ""
    try:
        d = date.fromisoformat(iso_date)
    except ValueError:
        return iso_date
    return d.strftime("%d/%m/%Y")


def _resolve_id_deposito(policy_context: PolicyContext, filters: dict) -> int | None:
    raw = filters.get("id_deposito")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    if filters.get("deposito_hint_semi") or filters.get("deposito_hint") == "semi":
        return get_deposito_semi_elaborado_mpr(policy_context.base_empresa or "")
    return get_deposito_semi_elaborado_mpr(policy_context.base_empresa or "")


def _resolve_id_articulo(policy_context: PolicyContext, filters: dict) -> tuple[int | None, str | None]:
    raw_id = filters.get("id_articulo")
    if raw_id is not None:
        try:
            return int(raw_id), None
        except (TypeError, ValueError):
            pass

    codigo = (filters.get("codigo_articulo") or "").strip()
    if not codigo:
        return None, "Indicá el código o nombre del artículo para consultar el kardex."

    base = policy_context.base_empresa or ""
    candidatos = buscar_articulos(base, codigo, limit=10)
    if not candidatos:
        return None, f"No encontré ningún artículo que coincida con «{codigo}». Verificá el código e intentá de nuevo."

    if len(candidatos) == 1:
        return int(candidatos[0]["id_articulo"]), None

    lineas = []
    for i, art in enumerate(candidatos[:8], 1):
        cod = art.get("codigo_manual") or art.get("codigo_articulo") or "—"
        desc = (art.get("descripcion_articulo") or "").strip()
        lineas.append(f"{i}. {cod} — {desc}" if desc else f"{i}. {cod}")
    return None, (
        "Hay más de un artículo que coincide. Indicá cuál querés consultar:\n"
        + "\n".join(lineas)
    )


def _default_periodo(filters: dict) -> tuple[str, str]:
    desde = filters.get("fecha_desde") or filters.get("desde")
    hasta = filters.get("fecha_hasta") or filters.get("hasta")
    if desde and hasta:
        return str(desde), str(hasta)
    hoy = date.today()
    return (hoy - timedelta(days=6)).isoformat(), hoy.isoformat()


def _resumir_bom(bom: dict | None) -> str:
    if not bom:
        return ""
    componentes = bom.get("componentes") or bom.get("items") or []
    if not componentes:
        return ""
    n = len(componentes)
    muestra = []
    for comp in componentes[:3]:
        cod = comp.get("codigo") or comp.get("codigo_manual") or comp.get("id_articulo") or "—"
        qty = comp.get("cantidad") or comp.get("qty") or "—"
        muestra.append(f"{cod}×{qty}")
    texto = f"BOM: {n} componente(s)"
    if muestra:
        texto += f" ({', '.join(muestra)}{'…' if n > 3 else ''})"
    return texto


def _build_answer_text(
    *,
    kardex: dict,
    fecha_desde: str,
    fecha_hasta: str,
    movimientos_recientes: list[dict],
) -> str:
    articulo = kardex.get("articulo") or {}
    deposito = kardex.get("deposito") or {}
    kpis = kardex.get("kpis") or {}
    codigo = articulo.get("codigo") or "—"
    dep_nombre = deposito.get("nombre") or "depósito indicado"
    d_ini = _format_fecha_display(fecha_desde)
    d_fin = _format_fecha_display(fecha_hasta)
    saldo = int(kpis.get("saldo_final") or 0)
    partes = [
        f"Kardex del artículo {codigo} en {dep_nombre} entre {d_ini} y {d_fin}: "
        f"saldo final {saldo} unidades."
    ]
    bom_txt = _resumir_bom(kardex.get("bom"))
    if bom_txt:
        partes.append(bom_txt)
    max_packs = kpis.get("max_packs")
    if articulo.get("es_pack") and max_packs is not None:
        partes.append(f"Máximo de packs armables: {int(max_packs)}.")
    if movimientos_recientes:
        partes.append("Últimos movimientos:")
        for mov in movimientos_recientes:
            fecha = mov.get("fecha_display") or "—"
            tipo = mov.get("tipo_mov") or "—"
            ent = int(mov.get("entrada") or 0)
            sal = int(mov.get("salida") or 0)
            corr = int(mov.get("saldo_corrido") or 0)
            nro = mov.get("nro_comprobante") or "—"
            partes.append(
                f"- {fecha} {tipo}: +{ent}/−{sal}, saldo {corr} (comprob. {nro})"
            )
    else:
        partes.append("No hay movimientos OPP/OPA en el período consultado.")
    advertencias = kardex.get("advertencias") or []
    for adv in advertencias:
        if adv:
            partes.append(str(adv))
    partes.append(
        "Para el detalle completo del ledger, usá el reporte "
        "«Kardex artículo» en MPR → Trazabilidad."
    )
    return "\n".join(partes)


def execute_kardex_articulo(policy_context: PolicyContext, filters: dict | None = None) -> dict[str, Any]:
    """
    Ejecuta kardex MPR vía servicio canon (sin SQL libre).
    Devuelve texto NL + payload acotado para el LLM (KPIs, BOM resumido, ≤20 movimientos).
    """
    filtros = dict(filters or {})
    if not _has_mpr_kardex_permission(policy_context):
        return {
            "answer": "",
            "payload": {},
            "requires_clarification": True,
            "clarification_question": (
                "No tenés permisos para consultar trazabilidad MPR. "
                "Se requiere permiso mpr.ver o mpr.reportes."
            ),
            "status": "partial",
        }

    base = policy_context.base_empresa or ""
    if not base:
        return {
            "answer": "",
            "payload": {},
            "requires_clarification": True,
            "clarification_question": "No pude determinar la base de empresa de la sesión.",
            "status": "partial",
        }

    id_articulo, clarificacion = _resolve_id_articulo(policy_context, filtros)
    if clarificacion:
        return {
            "answer": "",
            "payload": {},
            "requires_clarification": True,
            "clarification_question": clarificacion,
            "status": "partial",
        }

    id_deposito = _resolve_id_deposito(policy_context, filtros)
    fecha_desde, fecha_hasta = _default_periodo(filtros)

    kardex = construir_kardex_articulo(
        base,
        int(id_articulo),
        id_deposito=id_deposito,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    movimientos = kardex.get("movimientos") or []
    recientes = movimientos[-MAX_MOVIMIENTOS_LLM:]
    recientes_payload = [
        {
            "fecha_display": m.get("fecha_display"),
            "tipo_mov": m.get("tipo_mov"),
            "entrada": m.get("entrada"),
            "salida": m.get("salida"),
            "saldo_corrido": m.get("saldo_corrido"),
            "nro_comprobante": m.get("nro_comprobante"),
        }
        for m in recientes
    ]

    payload = {
        "articulo": kardex.get("articulo"),
        "deposito": kardex.get("deposito"),
        "kpis": kardex.get("kpis"),
        "bom_resumen": _resumir_bom(kardex.get("bom")),
        "movimientos_recientes": recientes_payload,
        "total_movimientos": len(movimientos),
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }

    answer = _build_answer_text(
        kardex=kardex,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        movimientos_recientes=recientes_payload,
    )

    return {
        "answer": answer,
        "payload": payload,
        "requires_clarification": False,
        "status": "success",
    }
