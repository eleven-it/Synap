"""
API Views para el módulo Strategic Insights & Alignment (SIA)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Min, Max, Count, StdDev, Q
from django.utils.translation import gettext_lazy as _
from sia.models import (
    Department,
    EvaluationCycle,
    StrategicSurveyResponse,
    FodaItem,
    Rating,
    OpenAnswer,
    CameAction,
)
from sia.api.serializers import (
    DepartmentSerializer,
    EvaluationCycleSerializer,
    StrategicSurveyResponseSerializer,
    StrategicSurveyResponseCreateSerializer,
    FodaItemSerializer,
    RatingSerializer,
    OpenAnswerSerializer,
    CameActionSerializer,
    ConsolidatedFodaSerializer,
    ConsolidatedRatingsSerializer,
)
from core.models import Empresa
from sia.services import DashboardDataService
from sia.permissions import get_user_empresa, has_sia_permission, SIA_PERMISSIONS
from rest_framework.views import APIView


class DepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet para Department."""
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Department.objects.all()
        empresa = get_user_empresa(self.request)
        
        # Filtrar por empresa del usuario (ignorar empresa_id del query si no tiene permisos globales)
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        else:
            # Si no hay empresa, no mostrar nada
            queryset = queryset.none()
        
        return queryset.select_related('empresa')


class EvaluationCycleViewSet(viewsets.ModelViewSet):
    """ViewSet para EvaluationCycle."""
    serializer_class = EvaluationCycleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = EvaluationCycle.objects.all()
        empresa = get_user_empresa(self.request)
        is_active = self.request.query_params.get('is_active', None)
        
        # Filtrar por empresa del usuario (ignorar empresa_id del query si no tiene permisos globales)
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        else:
            # Si no hay empresa, no mostrar nada
            queryset = queryset.none()
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.select_related('empresa', 'created_by').prefetch_related('survey_responses')
    
    @action(detail=True, methods=['get'])
    def consolidated_data(self, request, pk=None):
        """Retorna datos consolidados del ciclo de evaluación."""
        cycle = self.get_object()
        
        # FODA consolidado
        foda_data = {}
        for quadrant in ['strength', 'weakness', 'opportunity', 'threat']:
            items = FodaItem.objects.filter(
                survey_response__evaluation_cycle=cycle,
                survey_response__status='submitted',
                quadrant=quadrant
            ).values('description').annotate(
                count=Count('id')
            ).order_by('-count')[:10]  # Top 10 más mencionados
            
            foda_data[quadrant] = list(items)
        
        # Ratings consolidados
        ratings_data = Rating.objects.filter(
            survey_response__evaluation_cycle=cycle,
            survey_response__status='submitted'
        ).values('dimension').annotate(
            average=Avg('value'),
            min_value=Min('value'),
            max_value=Max('value'),
            std_dev=StdDev('value'),
            count=Count('id')
        )
        
        return Response({
            'foda': foda_data,
            'ratings': list(ratings_data)
        })


class StrategicSurveyResponseViewSet(viewsets.ModelViewSet):
    """ViewSet para StrategicSurveyResponse."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StrategicSurveyResponseCreateSerializer
        return StrategicSurveyResponseSerializer
    
    def get_queryset(self):
        queryset = StrategicSurveyResponse.objects.all()
        empresa = get_user_empresa(self.request)
        cycle_id = self.request.query_params.get('cycle', None)
        user_id = self.request.query_params.get('user', None)
        status_filter = self.request.query_params.get('status', None)
        
        # Filtrar por empresa primero
        if empresa:
            queryset = queryset.filter(evaluation_cycle__empresa=empresa)
        else:
            queryset = queryset.none()
        
        # Reglas de visibilidad: usuarios normales solo ven sus propias respuestas
        if not has_sia_permission(self.request.user, SIA_PERMISSIONS['can_view_all_responses']):
            queryset = queryset.filter(user=self.request.user)
        
        if cycle_id:
            queryset = queryset.filter(evaluation_cycle_id=cycle_id)
        if user_id and has_sia_permission(self.request.user, SIA_PERMISSIONS['can_view_all_responses']):
            # Solo permitir filtrar por usuario si tiene permiso para ver todas
            queryset = queryset.filter(user_id=user_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related(
            'evaluation_cycle', 'user', 'department'
        ).prefetch_related('foda_items', 'ratings', 'open_answers')
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Marca una respuesta como enviada."""
        response = self.get_object()
        if response.status == 'draft':
            response.status = 'submitted'
            response.save()
            return Response({'status': 'submitted'}, status=status.HTTP_200_OK)
        return Response(
            {'error': _('Response already submitted')}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class FodaItemViewSet(viewsets.ModelViewSet):
    """ViewSet para FodaItem."""
    serializer_class = FodaItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = FodaItem.objects.all()
        response_id = self.request.query_params.get('response', None)
        quadrant = self.request.query_params.get('quadrant', None)
        
        if response_id:
            queryset = queryset.filter(survey_response_id=response_id)
        if quadrant:
            queryset = queryset.filter(quadrant=quadrant)
        
        return queryset.select_related('survey_response')


class RatingViewSet(viewsets.ModelViewSet):
    """ViewSet para Rating."""
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Rating.objects.all()
        response_id = self.request.query_params.get('response', None)
        dimension = self.request.query_params.get('dimension', None)
        
        if response_id:
            queryset = queryset.filter(survey_response_id=response_id)
        if dimension:
            queryset = queryset.filter(dimension=dimension)
        
        return queryset.select_related('survey_response')


class OpenAnswerViewSet(viewsets.ModelViewSet):
    """ViewSet para OpenAnswer."""
    serializer_class = OpenAnswerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = OpenAnswer.objects.all()
        response_id = self.request.query_params.get('response', None)
        question_type = self.request.query_params.get('question_type', None)
        
        if response_id:
            queryset = queryset.filter(survey_response_id=response_id)
        if question_type:
            queryset = queryset.filter(question_type=question_type)
        
        return queryset.select_related('survey_response')


class CameActionViewSet(viewsets.ModelViewSet):
    """ViewSet para CameAction."""
    serializer_class = CameActionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = CameAction.objects.all()
        cycle_id = self.request.query_params.get('cycle', None)
        action_type = self.request.query_params.get('action_type', None)
        status_filter = self.request.query_params.get('status', None)
        assigned_to = self.request.query_params.get('assigned_to', None)
        
        if cycle_id:
            queryset = queryset.filter(evaluation_cycle_id=cycle_id)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        return queryset.select_related(
            'evaluation_cycle', 'assigned_to', 'created_by', 'related_foda_item'
        )


class DashboardDataAPIView(APIView):
    """
    API endpoint para obtener datos consolidados del dashboard SIA.
    
    Parámetros GET:
        - empresa_id: ID de la empresa (ignorado si el usuario no tiene permisos globales)
        - cycle_id: ID del ciclo de evaluación (opcional, usa el más reciente si no se especifica)
    
    Retorna JSON con:
        - ratings: lista de estadísticas por dimensión
        - foda: dict con items por cuadrante
        - total_responses: número total de respuestas
        - cycle_info: información del ciclo seleccionado
    
    Requiere permiso: sia.view_company_dashboard
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Verificar permiso para ver dashboard consolidado
        if not has_sia_permission(request.user, SIA_PERMISSIONS['can_view_company_dashboard']):
            return Response(
                {'detail': 'No tienes permisos para ver el dashboard consolidado.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener empresa del usuario/sesión
        empresa = get_user_empresa(request)
        if not empresa:
            return Response(
                {'detail': 'No se pudo determinar la empresa asociada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Solo permitir especificar empresa_id si el usuario tiene permisos globales (admin)
        empresa_id = None
        if hasattr(request.user, 'is_admin') and request.user.is_admin():
            empresa_id_param = request.query_params.get('empresa_id', None)
            if empresa_id_param:
                try:
                    empresa_id = int(empresa_id_param)
                    # Verificar que la empresa existe
                    try:
                        Empresa.objects.get(id=empresa_id, activa=True)
                    except Empresa.DoesNotExist:
                        return Response(
                            {'detail': 'Empresa no encontrada.'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                except (ValueError, TypeError):
                    empresa_id = None
        
        # Si no se especificó empresa_id o no tiene permisos, usar la del usuario
        if not empresa_id:
            empresa_id = empresa.id
        
        cycle_id = request.query_params.get('cycle_id', None)
        if cycle_id:
            try:
                cycle_id = int(cycle_id)
            except (ValueError, TypeError):
                cycle_id = None
        
        # Obtener datos consolidados usando el servicio
        data = DashboardDataService.get_consolidated_data(
            empresa_id=empresa_id,
            cycle_id=cycle_id
        )
        
        return Response(data, status=status.HTTP_200_OK)

