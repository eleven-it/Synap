#!/bin/bash

# ============================================================================
# Script de Inicialización Completa de Synap
# ============================================================================
# Este script configura una instancia nueva de Synap desde cero
# Ejecuta migraciones, setup inicial, carga de datos y configuración
# 
# Uso:
#   chmod +x init_synap_instance.sh
#   ./init_synap_instance.sh
#
# Compatible con:
#   - Docker Desktop (macOS, Windows WSL2)
#   - Docker Compose (Linux)
# ============================================================================

set -e

# Colores para output
COLOR_OK='\033[1;32m'
COLOR_WARN='\033[1;33m'
COLOR_ERR='\033[1;31m'
COLOR_CYAN='\033[1;36m'
COLOR_RESET='\033[0m'

function ok() { echo -e "${COLOR_OK}✅ $1${COLOR_RESET}"; }
function warn() { echo -e "${COLOR_WARN}⚙️  $1${COLOR_RESET}"; }
function err() { echo -e "${COLOR_ERR}❌ $1${COLOR_RESET}"; }
function info() { echo -e "${COLOR_CYAN}ℹ️  $1${COLOR_RESET}"; }
function header() { 
    echo ""
    echo -e "${COLOR_CYAN}============================================================================${COLOR_RESET}"
    echo -e "${COLOR_CYAN}$1${COLOR_RESET}"
    echo -e "${COLOR_CYAN}============================================================================${COLOR_RESET}"
    echo ""
}

header "INICIALIZACIÓN COMPLETA DE SYNAP"

# Verificar que Docker esté corriendo
info "Verificando que Docker esté corriendo..."
if ! docker ps > /dev/null 2>&1; then
    err "Docker no está corriendo. Por favor inicia Docker Desktop."
    exit 1
fi
ok "Docker está corriendo"

# Verificar que el contenedor Synap_app exista
info "Verificando contenedor Synap_app..."
if ! docker ps -a | grep -q Synap_app; then
    err "Contenedor Synap_app no encontrado."
    err "Por favor ejecuta: docker compose up -d"
    exit 1
fi

# Verificar que el contenedor esté corriendo
if ! docker ps | grep -q Synap_app; then
    warn "Contenedor Synap_app no está corriendo. Iniciando..."
    docker compose up -d
    sleep 10
fi
ok "Contenedor Synap_app está corriendo"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 1: MIGRACIONES DE BASE DE DATOS"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Aplicando migraciones de base de datos..."
docker exec Synap_app python manage.py migrate --noinput
ok "Migraciones aplicadas exitosamente"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 2: SETUP INICIAL DEL SISTEMA"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Configurando sistema (usuarios, empresa, permisos)..."
docker exec Synap_app python manage.py initial_setup --skip-migrations
ok "Setup inicial completado"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 3: DATOS INICIALES"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Cargando datos iniciales (países, monedas, unidades, etc.)..."
docker exec Synap_app python manage.py load_initial_data
ok "Datos iniciales cargados"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 4: ARCHIVOS ESTÁTICOS"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Recolectando archivos estáticos..."
docker exec Synap_app python manage.py collectstatic --noinput
ok "Archivos estáticos recolectados"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 5: CONFIGURACIÓN DE i18n"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Compilando traducciones..."
docker exec Synap_app python manage.py compilemessages 2>/dev/null || info "Sin archivos de traducción para compilar (opcional)"
ok "Traducciones compiladas"

echo ""
warn "═══════════════════════════════════════════════════════════════════════════"
warn "PASO 6: VERIFICACIÓN FINAL"
warn "═══════════════════════════════════════════════════════════════════════════"
info "Verificando servicios..."
docker compose ps

# Obtener información del usuario administrador creado
echo ""
info "Obteniendo credenciales de administrador..."
docker exec Synap_app python manage.py shell << 'PYTHON_SCRIPT'
from core.models import UsuarioExtendido, Rol

# Buscar usuario administrador
admin_users = UsuarioExtendido.objects.filter(roles__nombre='Administrador').first()

if admin_users:
    print(f"\n{'=' * 80}")
    print(f"🔑 CREDENCIALES DE ACCESO")
    print(f"{'=' * 80}")
    print(f"\n   Usuario:   {admin_users.username}")
    print(f"   Email:     {admin_users.email}")
    print(f"   UID:       {admin_users.uid}")
    print(f"   Roles:     {[r.nombre for r in admin_users.roles.all()]}")
    print(f"\n{'=' * 80}")
else:
    print("\n⚠️  No se encontró usuario administrador")
    print("   Ejecuta: python manage.py createsuperuser")
    print("   O: ./misc/scripts/reset_auth_wsl2.sh")
PYTHON_SCRIPT

# Resultado final
header "✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE"

echo -e "${COLOR_CYAN}🌐 ACCESO A SYNAP:${COLOR_RESET}"
echo -e "   Local:      ${COLOR_OK}http://localhost:8002${COLOR_RESET}"
echo -e "   Login:      ${COLOR_OK}http://localhost:8002/login/${COLOR_RESET}"
echo -e "   Dashboard:  ${COLOR_OK}http://localhost:8002/core/dashboard/${COLOR_RESET}"
echo -e "   Admin:      ${COLOR_OK}http://localhost:8002/admin/${COLOR_RESET}"
echo -e "   Rosetta:    ${COLOR_OK}http://localhost:8002/rosetta/${COLOR_RESET} (traducciones)"
echo ""

echo -e "${COLOR_CYAN}📋 COMANDOS ÚTILES:${COLOR_RESET}"
echo -e "   Ver logs:        ${COLOR_WARN}docker compose logs -f app${COLOR_RESET}"
echo -e "   Reiniciar:       ${COLOR_WARN}docker compose restart app${COLOR_RESET}"
echo -e "   Entrar a shell:  ${COLOR_WARN}docker exec -it Synap_app bash${COLOR_RESET}"
echo -e "   Django shell:    ${COLOR_WARN}docker exec -it Synap_app python manage.py shell${COLOR_RESET}"
echo ""

echo -e "${COLOR_CYAN}🔧 SI HAY PROBLEMAS:${COLOR_RESET}"
echo -e "   Redirect loop:   ${COLOR_WARN}./misc/scripts/reset_auth_wsl2.sh${COLOR_RESET}"
echo -e "   Documentación:   ${COLOR_WARN}misc/documentacion/troubleshooting_redirect_loop.md${COLOR_RESET}"
echo ""

ok "🎉 ¡Synap está listo para usarse!"
echo "" 