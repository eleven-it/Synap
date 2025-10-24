#!/bin/bash

# ============================================================================
# Script de Reset de Autenticación para WSL2
# ============================================================================
# Soluciona problemas de ERR_TOO_MANY_REDIRECTS
# Limpia sesiones y crea usuario administrador UsuarioExtendido
# ============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}============================================================================${NC}"
echo -e "${CYAN}       RESET DE AUTENTICACIÓN - SOLUCIÓN REDIRECT LOOP${NC}"
echo -e "${CYAN}============================================================================${NC}"
echo ""

# 1. Verificar Docker
echo -e "${YELLOW}1. Verificando servicios Docker...${NC}"
if ! docker compose ps | grep -q "Synap_app.*Up"; then
    echo -e "${RED}❌ Synap_app no está corriendo${NC}"
    echo -e "${YELLOW}   Iniciando servicios...${NC}"
    docker compose up -d
    sleep 10
fi
echo -e "${GREEN}✅ Docker corriendo${NC}"

# 2. Limpiar Redis
echo ""
echo -e "${YELLOW}2. Limpiando Redis...${NC}"
docker exec Synap_redis redis-cli FLUSHALL > /dev/null 2>&1
echo -e "${GREEN}✅ Redis limpiado${NC}"

# 3. Limpiar sesiones DB
echo ""
echo -e "${YELLOW}3. Limpiando sesiones en base de datos...${NC}"
docker exec Synap_app python manage.py shell -c "
from django.contrib.sessions.models import Session
deleted = Session.objects.all().delete()
print('Sesiones eliminadas:', deleted[0])
" 2>/dev/null
echo -e "${GREEN}✅ Sesiones DB limpiadas${NC}"

# 4. Crear usuario administrador
echo ""
echo -e "${YELLOW}4. Creando usuario administrador UsuarioExtendido...${NC}"

# Solicitar credenciales
read -p "Nombre de usuario [admin]: " username
username=${username:-admin}

read -p "Email [admin@synap.com]: " email
email=${email:-admin@synap.com}

read -sp "Contraseña [admin123]: " password
echo
password=${password:-admin123}

docker exec Synap_app python manage.py shell << PYTHON_SCRIPT
from core.models import UsuarioExtendido, Rol
from django.contrib.auth.hashers import make_password

# Eliminar usuario si existe
UsuarioExtendido.objects.filter(username='${username}').delete()
print('🗑️  Usuario anterior eliminado (si existía)')

# Crear nuevo usuario
user = UsuarioExtendido.objects.create(
    username='${username}',
    email='${email}',
    first_name='Admin',
    last_name='Synap',
    uid='${username}',
    password=make_password('${password}'),
    is_staff=True,
    is_superuser=True
)

print(f'✅ Usuario {user.username} creado')

# Asignar rol Administrador
try:
    admin_role = Rol.objects.get(nombre='Administrador')
    print('📋 Rol Administrador encontrado')
except Rol.DoesNotExist:
    print('⚠️  Rol Administrador no existe, creándolo...')
    admin_role = Rol.objects.create(
        nombre='Administrador',
        descripcion='Acceso total al sistema',
        activo=True
    )
    print('✅ Rol Administrador creado')

user.roles.add(admin_role)
print('✅ Rol asignado al usuario')

# Verificar
print('')
print('📊 Verificación:')
print(f'   Usuario: {user.username}')
print(f'   Email: {user.email}')
print(f'   UID: {user.uid}')
print(f'   Staff: {user.is_staff}')
print(f'   Superuser: {user.is_superuser}')
print(f'   Roles: {[r.nombre for r in user.roles.all()]}')
PYTHON_SCRIPT

echo -e "${GREEN}✅ Usuario administrador creado${NC}"

# 5. Reiniciar servicios
echo ""
echo -e "${YELLOW}5. Reiniciando servicios...${NC}"
docker compose restart app
echo -e "${GREEN}✅ Servicios reiniciados${NC}"

# 6. Esperar a que el servicio esté listo
echo ""
echo -e "${YELLOW}6. Esperando a que el servicio esté listo...${NC}"
sleep 5
echo -e "${GREEN}✅ Servicio listo${NC}"

# 7. Verificar servicios
echo ""
echo -e "${YELLOW}7. Verificando estado de servicios...${NC}"
docker compose ps

# Resultado final
echo ""
echo -e "${GREEN}============================================================================${NC}"
echo -e "${GREEN}       ✅ RESET COMPLETADO EXITOSAMENTE${NC}"
echo -e "${GREEN}============================================================================${NC}"
echo ""
echo -e "${CYAN}🔑 Credenciales de acceso:${NC}"
echo -e "   Usuario:   ${YELLOW}${username}${NC}"
echo -e "   Password:  ${YELLOW}${password}${NC}"
echo -e "   Email:     ${YELLOW}${email}${NC}"
echo ""
echo -e "${CYAN}🌐 Acceso:${NC}"
echo -e "   Local:     ${YELLOW}http://localhost:8002/login/${NC}"
echo -e "   Dashboard: ${YELLOW}http://localhost:8002/core/dashboard/${NC}"
echo ""
echo -e "${CYAN}📋 Próximos pasos:${NC}"
echo -e "   1. Abrir navegador"
echo -e "   2. Ir a http://localhost:8002/login/"
echo -e "   3. Ingresar credenciales"
echo -e "   4. Verificar acceso al dashboard"
echo ""
echo -e "${GREEN}============================================================================${NC}"

