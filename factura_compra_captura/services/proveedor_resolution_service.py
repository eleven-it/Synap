from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from core.services.administranet_compras import buscar_proveedores
from factura_compra_captura.services.proveedor_legacy_service import (
    crear_proveedor_desde_borrador,
)
from self_checkout.services.padron_afip_service import consultar_condicion_fiscal

logger = logging.getLogger(__name__)


def _normalizar_cuit(cuit: str) -> str:
    return "".join(ch for ch in str(cuit or "") if ch.isdigit())


@dataclass(frozen=True)
class ProveedorResolucion:
    encontrado_legacy: bool
    codigo_proveedor_legacy: int | None
    proveedor_synap: dict
    detail: str


def resolver_proveedor_desde_legacy_o_padron(
    *,
    base_empresa: str,
    cuit: str,
    razon_social_borrador: str = "",
) -> ProveedorResolucion:
    """
    Regla negocio: siempre intentar primero AdministraNET.
    Si no existe por CUIT, consultar padrón AFIP y devolver borrador parcial.
    """
    cuit_norm = _normalizar_cuit(cuit)
    if len(cuit_norm) != 11:
        raise ValueError("CUIT inválido (debe tener 11 dígitos).")

    encontrados = buscar_proveedores(base_empresa, cuit_norm, limite=10)
    for row in encontrados:
        row_cuit = _normalizar_cuit(str(row.get("CUIT") or ""))
        if row_cuit == cuit_norm:
            return ProveedorResolucion(
                encontrado_legacy=True,
                codigo_proveedor_legacy=int(row.get("Codigo")),
                proveedor_synap={
                    "modo": "legacy_vinculado",
                    "cuit": cuit_norm,
                    "razon_social": str(row.get("Nombre") or "").strip(),
                    "responsabilidad_iva": str(row.get("responsabilidad_iva") or "").strip(),
                    "origen": "administranet",
                    "actualizado_en": datetime.now(timezone.utc).isoformat(),
                },
                detail="Proveedor encontrado en AdministraNET.",
            )

    tipo, denominacion, err = consultar_condicion_fiscal(base_empresa, cuit_norm)
    proveedor_synap_borrador = {
        "modo": "borrador_nuevo",
        "cuit": cuit_norm,
        "razon_social": (denominacion or razon_social_borrador or "").strip(),
        "tipo_factura_sugerida": tipo,
        "padron_detalle": err or {},
        "origen": "padron_afip",
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    if err:
        return ProveedorResolucion(
            encontrado_legacy=False,
            codigo_proveedor_legacy=None,
            proveedor_synap=proveedor_synap_borrador,
            detail=f"No existe en AdministraNET y el padrón AFIP no respondió: {err.get('msg', 'sin detalle')}",
        )

    # Misma cadena que TPV/self_checkout: padrón AFIP vía consultar_condicion_fiscal (A5/A4, certificados FE).
    razon_alta = (denominacion or razon_social_borrador or "").strip()
    try:
        dto = crear_proveedor_desde_borrador(
            base_empresa=base_empresa,
            cuit=cuit_norm,
            razon_social=razon_alta,
            tipo_factura_sugerida=tipo,
        )
        return ProveedorResolucion(
            encontrado_legacy=True,
            codigo_proveedor_legacy=dto.codigo,
            proveedor_synap={
                "modo": "legacy_vinculado",
                "cuit": cuit_norm,
                "razon_social": dto.nombre,
                "tipo_factura_sugerida": tipo,
                "responsabilidad_iva": "",
                "origen": "alta_administranet_tras_padron_afip",
                "actualizado_en": datetime.now(timezone.utc).isoformat(),
            },
            detail="Proveedor creado en AdministraNET tras validación en padrón AFIP.",
        )
    except Exception as e:
        logger.exception("crear_proveedor_desde_borrador tras padrón AFIP")
        return ProveedorResolucion(
            encontrado_legacy=False,
            codigo_proveedor_legacy=None,
            proveedor_synap=proveedor_synap_borrador,
            detail=(
                "AFIP validó el CUIT pero no se pudo crear el proveedor en AdministraNET: "
                f"{e}"
            ),
        )
