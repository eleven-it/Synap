"""
Sistema de Autenticación Unificado con osTicket
Permite a los usuarios usar las mismas credenciales en el chat y osTicket
"""

import logging
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
from .osticket_integration import get_osticket_integration
import json

logger = logging.getLogger(__name__)


class OsTicketAuth:
    """
    Sistema de autenticación unificado con osTicket
    """
    
    def __init__(self):
        self.osticket_integration = get_osticket_integration()
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Autentica un usuario usando las credenciales de osTicket
        
        Args:
            username: Nombre de usuario o email
            password: Contraseña del usuario
            
        Returns:
            Dict con el resultado de la autenticación
        """
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {
                    'success': False,
                    'error': 'No se pudo conectar con osTicket'
                }
            
            cursor = conn.cursor(dictionary=True)
            
            # Buscar usuario por username o email
            user_query = """
                SELECT 
                    u.id,
                    u.org_id,
                    u.status,
                    u.name,
                    ue.address as email,
                    u.created,
                    u.updated
                FROM ost_user u
                JOIN ost_user_email ue ON u.id = ue.user_id
                WHERE ue.address = %s OR u.name = %s
                LIMIT 1
            """
            
            cursor.execute(user_query, (username, username))
            user_data = cursor.fetchone()
            
            if not user_data:
                return {
                    'success': False,
                    'error': 'Usuario no encontrado'
                }
            
            # Verificar contraseña (osTicket usa MD5)
            # Primero intentar con la contraseña hasheada
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            # Buscar en ost_user_account
            account_query = """
                SELECT 
                    user_id,
                    passwd,
                    backend
                FROM ost_user_account 
                WHERE user_id = %s
            """
            
            cursor.execute(account_query, (user_data['id'],))
            account_data = cursor.fetchone()
            
            if not account_data:
                # Usuario sin cuenta de autenticación, crear una
                self._create_user_account(cursor, user_data['id'], password)
                account_data = {
                    'user_id': user_data['id'],
                    'passwd': hashlib.md5(password.encode()).hexdigest(),
                    'backend': 'local'
                }
            
            # Verificar contraseña
            if account_data['passwd'] != hashed_password:
                return {
                    'success': False,
                    'error': 'Contraseña incorrecta'
                }
            
            # Verificar estado del usuario
            if user_data["status"] == 0:  # 1 = Activo
                return {
                    'success': False,
                    'error': 'Usuario inactivo o bloqueado'
                }
            
            # Obtener roles y permisos del usuario
            user_roles = self._get_user_roles(cursor, user_data['id'])
            
            # Crear o actualizar usuario en Django
            django_user = self._sync_user_to_django(user_data, user_roles)
            
            cursor.close()
            
            return {
                'success': True,
                'user': {
                    'id': user_data['id'],
                    'username': user_data['name'],
                    'email': user_data['email'],
                    'full_name': user_data['name'],
                    'org_id': user_data['org_id'],
                    'status': user_data['status'],
                    'roles': user_roles,
                    'django_user_id': django_user.id if django_user else None
                },
                'message': 'Autenticación exitosa'
            }
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_user_account(self, cursor, user_id: int, password: str):
        """Crea una cuenta de autenticación para el usuario"""
        try:
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            insert_query = """
                INSERT INTO ost_user_account (user_id, passwd, backend, registered) VALUES (%s, %s, %s, %s)
                    user_id, passwd, backend, registered
                ) VALUES (%s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                user_id,
                hashed_password,
                'local',
                timezone.now(),
                timezone.now()
            ))
            
            logger.info(f"Cuenta de autenticación creada para usuario {user_id}")
            
        except Exception as e:
            logger.error(f"Error creando cuenta de autenticación: {e}")
    
    def _get_user_roles(self, cursor, user_id: int) -> Dict[str, Any]:
        """Obtiene los roles y permisos del usuario"""
        try:
            # Buscar en ost_staff
            staff_query = """
                SELECT 
                    staff_id,
                    dept_id,
                    role_id,
                    permissions
                FROM ost_staff 
                WHERE user_id = %s
            """
            
            cursor.execute(staff_query, (user_id,))
            staff_data = cursor.fetchone()
            
            if staff_data:
                # Es staff, obtener permisos
                permissions = self._get_staff_permissions(cursor, staff_data['staff_id'])
                
                return {
                    'type': 'staff',
                    'staff_id': staff_data['staff_id'],
                    'dept_id': staff_data['dept_id'],
                    'role_id': staff_data['role_id'],
                    'permissions': permissions
                }
            else:
                # Es usuario regular
                return {
                    'type': 'user',
                    'permissions': ['create_ticket', 'view_own_tickets']
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo roles: {e}")
            return {
                'type': 'user',
                'permissions': ['create_ticket', 'view_own_tickets']
            }
    
    def _get_staff_permissions(self, cursor, staff_id: int) -> list:
        """Obtiene los permisos específicos del staff"""
        try:
            # Buscar permisos en ost_staff_dept_access
            dept_query = """
                SELECT 
                    dept_id,
                    role_id
                FROM ost_staff_dept_access 
                WHERE staff_id = %s
            """
            
            cursor.execute(dept_query, (staff_id,))
            dept_access = cursor.fetchall()
            
            permissions = []
            
            for access in dept_access:
                if access['role_id'] == 1:  # Admin
                    permissions.extend(['admin', 'manage_tickets', 'manage_users'])
                elif access['role_id'] == 2:  # Manager
                    permissions.extend(['manage_tickets', 'view_reports'])
                elif access['role_id'] == 3:  # Agent
                    permissions.extend(['view_tickets', 'respond_tickets'])
            
            return list(set(permissions))  # Remover duplicados
            
        except Exception as e:
            logger.error(f"Error obteniendo permisos de staff: {e}")
            return ['view_tickets']
    
    def _sync_user_to_django(self, user_data: Dict[str, Any], user_roles: Dict[str, Any]) -> Optional[User]:
        """Sincroniza el usuario de osTicket con Django"""
        try:
            # Buscar usuario existente en Django
            django_user = User.objects.filter(username=user_data['name']).first()
            
            if not django_user:
                # Crear nuevo usuario en Django
                django_user = User.objects.create_user(
                    username=user_data['name'],
                    email=user_data['email'],
                    first_name=user_data['name'].split()[0] if ' ' in user_data['name'] else user_data['name'],
                    last_name=' '.join(user_data['name'].split()[1:]) if ' ' in user_data['name'] else '',
                    is_active=user_data["status"] == 0
                )
                
                logger.info(f"Usuario Django creado: {django_user.username}")
            else:
                # Actualizar usuario existente
                django_user.email = user_data['email']
                django_user.is_active = user_data['status'] == 1
                django_user.save()
                
                logger.info(f"Usuario Django actualizado: {django_user.username}")
            
            return django_user
            
        except Exception as e:
            logger.error(f"Error sincronizando usuario con Django: {e}")
            return None
    
    def get_user_info(self, user_id: int) -> Dict[str, Any]:
        """Obtiene información completa del usuario"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            user_query = """
                SELECT 
                    u.id,
                    u.org_id,
                    u.status,
                    u.name,
                    ue.address as email,
                    u.created,
                    u.updated
                FROM ost_user u
                JOIN ost_user_email ue ON u.id = ue.user_id
                WHERE u.id = %s
            """
            
            cursor.execute(user_query, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                return {'error': 'Usuario no encontrado'}
            
            # Obtener roles
            user_roles = self._get_user_roles(cursor, user_id)
            
            # Obtener tickets del usuario
            tickets_query = """
                SELECT 
                    ticket_id,
                    number,
                    status_id,
                    dept_id,
                    created,
                    updated
                FROM ost_ticket 
                WHERE user_id = %s
                ORDER BY created DESC
                LIMIT 10
            """
            
            cursor.execute(tickets_query, (user_id,))
            user_tickets = cursor.fetchall()
            
            cursor.close()
            
            return {
                'success': True,
                'user': user_data,
                'roles': user_roles,
                'tickets': user_tickets
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo información del usuario: {e}")
            return {'error': str(e)}
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """Cambia la contraseña del usuario"""
        try:
            # Primero autenticar con la contraseña antigua
            auth_result = self.authenticate_user_by_id(user_id, old_password)
            if not auth_result['success']:
                return {
                    'success': False,
                    'error': 'Contraseña actual incorrecta'
                }
            
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor()
            
            # Hashear nueva contraseña
            new_hashed = hashlib.md5(new_password.encode()).hexdigest()
            
            # Actualizar contraseña
            update_query = """
                UPDATE ost_user_account 
                SET passwd = %s, updated = %s
                WHERE user_id = %s
            """
            
            cursor.execute(update_query, (new_hashed, timezone.now(), user_id))
            
            if cursor.rowcount > 0:
                conn.commit()
                cursor.close()
                
                return {
                    'success': True,
                    'message': 'Contraseña actualizada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo actualizar la contraseña'
                }
                
        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            return {'error': str(e)}
    
    def authenticate_user_by_id(self, user_id: int, password: str) -> Dict[str, Any]:
        """Autentica un usuario por ID"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            # Buscar cuenta del usuario
            account_query = """
                SELECT passwd FROM ost_user_account 
                WHERE user_id = %s
            """
            
            cursor.execute(account_query, (user_id,))
            account_data = cursor.fetchone()
            
            if not account_data:
                return {
                    'success': False,
                    'error': 'Usuario no encontrado'
                }
            
            # Verificar contraseña
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            
            if account_data['passwd'] == hashed_password:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': 'Contraseña incorrecta'
                }
                
        except Exception as e:
            logger.error(f"Error autenticando por ID: {e}")
            return {'error': str(e)}


# Instancia global
_osticket_auth = None


def get_osticket_auth() -> OsTicketAuth:
    """Obtiene la instancia global de autenticación de osTicket"""
    global _osticket_auth
    
    if _osticket_auth is None:
        _osticket_auth = OsTicketAuth()
    
    return _osticket_auth


def test_osticket_auth() -> Dict[str, Any]:
    """Prueba el sistema de autenticación de osTicket"""
    try:
        auth = get_osticket_auth()
        
        # Probar autenticación con usuario existente
        print("🧪 Probando autenticación con osTicket...")
        
        # Usar credenciales de prueba (ajustar según tu base de datos)
        test_username = "support@osticket.com"  # Usuario por defecto de osTicket
        test_password = "password123"  # Contraseña de prueba
        
        result = auth.authenticate_user(test_username, test_password)
        
        if result['success']:
            user = result['user']
            print(f"✅ Autenticación exitosa")
            print(f"   Usuario: {user['username']}")
            print(f"   Email: {user['email']}")
            print(f"   Roles: {user['roles']['type']}")
            print(f"   Permisos: {user['roles']['permissions']}")
            
            return {
                'success': True,
                'user': user,
                'message': 'Sistema de autenticación funcionando correctamente'
            }
        else:
            print(f"❌ Error de autenticación: {result['error']}")
            return result
            
    except Exception as e:
        logger.error(f"Error probando autenticación: {e}")
        return {
            'success': False,
            'error': str(e)
        }
