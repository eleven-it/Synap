"""
Permisos y mixins para el módulo Strategic Insights & Alignment (SIA)
"""
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.models import Empresa


# Códigos de permisos para SIA
SIA_PERMISSIONS = {
    'can_manage_cycles': 'sia.manage_cycles',
    'can_view_company_dashboard': 'sia.view_company_dashboard',
    'can_view_own_responses': 'sia.view_own_responses',
    'can_create_response': 'sia.create_response',
    'can_view_all_responses': 'sia.view_all_responses',  # Para roles administrativos
}


def get_user_empresa(request):
    """
    Helper centralizado para obtener la empresa del usuario/sesión.
    
    Prioridad:
    1. request.session['user']['base_empresa'] -> buscar empresa Django por nombre/CUIT
    2. request.user.base_empresa (AdministraNETUser) -> buscar empresa Django
    3. request.session['user']['id_empresa'] -> buscar empresa Django
    4. request.user.empresa_activa (UsuarioExtendido)
    5. None
    
    Args:
        request: HttpRequest object
    
    Returns:
        Empresa object or None
    """
    base_empresa = None
    id_empresa = None
    
    # Obtener base_empresa desde sesión o usuario
    if hasattr(request, 'session') and request.session:
        session_user = request.session.get('user', {})
        base_empresa = session_user.get('base_empresa')
        id_empresa = session_user.get('id_empresa')
    
    # Si no está en sesión, intentar desde el usuario
    if not base_empresa and hasattr(request, 'user') and request.user:
        base_empresa = getattr(request.user, 'base_empresa', None)
        id_empresa = getattr(request.user, 'id_empresa', None)
    
    # Si tenemos base_empresa, buscar empresa Django usando el mismo método que context_processors
    if base_empresa:
        try:
            from core.services.administranet_empresas import AdministraNETEmpresaService
            empresa_service = AdministraNETEmpresaService()
            empresa_data = empresa_service.obtener_empresa(base_empresa)
            
            if empresa_data:
                # Buscar empresa Django por nombre o identificador fiscal
                nombre_empresa = empresa_data.get('Nombre', '')
                cuit_empresa = empresa_data.get('CUIT', '').replace('-', '').replace(' ', '')
                
                # Primero intentar por CUIT (más confiable)
                if cuit_empresa:
                    try:
                        empresa_django = Empresa.objects.filter(
                            identificador_fiscal__icontains=cuit_empresa,
                            activa=True
                        ).first()
                        if empresa_django:
                            return empresa_django
                        
                        # Intentar con formato con guiones
                        if len(cuit_empresa) == 11:
                            cuit_formateado = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}"
                            empresa_django = Empresa.objects.filter(
                                identificador_fiscal__icontains=cuit_formateado,
                                activa=True
                            ).first()
                            if empresa_django:
                                return empresa_django
                    except Exception:
                        pass
                
                # Si no se encontró por CUIT, intentar por nombre
                if nombre_empresa:
                    try:
                        empresa_django = Empresa.objects.filter(
                            nombre__iexact=nombre_empresa,
                            activa=True
                        ).first()
                        if empresa_django:
                            return empresa_django
                        
                        # Intentar búsqueda parcial
                        empresa_django = Empresa.objects.filter(
                            nombre__icontains=nombre_empresa,
                            activa=True
                        ).first()
                        if empresa_django:
                            return empresa_django
                    except Exception:
                        pass
        except Exception:
            pass
    
    # Intentar por id_empresa directamente (si existe campo de mapeo)
    if id_empresa:
        try:
            # Intentar buscar por ID directamente (asumiendo que puede haber coincidencia)
            empresa = Empresa.objects.filter(id=id_empresa, activa=True).first()
            if empresa:
                return empresa
        except Exception:
            pass
    
    # Fallback: buscar empresa_id en sesión (compatibilidad)
    if hasattr(request, 'session') and request.session:
        empresa_id = request.session.get('empresa_id')
        if empresa_id:
            try:
                return Empresa.objects.get(id=empresa_id, activa=True)
            except Empresa.DoesNotExist:
                pass
    
    # Último recurso: empresa_activa del usuario
    if hasattr(request, 'user') and request.user and hasattr(request.user, 'empresa_activa'):
        empresa = getattr(request.user, 'empresa_activa', None)
        if empresa:
            return empresa
    
    return None


def has_sia_permission(user, permission_code):
    """
    Verifica si el usuario tiene un permiso específico de SIA.
    
    Args:
        user: Usuario autenticado
        permission_code: Código del permiso (ej: 'sia.manage_cycles')
    
    Returns:
        bool: True si tiene el permiso, False en caso contrario
    """
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    
    # Administradores tienen acceso total
    if hasattr(user, 'is_admin') and user.is_admin():
        return True
    
    # Verificar permiso específico
    if hasattr(user, 'tiene_permiso'):
        return user.tiene_permiso(permission_code) or user.tiene_permiso('*')
    
    return False


class SiaPermissionRequiredMixin:
    """
    Mixin para verificar permisos específicos de SIA.
    Combina autenticación, verificación de permisos y filtrado por empresa.
    """
    permission_required = None  # Código del permiso requerido (ej: 'sia.manage_cycles')
    require_empresa = True  # Si True, requiere que el usuario tenga una empresa asociada
    
    def dispatch(self, request, *args, **kwargs):
        """Verifica permisos y empresa antes de procesar la vista"""
        # Verificar autenticación básica
        if not request.user.is_authenticated:
            messages.error(request, _("Debes iniciar sesión para acceder a esta página."))
            return redirect('login:login')
        
        # Verificar sesión de administraNET
        if "user" not in request.session:
            messages.error(request, _("Sesión no válida. Por favor, inicia sesión nuevamente."))
            return redirect("login:login")
        
        # Verificar permisos PRIMERO (antes de verificar empresa)
        if self.permission_required:
            if not has_sia_permission(request.user, self.permission_required):
                messages.error(request, _("No tienes permisos para acceder a esta página."))
                raise PermissionDenied
        
        # Verificar empresa si es requerida (después de permisos)
        if self.require_empresa:
            empresa = get_user_empresa(request)
            if not empresa:
                # Si no encontramos empresa Django pero tenemos base_empresa en sesión,
                # permitir acceso (los permisos ya fueron verificados arriba)
                session_user = request.session.get('user', {})
                base_empresa = session_user.get('base_empresa') or getattr(request.user, 'base_empresa', None)
                
                if base_empresa:
                    # Log warning pero permitir acceso (la empresa se puede crear/mapear después)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Usuario {getattr(request.user, 'cod_usuario', 'unknown')} tiene permisos "
                        f"pero no se encontró empresa Django para base_empresa={base_empresa}. "
                        f"Permitiendo acceso basado en permisos verificados."
                    )
                    # Continuar sin empresa Django
                else:
                    # No hay base_empresa ni empresa Django - esto es un error real
                    messages.error(request, _("No se pudo determinar la empresa asociada. Por favor, contacta al administrador."))
                    raise PermissionDenied
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_empresa(self):
        """Obtiene la empresa del usuario/sesión"""
        return get_user_empresa(self.request)


class SiaEmpresaFilterMixin:
    """
    Mixin para filtrar querysets por empresa automáticamente.
    """
    empresa_field = 'empresa'  # Nombre del campo ForeignKey a Empresa
    
    def get_queryset(self):
        """Filtra el queryset por empresa del usuario"""
        queryset = super().get_queryset()
        empresa = get_user_empresa(self.request)
        
        if empresa:
            # Filtrar por empresa
            filter_kwargs = {self.empresa_field: empresa}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset


class SiaResponseVisibilityMixin:
    """
    Mixin para controlar la visibilidad de respuestas individuales.
    
    Reglas:
    - Cada usuario puede ver SOLO sus propias respuestas
    - Usuarios con 'sia.view_all_responses' pueden ver todas las respuestas de su empresa
    """
    def get_queryset(self):
        """Filtra respuestas según las reglas de visibilidad"""
        queryset = super().get_queryset()
        empresa = get_user_empresa(self.request)
        
        if not empresa:
            return queryset.none()
        
        # Filtrar por empresa primero
        queryset = queryset.filter(evaluation_cycle__empresa=empresa)
        
        # Si el usuario NO tiene permiso para ver todas las respuestas,
        # solo puede ver las suyas
        if not has_sia_permission(self.request.user, SIA_PERMISSIONS['can_view_all_responses']):
            queryset = queryset.filter(user=self.request.user)
        
        return queryset

