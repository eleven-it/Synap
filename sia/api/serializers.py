"""
Serializers para el módulo Strategic Insights & Alignment (SIA)
"""
from rest_framework import serializers
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
from core.models import Empresa, UsuarioExtendido


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer para Department."""
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    
    class Meta:
        model = Department
        fields = [
            'id', 'empresa', 'empresa_nombre', 'name', 'code', 
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EvaluationCycleSerializer(serializers.ModelSerializer):
    """Serializer para EvaluationCycle."""
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre_completo', read_only=True)
    response_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EvaluationCycle
        fields = [
            'id', 'empresa', 'empresa_nombre', 'name', 'description',
            'start_date', 'end_date', 'is_active', 'created_by', 
            'created_by_nombre', 'response_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def get_response_count(self, obj):
        """Retorna el número de respuestas en este ciclo."""
        return obj.survey_responses.filter(status='submitted').count()


class FodaItemSerializer(serializers.ModelSerializer):
    """Serializer para FodaItem."""
    quadrant_display = serializers.CharField(source='get_quadrant_display', read_only=True)
    
    class Meta:
        model = FodaItem
        fields = [
            'id', 'survey_response', 'quadrant', 'quadrant_display',
            'description', 'priority', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class RatingSerializer(serializers.ModelSerializer):
    """Serializer para Rating."""
    dimension_display = serializers.CharField(source='get_dimension_display', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'survey_response', 'dimension', 'dimension_display',
            'value', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class OpenAnswerSerializer(serializers.ModelSerializer):
    """Serializer para OpenAnswer."""
    question_type_display = serializers.CharField(source='get_question_type_display', read_only=True)
    
    class Meta:
        model = OpenAnswer
        fields = [
            'id', 'survey_response', 'question_type', 'question_type_display',
            'question_text', 'answer', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class StrategicSurveyResponseSerializer(serializers.ModelSerializer):
    """Serializer para StrategicSurveyResponse con datos anidados."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_nombre = serializers.CharField(source='user.nombre_completo', read_only=True)
    evaluation_cycle_name = serializers.CharField(source='evaluation_cycle.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Datos anidados
    foda_items = FodaItemSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    open_answers = OpenAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = StrategicSurveyResponse
        fields = [
            'id', 'evaluation_cycle', 'evaluation_cycle_name', 'user', 
            'user_email', 'user_nombre', 'department', 'department_name',
            'status', 'status_display', 'submitted_at', 'created_at', 'updated_at',
            'foda_items', 'ratings', 'open_answers'
        ]
        read_only_fields = ['submitted_at', 'created_at', 'updated_at']


class StrategicSurveyResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear una respuesta de encuesta."""
    
    class Meta:
        model = StrategicSurveyResponse
        fields = [
            'evaluation_cycle', 'user', 'department', 'status'
        ]


class CameActionSerializer(serializers.ModelSerializer):
    """Serializer para CameAction."""
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    evaluation_cycle_name = serializers.CharField(source='evaluation_cycle.name', read_only=True)
    assigned_to_email = serializers.CharField(source='assigned_to.email', read_only=True, allow_null=True)
    assigned_to_nombre = serializers.CharField(source='assigned_to.nombre_completo', read_only=True, allow_null=True)
    created_by_nombre = serializers.CharField(source='created_by.nombre_completo', read_only=True, allow_null=True)
    
    class Meta:
        model = CameAction
        fields = [
            'id', 'evaluation_cycle', 'evaluation_cycle_name', 'action_type', 
            'action_type_display', 'title', 'description', 'related_foda_item',
            'priority', 'status', 'status_display', 'assigned_to', 
            'assigned_to_email', 'assigned_to_nombre', 'due_date', 
            'completed_at', 'created_by', 'created_by_nombre', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['completed_at', 'created_at', 'updated_at', 'created_by']


# Serializers para consolidación y dashboards
class ConsolidatedFodaSerializer(serializers.Serializer):
    """Serializer para FODA consolidado."""
    quadrant = serializers.CharField()
    items = serializers.ListField(
        child=serializers.DictField(),
        help_text=_('Lista de ítems con description y count')
    )


class ConsolidatedRatingsSerializer(serializers.Serializer):
    """Serializer para ratings consolidados."""
    dimension = serializers.CharField()
    dimension_display = serializers.CharField()
    average = serializers.FloatField()
    min_value = serializers.IntegerField()
    max_value = serializers.IntegerField()
    std_dev = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()













