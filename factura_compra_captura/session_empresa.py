"""
Resolución de la empresa Synap activa desde la sesión administraNET.

Debe ser idéntica en API (creación de expediente) y vistas web (listado, documento).
Prioridad: ``empresa_activa_id`` en sesión; si no, ``session['user']['id_empresa']``.
"""


def empresa_synap_id_desde_sesion(request) -> int | None:
    if not request or not getattr(request, "session", None):
        return None
    raw = request.session.get("empresa_activa_id")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    session_user = request.session.get("user") or {}
    id_emp = session_user.get("id_empresa")
    if id_emp is not None:
        try:
            return int(id_emp)
        except (TypeError, ValueError):
            return None
    return None
