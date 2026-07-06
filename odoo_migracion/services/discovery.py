"""F0 — inventario cuantitativo (reexporta extractores.discovery)."""

from odoo_migracion.extractors.discovery import (
    DiscoveryAnomaly,
    DiscoveryReport,
    run_discovery,
)

__all__ = ["DiscoveryAnomaly", "DiscoveryReport", "run_discovery"]
