"""F0 — inventario cuantitativo por dominio."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.mysql_pool import get_connection

from odoo_migracion.services.domains import DOMAIN_SPECS


@dataclass
class DiscoveryAnomaly:
    dominio: str
    codigo: str
    mensaje: str
    cantidad: int = 0


@dataclass
class DiscoveryReport:
    base_empresa: str
    conteos: Dict[str, int] = field(default_factory=dict)
    anomalias: List[DiscoveryAnomaly] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_empresa": self.base_empresa,
            "conteos": self.conteos,
            "anomalias": [
                {"dominio": a.dominio, "codigo": a.codigo, "mensaje": a.mensaje, "cantidad": a.cantidad}
                for a in self.anomalias
            ],
        }


def run_discovery(base_empresa: str) -> DiscoveryReport:
    """Conteos por dominio y anomalías básicas de integridad."""
    report = DiscoveryReport(base_empresa=base_empresa.strip())
    be = report.base_empresa

    for spec in DOMAIN_SPECS:
        try:
            report.conteos[spec.key] = spec.extractor_cls(be).count()
        except Exception as exc:
            report.anomalias.append(
                DiscoveryAnomaly(spec.key, "count_error", str(exc)[:200])
            )

    _detect_anomalies(be, report)
    return report


def _detect_anomalies(base_empresa: str, report: DiscoveryReport) -> None:
    checks = [
        (
            "cliente",
            "sin_cuit",
            "SELECT COUNT(*) FROM cliente WHERE Estado = 'Activo' AND (CUIT IS NULL OR TRIM(CUIT) = '' OR CUIT = '0')",
        ),
        (
            "articulo",
            "sin_rubro",
            "SELECT COUNT(*) FROM articulo WHERE (CodigoRubro IS NULL OR CodigoRubro = 0)",
        ),
        (
            "articulo",
            "sin_uom",
            "SELECT COUNT(*) FROM articulo WHERE (id_unimed IS NULL OR id_unimed = 0)",
        ),
        (
            "stock_saldo",
            "saldo_negativo",
            "SELECT COUNT(*) FROM stock_deposito WHERE saldo < 0",
        ),
        (
            "cuenta_cliente",
            "abiertas_sin_saldo",
            """
            SELECT COUNT(*) FROM cuentacliente
            WHERE Anulado = 'No' AND (saldo IS NULL OR saldo = 0)
              AND TipoComprobante IN ('FA','FB','FC','ND')
            """,
        ),
    ]
    with get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        for dominio, codigo, sql in checks:
            try:
                cursor.execute(sql)
                row = cursor.fetchone()
                n = int(row[0] or 0) if row else 0
                if n > 0:
                    report.anomalias.append(
                        DiscoveryAnomaly(
                            dominio,
                            codigo,
                            f"Registros con condición {codigo}",
                            n,
                        )
                    )
            except Exception:
                pass
