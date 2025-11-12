from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from django.conf import settings
from django.utils import timezone


@dataclass
class ExportResult:
    """Resultado estandarizado de exportaciones."""

    path: str
    created_at: str
    expires_at: str | None = None


class ExportService:
    """Servicio para generar exportaciones PDF/XLSX."""

    def __init__(self, user):
        self.user = user

    def export(self, report_slug: str, payload: Dict, export_type: str) -> ExportResult:
        """Inicia un proceso de exportación (stub)."""
        # Comentario: Implementar en siguientes iteraciones (ReportLab / openpyxl).
        export_dir = Path(settings.MEDIA_ROOT) / "reports" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        filename = f"{report_slug}_{timestamp}.{export_type}"
        file_path = export_dir / filename
        file_path.write_text("Export not implemented yet.")

        return ExportResult(
            path=str(file_path.relative_to(settings.MEDIA_ROOT)),
            created_at=timezone.now().isoformat(),
            expires_at=None,
        )


