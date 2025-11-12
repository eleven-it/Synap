"""
API para gestión del Catálogo Funcional
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from reports_ai.services.vb6_files_service import VB6FilesService

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@login_required
def get_vb6_forms(request):
    """
    Obtiene lista de formularios VB6 disponibles
    
    GET /reports-ai/api/catalog/vb6-forms/
    
    Query params:
        - category: filtrar por categoría (opcional)
        - q: búsqueda (opcional)
    """
    try:
        service = VB6FilesService()
        category = request.GET.get('category')
        search_query = request.GET.get('q', '').lower()
        
        if category:
            # Obtener por categoría
            forms_by_category = service.get_forms_by_category()
            forms = forms_by_category.get(category, [])
        else:
            # Obtener todos
            forms = service.get_vb6_forms()
        
        # Aplicar búsqueda si existe
        if search_query:
            forms = [f for f in forms if search_query in f.lower()]
        
        # Limitar a 50 resultados
        forms = forms[:50]
        
        return JsonResponse({
            'success': True,
            'count': len(forms),
            'forms': forms
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo formularios VB6: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_vb6_forms_grouped(request):
    """
    Obtiene formularios agrupados por categoría
    
    GET /reports-ai/api/catalog/vb6-forms-grouped/
    """
    try:
        service = VB6FilesService()
        grouped = service.get_forms_by_category()
        
        return JsonResponse({
            'success': True,
            'categories': grouped
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo formularios agrupados: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_vb6_modules(request):
    """
    Obtiene lista de módulos VB6 (.bas, .cls)
    
    GET /reports-ai/api/catalog/vb6-modules/
    """
    try:
        service = VB6FilesService()
        search_query = request.GET.get('q', '').lower()
        
        modules = service.get_vb6_modules()
        
        # Aplicar búsqueda
        if search_query:
            modules = [m for m in modules if search_query in m.lower()]
        
        modules = modules[:50]
        
        return JsonResponse({
            'success': True,
            'count': len(modules),
            'modules': modules
        })
    
    except Exception as e:
        logger.error(f"Error obteniendo módulos VB6: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_entities_suggestions(request):
    """
    Obtiene lista de entidades comunes sugeridas
    
    GET /reports-ai/api/catalog/entities/
    """
    try:
        service = VB6FilesService()
        entities = service.get_common_entities()
        
        search_query = request.GET.get('q', '').lower()
        
        if search_query:
            entities = [e for e in entities if search_query in e.lower()]
        
        return JsonResponse({
            'success': True,
            'count': len(entities),
            'entities': entities
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_tables_from_schema(request):
    """
    Obtiene lista de tablas desde el schema MySQL de administraNET
    
    GET /reports-ai/api/catalog/tables/
    """
    try:
        # Import solo cuando se necesita
        from administraNET_integration.services.administranet_connection import AdministraNETConnectionService
        import mysql.connector
        
        search_query = request.GET.get('q', '').lower()
        
        # Conectar a MySQL
        connection_service = AdministraNETConnectionService()
        conn = mysql.connector.connect(**connection_service.get_connection_params())
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SHOW TABLES")
            
            tables = [list(row.values())[0] for row in cursor.fetchall()]
            
            # Aplicar búsqueda
            if search_query:
                tables = [t for t in tables if search_query in t.lower()]
            
            tables = sorted(tables)[:50]
            
            return JsonResponse({
                'success': True,
                'count': len(tables),
                'tables': tables
            })
        
        finally:
            cursor.close()
            conn.close()
    
    except Exception as e:
        logger.error(f"Error obteniendo tablas: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

