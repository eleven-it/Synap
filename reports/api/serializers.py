from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Empresa, Branch, UsuarioExtendido
from .models import Report, ReportTemplate, ReportComponent, ReportSchedule, ReportExport

User = get_user_model()


class EmpresaSerializer(serializers.ModelSerializer):
    """Serializador para Empresa"""
    
    class Meta:
        model = Empresa
        fields = ['id', 'nombre', 'cuit', 'email', 'telefono', 'direccion']


class BranchSerializer(serializers.ModelSerializer):
    """Serializador para Branch"""
    
    class Meta:
        model = Branch
        fields = ['id', 'name', 'address', 'phone', 'email']


class UsuarioExtendidoSerializer(serializers.ModelSerializer):
    """Serializador para UsuarioExtendido"""
    
    class Meta:
        model = UsuarioExtendido
        fields = ['id', 'nombre', 'email', 'uid']


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializador para ReportTemplate"""
    
    empresa = EmpresaSerializer(read_only=True)
    created_by = UsuarioExtendidoSerializer(read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'configuration',
            'is_active', 'created_at', 'updated_at', 'empresa', 'created_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'empresa', 'created_by']


class ReportComponentSerializer(serializers.ModelSerializer):
    """Serializador para ReportComponent"""
    
    class Meta:
        model = ReportComponent
        fields = [
            'id', 'name', 'component_type', 'configuration', 'position',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializador para ReportSchedule"""
    
    report = serializers.PrimaryKeyRelatedField(queryset=Report.objects.all())
    branch = BranchSerializer(read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = [
            'id', 'report', 'schedule_type', 'frequency', 'next_run',
            'is_active', 'created_at', 'updated_at', 'branch'
        ]
        read_only_fields = ['created_at', 'updated_at', 'next_run']


class ReportExportSerializer(serializers.ModelSerializer):
    """Serializador para ReportExport"""
    
    report = serializers.PrimaryKeyRelatedField(queryset=Report.objects.all())
    branch = BranchSerializer(read_only=True)
    
    class Meta:
        model = ReportExport
        fields = [
            'id', 'report', 'export_type', 'file_path', 'file_size',
            'export_date', 'status', 'created_at', 'branch'
        ]
        read_only_fields = ['created_at', 'export_date']


class ReportSerializer(serializers.ModelSerializer):
    """Serializador para Report"""
    
    empresa = EmpresaSerializer(read_only=True)
    created_by = UsuarioExtendidoSerializer(read_only=True)
    template = ReportTemplateSerializer(read_only=True)
    components = ReportComponentSerializer(many=True, read_only=True)
    schedules = ReportScheduleSerializer(many=True, read_only=True)
    exports = ReportExportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'configuration',
            'is_active', 'created_at', 'updated_at', 'empresa', 'created_by',
            'template', 'components', 'schedules', 'exports'
        ]
        read_only_fields = ['created_at', 'updated_at', 'empresa', 'created_by']


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear Report"""
    
    class Meta:
        model = Report
        fields = [
            'name', 'description', 'report_type', 'configuration',
            'template', 'is_active'
        ]


class ReportUpdateSerializer(serializers.ModelSerializer):
    """Serializador para actualizar Report"""
    
    class Meta:
        model = Report
        fields = [
            'name', 'description', 'report_type', 'configuration',
            'template', 'is_active'
        ]


class ReportDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para Report"""
    
    empresa = EmpresaSerializer(read_only=True)
    created_by = UsuarioExtendidoSerializer(read_only=True)
    template = ReportTemplateSerializer(read_only=True)
    components = ReportComponentSerializer(many=True, read_only=True)
    schedules = ReportScheduleSerializer(many=True, read_only=True)
    exports = ReportExportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'name', 'description', 'report_type', 'configuration',
            'is_active', 'created_at', 'updated_at', 'empresa', 'created_by',
            'template', 'components', 'schedules', 'exports'
        ]
        read_only_fields = ['created_at', 'updated_at', 'empresa', 'created_by'] 