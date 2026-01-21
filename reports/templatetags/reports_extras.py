"""
Template tags personalizados para el módulo de reportes.
"""
from django import template
from ..permissions import BuilderReportsPermission

register = template.Library()


@register.filter
def has_builder_permission(user):
    """Verifica si el usuario tiene permiso de builder."""
    if not user:
        return False
    permission = BuilderReportsPermission()
    # Crear un request mock para usar has_permission
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    class MockView:
        pass
    
    mock_request = MockRequest(user)
    mock_view = MockView()
    return permission.has_permission(mock_request, mock_view)











