"""
APIs para exportación de reportes a Excel y PDF
"""
import json
import os
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from ..services.export_service import ReportExportService
from ..models import ReportRequest, ReportExport, ChatMessage
from core.models.models import Empresa


# Instancia global del servicio
export_service = ReportExportService()


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def export_report(request, report_id):
    """
    Genera exportación de un reporte
    
    POST /api/export/<report_id>/
    Body: {
        "format": "excel|pdf",
        "chat_message_id": "uuid"  // opcional
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        export_format = data.get('format', 'excel').lower()
        chat_message_id = data.get('chat_message_id')
        
        if export_format not in ['excel', 'pdf']:
            return JsonResponse({
                'success': False,
                'error': 'Formato no válido. Usa "excel" o "pdf"'
            }, status=400)
        
        # Obtener reporte
        report_request = get_object_or_404(ReportRequest, id=report_id)
        
        # Obtener empresa del usuario
        empresa = None
        if hasattr(request.user, 'empresa'):
            empresa = request.user.empresa
        elif Empresa.objects.exists():
            empresa = Empresa.objects.first()
        
        # Obtener mensaje de chat si se especificó
        chat_message = None
        if chat_message_id:
            try:
                chat_message = ChatMessage.objects.get(message_id=chat_message_id)
            except ChatMessage.DoesNotExist:
                pass
        
        # Generar exportación
        if export_format == 'excel':
            export = export_service.export_to_excel(
                report_request=report_request,
                user=request.user,
                empresa=empresa,
                chat_message=chat_message
            )
        else:  # pdf
            export = export_service.export_to_pdf(
                report_request=report_request,
                user=request.user,
                empresa=empresa,
                chat_message=chat_message
            )
        
        return JsonResponse({
            'success': True,
            'export_id': str(export.export_id),
            'filename': export.filename,
            'file_size': export.file_size,
            'format': export.format,
            'download_url': export_service.get_download_url(export),
            'message': f'Reporte exportado a {export.get_format_display()} exitosamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def download_export(request, export_id):
    """
    Descarga un archivo exportado
    
    GET /api/export/download/<export_id>/
    """
    try:
        export = get_object_or_404(
            ReportExport,
            export_id=export_id,
            user=request.user
        )
        
        # Verificar que el archivo existe
        if not export.file or not os.path.exists(export.file.path):
            raise Http404("Archivo no encontrado")
        
        # Marcar como descargado
        export.mark_downloaded()
        
        # Retornar archivo
        response = FileResponse(
            open(export.file.path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{export.filename}"'
        
        return response
    
    except Http404:
        return JsonResponse({
            'success': False,
            'error': 'Exportación no encontrada'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def export_status(request, export_id):
    """
    Obtiene información de una exportación
    
    GET /api/export/status/<export_id>/
    """
    try:
        export = get_object_or_404(
            ReportExport,
            export_id=export_id,
            user=request.user
        )
        
        return JsonResponse({
            'success': True,
            'export': {
                'export_id': str(export.export_id),
                'filename': export.filename,
                'format': export.format,
                'file_size': export.file_size,
                'template_used': export.template_used,
                'generated_at': export.generated_at.isoformat(),
                'downloaded_at': export.downloaded_at.isoformat() if export.downloaded_at else None,
                'download_count': export.download_count,
                'download_url': export_service.get_download_url(export)
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)


@login_required
def list_user_exports(request):
    """
    Lista las exportaciones del usuario
    
    GET /api/export/list/
    Query params:
        - limit: int (default: 20)
        - format: excel|pdf|csv (opcional)
    """
    try:
        limit = int(request.GET.get('limit', 20))
        export_format = request.GET.get('format')
        
        exports = ReportExport.objects.filter(user=request.user)
        
        if export_format:
            exports = exports.filter(format=export_format)
        
        exports = exports.order_by('-generated_at')[:limit]
        
        exports_data = [{
            'export_id': str(exp.export_id),
            'filename': exp.filename,
            'format': exp.format,
            'file_size': exp.file_size,
            'generated_at': exp.generated_at.isoformat(),
            'download_count': exp.download_count,
            'report_query': exp.report_request.query if exp.report_request else None
        } for exp in exports]
        
        return JsonResponse({
            'success': True,
            'exports': exports_data,
            'total': len(exports_data)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

