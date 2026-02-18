"""Auth: login stub, usuario actual."""
from django.urls import path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model, login, authenticate

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Stub de login: acepta username/password y crea sesión. Sin JWT por defecto."""
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response(
            {"code": "VALIDATION_ERROR", "message": "username y password requeridos", "details": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"code": "UNAUTHORIZED", "message": "Credenciales inválidas", "details": []},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    login(request, user)
    role = "agent"
    if hasattr(user, "agent_profile"):
        role = user.agent_profile.role
    return Response({
        "user": {
            "id": user.pk,
            "username": user.username,
            "email": getattr(user, "email", "") or "",
            "role": role,
        },
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def current_user(request):
    """Usuario actual y rol. Devuelve 401 si no hay sesión (frontend muestra login)."""
    if not request.user.is_authenticated:
        return Response(
            {"detail": "No autenticado."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    user = request.user
    role = "agent"
    if hasattr(user, "agent_profile"):
        role = user.agent_profile.role
    return Response({
        "user": {
            "id": user.pk,
            "username": user.username,
            "email": getattr(user, "email", "") or "",
            "role": role,
        },
    })


urlpatterns = [
    path("auth/login/", login_view),
    path("auth/me/", current_user),
]
