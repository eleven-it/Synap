from rest_framework import serializers
from core.models import Permiso, Rol, UsuarioExtendido, Branch

class PermisoSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Permiso.
    """
    class Meta:
        model = Permiso
        fields = ['id', 'nombre', 'codigo']

class RolSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Rol, incluye los permisos anidados.
    """
    permisos = PermisoSerializer(many=True, read_only=True)

    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion', 'permisos']

class BranchSerializer(serializers.ModelSerializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', read_only=True)
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'code', 'empresa_id', 'active',
            'address', 'city', 'state', 'country', 'phone', 'email'
        ]

class UsuarioDetalleSerializer(serializers.ModelSerializer):
    roles = RolSerializer(many=True, read_only=True)
    permisos_directos = PermisoSerializer(many=True, read_only=True, source='permisos_extra')
    branches = BranchSerializer(many=True, read_only=True)
    default_branch_id = serializers.PrimaryKeyRelatedField(source='default_branch', queryset=Branch.objects.all(), allow_null=True, required=False)

    class Meta:
        model = UsuarioExtendido
        fields = [
            'id', 'email', 'nombre', 'nombre_completo',
            'roles', 'permisos_directos',
            'branches', 'default_branch_id'
        ]
        read_only_fields = ['nombre_completo'] 