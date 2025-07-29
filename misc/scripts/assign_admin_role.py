#!/usr/bin/env python3
"""
Script para asignar el rol de administrador al superusuario.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# En el contenedor Docker, el proyecto está en /app
if os.path.exists('/app'):
    sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from core.models import Rol

User = get_user_model()

def assign_admin_role():
    """Asigna el rol de administrador al superusuario."""
    print("=== Asignando Rol de Administrador ===")
    
    # Obtener el usuario
    try:
        user = User.objects.get(email='admin@example.com')
        print(f"✅ Usuario encontrado: {user.email}")
    except User.DoesNotExist:
        print("❌ Usuario no encontrado")
        return
    
    # Verificar roles actuales
    print(f"Roles actuales: {[r.nombre for r in user.roles.all()]}")
    
    # Buscar el rol de administrador
    admin_rol = Rol.objects.filter(nombre__iexact="administrador", activo=True).first()
    if admin_rol:
        print(f"✅ Rol administrador encontrado: {admin_rol.nombre}")
        
        # Asignar el rol si no lo tiene
        if admin_rol not in user.roles.all():
            user.roles.add(admin_rol)
            print("✅ Rol administrador asignado al usuario")
        else:
            print("✅ Usuario ya tiene el rol de administrador")
    else:
        print("❌ No se encontró el rol de administrador")
        
        # Crear el rol si no existe
        print("Creando rol de administrador...")
        admin_rol = Rol.objects.create(
            nombre="Administrador",
            descripcion="Rol de administrador del sistema",
            activo=True
        )
        user.roles.add(admin_rol)
        print("✅ Rol administrador creado y asignado")
    
    # Verificar roles finales
    print(f"Roles finales: {[r.nombre for r in user.roles.all()]}")

if __name__ == "__main__":
    assign_admin_role() 