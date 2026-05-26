"""
Resolución de request.user para ForeignKeys hacia AUTH_USER_MODEL (UsuarioExtendido).

En sesión AdministraNET, el middleware expone AdministraNETUser (no es instancia de
UsuarioExtendido): no debe asignarse a FK de Django.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import UsuarioExtendido


def usuario_extendido_para_fk(user) -> "UsuarioExtendido | None":
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    from core.models import UsuarioExtendido

    return user if isinstance(user, UsuarioExtendido) else None
