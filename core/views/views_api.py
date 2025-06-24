from rest_framework import generics, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.models import UsuarioExtendido, Rol, Permiso
from core.api.serializers import UsuarioDetalleSerializer, RolSerializer, PermisoSerializer

class UserDetailApiView(views.APIView):
    """ API para obtener y actualizar detalles de un usuario. """
    def get(self, request, user_id, *args, **kwargs):
        if not request.user.tiene_permiso("usuarios.ver"):
            return Response({"error": "Permiso denegado"}, status=status.HTTP_403_FORBIDDEN)
        usuario = get_object_or_404(UsuarioExtendido, id=user_id)
        serializer = UsuarioDetalleSerializer(usuario)
        return Response(serializer.data)

    def post(self, request, user_id, *args, **kwargs):
        if not request.user.tiene_permiso("usuarios.editar"):
            return Response({"error": "Permiso denegado"}, status=status.HTTP_403_FORBIDDEN)
        usuario = get_object_or_404(UsuarioExtendido, id=user_id)
        
        roles_ids = request.data.get('roles_ids', [])
        permisos_ids = request.data.get('permisos_ids', [])
        
        usuario.roles.set(Rol.objects.filter(id__in=roles_ids))
        usuario.user_permissions.set(Permiso.objects.filter(id__in=permisos_ids))
        
        return Response({'status': 'success'}, status=status.HTTP_200_OK)

class PermissionListApiView(generics.ListAPIView):
    """ API para listar todos los permisos, sin paginación. """
    queryset = Permiso.objects.all().order_by('nombre')
    serializer_class = PermisoSerializer
    pagination_class = None # Desactivamos la paginación para esta vista

    def get(self, request, *args, **kwargs):
        if not request.user.tiene_permiso("usuarios.ver"):
            return Response({"error": "Permiso denegado"}, status=status.HTTP_403_FORBIDDEN)
        return super().get(request, *args, **kwargs)

class RoleDetailApiView(views.APIView):
    """ API para obtener y actualizar un rol. """
    def get(self, request, rol_id, *args, **kwargs):
        if not request.user.tiene_permiso("usuarios.roles.ver"):
            return Response({"error": "Permiso denegado"}, status=status.HTTP_403_FORBIDDEN)
        rol = get_object_or_404(Rol.objects.prefetch_related('permisos'), id=rol_id)
        serializer = RolSerializer(rol)
        return Response(serializer.data)

    def put(self, request, rol_id, *args, **kwargs):
        if not request.user.tiene_permiso("usuarios.roles.editar"):
            return Response({"error": "Permiso denegado"}, status=status.HTTP_403_FORBIDDEN)
        rol = get_object_or_404(Rol, id=rol_id)

        rol.nombre = request.data.get('nombre', rol.nombre)
        rol.descripcion = request.data.get('descripcion', rol.descripcion)
        rol.save()

        if 'permisos_ids' in request.data:
            permisos = Permiso.objects.filter(id__in=request.data['permisos_ids'])
            rol.permisos.set(permisos)
        
        serializer = RolSerializer(rol)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RoleListCreateApiView(generics.ListCreateAPIView):
    """ API para listar y crear roles. """
    queryset = Rol.objects.all().order_by('nombre')
    serializer_class = RolSerializer

    def create(self, request, *args, **kwargs):
        nombre = request.data.get('nombre', '').strip()
        if not nombre:
            return Response({"error": "El nombre es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        
        if Rol.objects.filter(nombre__iexact=nombre).exists():
            return Response({"error": "Ya existe un rol con este nombre."}, status=status.HTTP_400_BAD_REQUEST)

        # Usamos el serializador para crear la instancia del rol (sin permisos aún)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rol = serializer.save()

        # Asignamos los permisos por separado
        if 'permisos_ids' in request.data:
            permisos = Permiso.objects.filter(id__in=request.data['permisos_ids'])
            rol.permisos.set(permisos)
        
        # Devolvemos el objeto completo, incluyendo los permisos
        response_serializer = self.get_serializer(rol)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers) 