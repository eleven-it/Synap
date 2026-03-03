"""
Session store acotado para Principal (paridad con VB6).
Fuente de verdad: request.session["user"]. No exponer id_sesion en JSON ni en barra de estado.
"""
from typing import Optional, Dict, Any


def get_session_work_context(request) -> Dict[str, Any]:
    """
    Devuelve el contexto de trabajo del usuario desde la sesión (para uso en vistas, APIs y barra de estado).
    Incluye solo lo necesario; no expone id_sesion ni base_empresa en respuestas frontend (seguridad).
    """
    if not request or not getattr(request, "session", None):
        return {}

    user_data = request.session.get("user") or {}
    if not user_data:
        return {}

    # Nombres para mostrar (barra de estado, etc.); no incluir id_sesion ni base_empresa en salidas públicas
    return {
        "id_usuario": user_data.get("id_usuario"),
        "cod_usuario": user_data.get("cod_usuario"),
        "nombre_usuario": user_data.get("nombre_usuario"),
        "apellido_usuario": user_data.get("apellido_usuario"),
        "nombre_completo": user_data.get("nombre_completo") or "",
        "id_empresa": user_data.get("id_empresa"),
        "id_sucursal": user_data.get("id_sucursal"),
        "id_puesto": user_data.get("id_puesto"),
        "nombre_puesto": user_data.get("nombre_puesto") or "",
        "base_empresa": user_data.get("base_empresa"),  # solo uso interno en servidor
        # Opcionales TPV/cajero (cuando exista auth-cashier)
        "id_vendedor_usr": user_data.get("id_vendedor_usr"),
        "id_caja": user_data.get("id_caja"),
        "id_punto_venta": user_data.get("id_punto_venta"),
        "nombre_cajero": user_data.get("nombre_cajero"),
    }
