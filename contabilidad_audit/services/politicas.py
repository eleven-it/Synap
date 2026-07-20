"""Resolución de políticas y cálculo de config_hash."""
from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal
from typing import Any

from contabilidad_audit.models import (
    ALCANCE_RECOMPUTE_CHOICES,
    CATEGORIAS_PREFIJOS,
    EJERCICIOS_CERRADOS_CHOICES,
    HistorialPoliticaAuditoria,
    PREFIJOS_CUENTA_DEFAULT,
    POLITICA_CENTAVO_CHOICES,
    PoliticaAuditoriaContable,
    TRATAMIENTO_ANULADOS_CHOICES,
)

logger = logging.getLogger(__name__)

CAMPOS_POLITICA = (
    "tratamiento_anulados",
    "politica_centavo",
    "prefijos_cuenta",
    "ejercicios_cerrados",
    "alcance_recompute",
    "tolerancia_decimal",
)


def _modelo_a_dict(politica: PoliticaAuditoriaContable) -> dict[str, Any]:
    return {
        "tratamiento_anulados": politica.tratamiento_anulados,
        "politica_centavo": politica.politica_centavo,
        "prefijos_cuenta": politica.prefijos_cuenta or {},
        "ejercicios_cerrados": politica.ejercicios_cerrados,
        "alcance_recompute": politica.alcance_recompute,
        "tolerancia_decimal": politica.tolerancia_decimal,
    }


def _defaults_globales() -> dict[str, Any]:
    return {
        "tratamiento_anulados": "excluir",
        "politica_centavo": "diario_manda",
        "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
        "ejercicios_cerrados": "no_tocar",
        "alcance_recompute": "ejercicio_seleccionado",
        "tolerancia_decimal": Decimal("0.005"),
    }


def resolver_politica(base_empresa: str) -> dict[str, Any]:
    """
    Carga política global __default__ y aplica override campo a campo.
    Fallback defensivo de prefijos vacíos desde default global.
    """
    efectiva = _defaults_globales()
    default_row = PoliticaAuditoriaContable.objects.filter(
        base_empresa=PoliticaAuditoriaContable.BASE_DEFAULT
    ).first()
    if default_row:
        efectiva.update(_modelo_a_dict(default_row))

    override = (
        None
        if base_empresa == PoliticaAuditoriaContable.BASE_DEFAULT
        else PoliticaAuditoriaContable.objects.filter(base_empresa=base_empresa).first()
    )
    if override:
        override_dict = _modelo_a_dict(override)
        for campo in CAMPOS_POLITICA:
            valor = override_dict.get(campo)
            if valor is not None and valor != "":
                efectiva[campo] = valor

    prefijos = dict(efectiva.get("prefijos_cuenta") or {})
    default_prefijos = (
        (default_row.prefijos_cuenta if default_row else None)
        or PREFIJOS_CUENTA_DEFAULT
    )
    for cat in CATEGORIAS_PREFIJOS:
        if cat not in prefijos or not prefijos.get(cat):
            fallback = default_prefijos.get(cat) or PREFIJOS_CUENTA_DEFAULT.get(cat, [])
            if fallback:
                logger.warning(
                    "Política %s: prefijo '%s' vacío; se usa fallback global %s",
                    base_empresa,
                    cat,
                    fallback,
                )
                prefijos[cat] = list(fallback)
    efectiva["prefijos_cuenta"] = prefijos
    efectiva["base_empresa_resuelta"] = base_empresa
    return efectiva


def calcular_config_hash(politica: dict) -> str:
    """Hash determinista v1:sha256 según design §5 decisión 4."""
    canon: dict[str, Any] = {}
    for k in CAMPOS_POLITICA:
        v = politica[k]
        if isinstance(v, dict):
            v = {kk: sorted(map(str, vv)) for kk, vv in sorted(v.items())}
        elif isinstance(v, Decimal):
            v = format(v, ".4f")
        canon[k] = v
    payload = json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


ETIQUETAS_CAMPO_POLITICA: dict[str, str] = {
    "tratamiento_anulados": "Tratamiento de anulados",
    "politica_centavo": "Política de centavo",
    "prefijos_cuenta": "Prefijos de cuenta",
    "ejercicios_cerrados": "Ejercicios cerrados",
    "alcance_recompute": "Alcance de recálculo",
    "tolerancia_decimal": "Tolerancia decimal",
}

_CHOICES_POR_CAMPO: dict[str, dict[str, str]] = {
    "tratamiento_anulados": dict(TRATAMIENTO_ANULADOS_CHOICES),
    "politica_centavo": dict(POLITICA_CENTAVO_CHOICES),
    "ejercicios_cerrados": dict(EJERCICIOS_CERRADOS_CHOICES),
    "alcance_recompute": dict(ALCANCE_RECOMPUTE_CHOICES),
}


def snapshot_desde_politica(politica: PoliticaAuditoriaContable | dict | None) -> dict[str, Any] | None:
    """Serializa los campos de política para historial (JSON-safe)."""
    if politica is None:
        return None
    raw = _modelo_a_dict(politica) if isinstance(politica, PoliticaAuditoriaContable) else dict(politica)
    snapshot: dict[str, Any] = {}
    for campo in CAMPOS_POLITICA:
        valor = raw.get(campo)
        if isinstance(valor, Decimal):
            valor = format(valor, ".4f")
        elif isinstance(valor, dict):
            valor = {k: list(v) if isinstance(v, list) else v for k, v in valor.items()}
        snapshot[campo] = valor
    return snapshot


def _formatear_valor_campo(campo: str, valor: Any) -> str:
    if valor is None:
        return "—"
    if campo in _CHOICES_POR_CAMPO:
        return _CHOICES_POR_CAMPO[campo].get(str(valor), str(valor))
    if isinstance(valor, dict):
        partes = []
        for cat in CATEGORIAS_PREFIJOS:
            items = valor.get(cat) or []
            if items:
                partes.append(f"{cat}: {', '.join(map(str, items))}")
        return "; ".join(partes) if partes else "—"
    return str(valor)


def diff_snapshots_politica(
    anterior: dict[str, Any] | None,
    nuevo: dict[str, Any],
) -> list[dict[str, str]]:
    """Lista campos que cambiaron entre dos snapshots de política."""
    cambios: list[dict[str, str]] = []
    for campo in CAMPOS_POLITICA:
        val_ant = (anterior or {}).get(campo)
        val_nuevo = nuevo.get(campo)
        if val_ant != val_nuevo:
            cambios.append(
                {
                    "campo": campo,
                    "etiqueta": ETIQUETAS_CAMPO_POLITICA.get(campo, campo),
                    "anterior": _formatear_valor_campo(campo, val_ant),
                    "nuevo": _formatear_valor_campo(campo, val_nuevo),
                }
            )
    return cambios


def registrar_historial_politica(
    base_empresa: str,
    anterior: PoliticaAuditoriaContable | dict | None,
    nuevo: PoliticaAuditoriaContable | dict,
    usuario: str,
) -> HistorialPoliticaAuditoria:
    """Persiste una fila de historial al crear o modificar una política (POL-10)."""
    snap_anterior = snapshot_desde_politica(anterior)
    snap_nuevo = snapshot_desde_politica(nuevo)
    assert snap_nuevo is not None
    hash_anterior = calcular_config_hash(snap_anterior) if snap_anterior else None
    hash_nuevo = calcular_config_hash(snap_nuevo)
    return HistorialPoliticaAuditoria.objects.create(
        base_empresa=base_empresa,
        snapshot_anterior=snap_anterior,
        snapshot_nuevo=snap_nuevo,
        config_hash_anterior=hash_anterior,
        config_hash_nuevo=hash_nuevo,
        cambiado_por=usuario,
    )


def listar_historial_politica(base_empresa: str, limite: int = 50) -> list[dict[str, Any]]:
    """Historial consultable con diffs legibles para la UI."""
    filas = []
    for registro in HistorialPoliticaAuditoria.objects.filter(base_empresa=base_empresa)[:limite]:
        filas.append(
            {
                "id": registro.id,
                "cambiado_en": registro.cambiado_en,
                "cambiado_por": registro.cambiado_por,
                "config_hash_anterior": registro.config_hash_anterior or "",
                "config_hash_nuevo": registro.config_hash_nuevo,
                "es_alta": registro.snapshot_anterior is None,
                "cambios": diff_snapshots_politica(
                    registro.snapshot_anterior,
                    registro.snapshot_nuevo,
                ),
            }
        )
    return filas
