"""
Base reutilizable para todos los PDF de reportes y comprobantes de Synap.
Encabezado con datos de empresa (y logo si existe), pie de página consistente,
estilo corporativo y minimalista. Usar desde stock, reports y futuros comprobantes.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Constantes de layout (unidades: mm)
MARGIN_MM = 20
LOGO_HEIGHT_MM = 20
FONT_TITLE_PT = 12
FONT_SUBTITLE_PT = 11
FONT_SECONDARY_PT = 8
GREY = (0.4, 0.4, 0.4)
LINE_GREY = (0.85, 0.85, 0.85)


def _formatear_cuit(cuit: Optional[str]) -> str:
    """Formatea CUIT a XX-XXXXXXXX-X (11 dígitos)."""
    if not cuit:
        return "-"
    digits = "".join(c for c in str(cuit) if c.isdigit())
    if len(digits) != 11:
        return cuit.strip() or "-"
    return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"


def _resolver_logo_empresa(nombre: str, cuit: str) -> Optional[str]:
    """
    Resuelve la ruta absoluta del logo desde el modelo Django Empresa
    (por nombre o CUIT). Devuelve path si el archivo existe; si no, None.
    """
    try:
        from core.models import Empresa

        cuit_limpio = "".join(c for c in str(cuit or "")) if cuit else ""
        empresa_django = None

        if cuit_limpio and len(cuit_limpio) >= 11:
            empresa_django = Empresa.objects.filter(
                identificador_fiscal__icontains=cuit_limpio[:11], activa=True
            ).first()
        if not empresa_django and (nombre or "").strip():
            empresa_django = Empresa.objects.filter(
                nombre__iexact=(nombre or "").strip(), activa=True
            ).first()
        if not empresa_django and (nombre or "").strip():
            empresa_django = Empresa.objects.filter(
                nombre__icontains=(nombre or "").strip(), activa=True
            ).first()

        if not empresa_django or not empresa_django.logo:
            return None

        # Ruta absoluta: MEDIA_ROOT + nombre del archivo relativo
        path = os.path.join(settings.MEDIA_ROOT, empresa_django.logo.name)
        if os.path.isfile(path):
            return path
        return None
    except Exception as e:
        logger.warning("No se pudo resolver logo para reporte PDF: %s", e)
        return None


def get_empresa_para_reporte(base_empresa: str) -> Dict[str, Any]:
    """
    Obtiene los datos de empresa para encabezados de reportes PDF.
    Usa AdministraNET (DatosEmpresa) y opcionalmente el logo del modelo Django Empresa.

    Returns:
        dict con: razon_social, domicilio, cuit_formateado, logo_path (opcional).
    """
    try:
        from core.services.administranet_empresas import AdministraNETEmpresaService
    except ImportError:
        return {
            "razon_social": "-",
            "domicilio": "-",
            "cuit_formateado": "-",
            "logo_path": None,
        }

    data = AdministraNETEmpresaService().obtener_empresa(base_empresa)
    if not data:
        return {
            "razon_social": "-",
            "domicilio": "-",
            "cuit_formateado": "-",
            "logo_path": None,
        }

    nombre = (data.get("Nombre") or "").strip() or "-"
    domicilio = (data.get("Domicilio") or "").strip() or "-"
    cuit = data.get("CUIT")
    cuit_formateado = _formatear_cuit(cuit) if cuit else "-"

    logo_path = _resolver_logo_empresa(nombre, cuit or "")

    return {
        "razon_social": nombre,
        "domicilio": domicilio,
        "cuit_formateado": cuit_formateado,
        "logo_path": logo_path,
    }


def draw_report_header(
    canvas: Any,
    empresa: Dict[str, Any],
    titulo: str,
    y_start: float,
) -> float:
    """
    Dibuja el encabezado corporativo: logo (si existe), razón social, domicilio/CUIT,
    línea de separación y título del reporte.

    Args:
        canvas: ReportLab canvas.
        empresa: dict de get_empresa_para_reporte (razon_social, domicilio, cuit_formateado, logo_path).
        titulo: Título del reporte (ej. "Comprobante de Movimiento de Stock").
        y_start: Coordenada y (en puntos) donde empieza el encabezado (ej. 297*mm para A4).

    Returns:
        Coordenada y donde termina el encabezado (donde el llamador debe dibujar el contenido).
    """
    from reportlab.lib.units import mm

    margin = MARGIN_MM * mm
    y = y_start

    # Logo (izquierda, altura máxima LOGO_HEIGHT_MM)
    logo_path = empresa.get("logo_path")
    if logo_path and os.path.isfile(logo_path):
        try:
            from reportlab.lib.utils import ImageReader

            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            h = LOGO_HEIGHT_MM * mm
            w = (iw / ih) * h if ih else h
            # Dibujar con esquina superior izquierda en (margin, y - h)
            canvas.drawImage(logo_path, margin, y - h, width=w, height=h)
            # Si el logo es ancho, dejar espacio a la derecha del logo para el texto
            text_x = margin + w + (4 * mm)
        except Exception as e:
            logger.warning("No se pudo dibujar logo en PDF: %s", e)
            text_x = margin
    else:
        text_x = margin

    # Línea 1: razón social (Helvetica-Bold 12pt)
    canvas.setFont("Helvetica-Bold", FONT_TITLE_PT)
    canvas.setFillColorRGB(0, 0, 0)
    canvas.drawString(text_x, y - (5 * mm), (empresa.get("razon_social") or "-")[:80])

    # Línea 2: domicilio, CUIT (8pt gris)
    canvas.setFont("Helvetica", FONT_SECONDARY_PT)
    canvas.setFillColorRGB(*GREY)
    linea2 = f"{empresa.get('domicilio') or '-'}  ·  CUIT {empresa.get('cuit_formateado') or '-'}"
    canvas.drawString(text_x, y - (10 * mm), linea2[:120])
    y = y - (14 * mm)

    # Línea de separación (0,5 pt gris)
    canvas.setStrokeColorRGB(*LINE_GREY)
    canvas.setLineWidth(0.5)
    canvas.line(margin, y, canvas._pagesize[0] - margin, y)
    y -= 4 * mm

    # Título del reporte (11pt)
    canvas.setFont("Helvetica", FONT_SUBTITLE_PT)
    canvas.setFillColorRGB(0, 0, 0)
    canvas.drawString(margin, y, titulo)
    y -= 8 * mm

    return y


def draw_report_footer(
    canvas: Any,
    pagina_actual: Optional[int] = None,
    total_paginas: Optional[int] = None,
) -> None:
    """
    Dibuja el pie de página: línea y texto "Synap · Generado el DD/MM/AAAA HH:MM"
    y opcionalmente "Página N" a la derecha.

    Args:
        canvas: ReportLab canvas.
        pagina_actual: Número de página actual (opcional).
        total_paginas: Total de páginas (opcional).
    """
    from reportlab.lib.units import mm

    margin = MARGIN_MM * mm
    now = datetime.now()
    texto_fecha = now.strftime("%d/%m/%Y %H:%M")

    # Línea de separación
    y_line = 18 * mm
    canvas.setStrokeColorRGB(*LINE_GREY)
    canvas.setLineWidth(0.5)
    canvas.line(margin, y_line, canvas._pagesize[0] - margin, y_line)

    # Texto "Synap · Generado el ..."
    canvas.setFont("Helvetica", FONT_SECONDARY_PT)
    canvas.setFillColorRGB(*GREY)
    canvas.drawString(margin, 12 * mm, f"Synap · Generado el {texto_fecha}")

    if pagina_actual is not None:
        pag_texto = f"Página {pagina_actual}" + (f" de {total_paginas}" if total_paginas is not None else "")
        canvas.drawRightString(canvas._pagesize[0] - margin, 12 * mm, pag_texto)
