"""
Utilidades de autenticación para el microservicio de IA
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from jose import JWTError, jwt
except ImportError:
    JWTError = None
    jwt = None

from config import settings

logger = logging.getLogger(__name__)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verificar token JWT"""
    try:
        if jwt is None:
            logger.warning("PyJWT no disponible, usando verificación simulada")
            return _simulate_token_verification(token)
        
        # Decodificar token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verificar expiración
        exp = payload.get("exp")
        if exp is None:
            raise JWTError("Token sin expiración")
        
        if datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise JWTError("Token expirado")
        
        # Extraer información del usuario
        user_data = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "company_id": payload.get("company_id"),
            "branch_id": payload.get("branch_id")
        }
        
        logger.info(f"Token verificado para usuario: {user_data.get('email')}")
        return user_data
        
    except JWTError as e:
        logger.error(f"Error verificando token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado verificando token: {e}")
        return None

def _simulate_token_verification(token: str) -> Dict[str, Any]:
    """Simular verificación de token para desarrollo"""
    return {
        "user_id": "simulated_user_id",
        "email": "user@example.com",
        "roles": ["user"],
        "permissions": ["reports.view", "reports.create"],
        "company_id": "simulated_company_id",
        "branch_id": "simulated_branch_id"
    }

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Crear token de acceso"""
    try:
        if jwt is None:
            logger.warning("PyJWT no disponible, no se puede crear token")
            return ""
        
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creando token: {e}")
        return ""

def has_permission(user_data: Dict[str, Any], required_permission: str) -> bool:
    """Verificar si el usuario tiene un permiso específico"""
    if not user_data:
        return False
    
    permissions = user_data.get("permissions", [])
    roles = user_data.get("roles", [])
    
    # Verificar permiso directo
    if required_permission in permissions:
        return True
    
    # Verificar permisos de administrador
    if "administrador" in roles or "*" in permissions:
        return True
    
    # Verificar permisos de módulo
    module_permission = f"{required_permission.split('.')[0]}.*"
    if module_permission in permissions:
        return True
    
    return False

def has_role(user_data: Dict[str, Any], required_role: str) -> bool:
    """Verificar si el usuario tiene un rol específico"""
    if not user_data:
        return False
    
    roles = user_data.get("roles", [])
    return required_role in roles

def get_user_context(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Obtener contexto del usuario para uso en IA"""
    return {
        "user_id": user_data.get("user_id"),
        "email": user_data.get("email"),
        "roles": user_data.get("roles", []),
        "company_id": user_data.get("company_id"),
        "branch_id": user_data.get("branch_id"),
        "permissions": user_data.get("permissions", [])
    } 