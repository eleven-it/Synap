#!/usr/bin/env python3
"""
Script simple para probar autenticación con usuarios reales de osTicket
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eleven_support.settings')
django.setup()

from support_ai.osticket_auth import get_osticket_auth

def test_auth_with_real_users():
    """Prueba autenticación con usuarios reales de osTicket"""
    
    print("🧪 PROBANDO AUTENTICACIÓN CON USUARIOS REALES DE OSTICKET")
    print("=" * 70)
    
    auth = get_osticket_auth()
    
    # Lista de usuarios de prueba (ajustar según tu base de datos)
    test_users = [
        {
            'email': 'drogueriacuyomed@gmail.com',
            'password': 'password123'  # Contraseña de prueba
        },
        {
            'email': 'mayra.gonzalez@gsolutions.com.ar',
            'password': 'password123'
        }
    ]
    
    for i, user_data in enumerate(test_users, 1):
        print(f"\n📝 Probando usuario {i}: {user_data['email']}")
        print("-" * 50)
        
        try:
            result = auth.authenticate_user(user_data['email'], user_data['password'])
            
            if result['success']:
                user = result['user']
                print(f"✅ Autenticación exitosa!")
                print(f"   Usuario: {user['username']}")
                print(f"   Email: {user['email']}")
                print(f"   Tipo de rol: {user['roles']['type']}")
                print(f"   Permisos: {user['roles']['permissions']}")
                
                # Probar obtención de información del usuario
                print(f"\n🔍 Obteniendo información del usuario...")
                user_info = auth.get_user_info(user['id'])
                
                if user_info.get('success'):
                    print(f"   ✅ Información obtenida")
                    print(f"   Tickets: {len(user_info['tickets'])}")
                else:
                    print(f"   ❌ Error: {user_info.get('error')}")
                
                return {
                    'success': True,
                    'user': user,
                    'message': 'Sistema de autenticación funcionando correctamente'
                }
                
            else:
                print(f"❌ Error de autenticación: {result['error']}")
                
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n❌ No se pudo autenticar ningún usuario")
    return {
        'success': False,
        'error': 'No se pudo autenticar ningún usuario de prueba'
    }

if __name__ == "__main__":
    result = test_auth_with_real_users()
    
    if result['success']:
        print(f"\n🎉 ¡SISTEMA DE AUTENTICACIÓN FUNCIONANDO!")
        print(f"   Usuario: {result['user']['username']}")
        print(f"   Email: {result['user']['email']}")
        print(f"   Roles: {result['user']['roles']['type']}")
    else:
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)
