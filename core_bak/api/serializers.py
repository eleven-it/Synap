from rest_framework import serializers
from core.models import Permiso, Rol, UsuarioExtendido

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

class UsuarioDetalleSerializer(serializers.ModelSerializer):
    roles = RolSerializer(many=True, read_only=True)
    permisos_directos = PermisoSerializer(many=True, read_only=True, source='permisos_extra')

    class Meta:
        model = UsuarioExtendido
        fields = ['id', 'email', 'nombre', 'nombre_completo', 'roles', 'permisos_directos']
        read_only_fields = ['nombre_completo'] 