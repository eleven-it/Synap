#!/bin/bash

# ============================================================================
# Script de Instalación Automática de Synap en WSL2
# ============================================================================
# Este script automatiza la instalación de Synap en WSL2 con Docker Desktop
# 
# Uso:
#   chmod +x setup_wsl2.sh
#   ./setup_wsl2.sh
#
# ============================================================================

set -e  # Salir si cualquier comando falla

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_header() {
    echo -e "\n${CYAN}============================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar que estamos en WSL2
check_wsl2() {
    print_header "Verificando Entorno WSL2"
    
    if ! grep -qi microsoft /proc/version; then
        print_error "Este script debe ejecutarse en WSL2"
        exit 1
    fi
    
    print_success "WSL2 detectado correctamente"
}

# Verificar Docker
check_docker() {
    print_header "Verificando Docker"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado"
        print_info "Por favor instala Docker Desktop para Windows"
        print_info "https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        print_error "Docker no está corriendo o no tiene permisos"
        print_info "Asegúrate de que Docker Desktop esté iniciado"
        print_info "Y que la integración con WSL2 esté habilitada"
        exit 1
    fi
    
    print_success "Docker está instalado y funcionando"
    docker --version
}

# Verificar Docker Compose
check_docker_compose() {
    print_header "Verificando Docker Compose"
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose no está instalado"
        exit 1
    fi
    
    print_success "Docker Compose está instalado"
    docker-compose --version
}

# Instalar dependencias
install_dependencies() {
    print_header "Instalando Dependencias del Sistema"
    
    print_info "Actualizando lista de paquetes..."
    sudo apt update
    
    print_info "Instalando Git..."
    sudo apt install -y git
    
    print_info "Instalando herramientas básicas..."
    sudo apt install -y curl wget nano vim
    
    print_success "Dependencias instaladas"
}

# Configurar Git
configure_git() {
    print_header "Configurando Git"
    
    # Verificar si Git ya está configurado
    if git config --global user.name &> /dev/null && git config --global user.email &> /dev/null; then
        print_success "Git ya está configurado"
        print_info "Usuario: $(git config --global user.name)"
        print_info "Email: $(git config --global user.email)"
        return
    fi
    
    # Configurar Git
    echo -e "${YELLOW}Configuración de Git:${NC}"
    read -p "Nombre de usuario: " git_name
    read -p "Email: " git_email
    
    git config --global user.name "$git_name"
    git config --global user.email "$git_email"
    
    print_success "Git configurado correctamente"
}

# Clonar repositorio
clone_repository() {
    print_header "Clonando Repositorio de Synap"
    
    # Crear directorio de proyectos si no existe
    PROJECTS_DIR="$HOME/proyectos"
    mkdir -p "$PROJECTS_DIR"
    
    # Directorio del proyecto
    PROJECT_DIR="$PROJECTS_DIR/Synap"
    
    # Si el directorio ya existe, preguntar si quiere actualizarlo
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "El directorio $PROJECT_DIR ya existe"
        read -p "¿Deseas actualizarlo? (s/n): " update_repo
        
        if [ "$update_repo" = "s" ] || [ "$update_repo" = "S" ]; then
            cd "$PROJECT_DIR"
            print_info "Actualizando repositorio..."
            git pull origin 1.0
            print_success "Repositorio actualizado"
        else
            print_info "Usando repositorio existente"
        fi
    else
        # Clonar repositorio
        cd "$PROJECTS_DIR"
        print_info "Clonando desde GitHub..."
        git clone https://github.com/eleven-it/Synap.git
        cd Synap
        
        # Cambiar a rama 1.0
        print_info "Cambiando a rama 1.0..."
        git checkout 1.0
        
        print_success "Repositorio clonado correctamente"
    fi
    
    # Guardar directorio del proyecto
    echo "$PROJECT_DIR" > /tmp/synap_project_dir
}

# Generar SECRET_KEY
generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_urlsafe(50))"
}

# Configurar archivo .env
configure_env() {
    print_header "Configurando Archivo .env"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    # Si .env ya existe, preguntar si quiere recrearlo
    if [ -f ".env" ]; then
        print_warning "El archivo .env ya existe"
        read -p "¿Deseas recrearlo? (s/n): " recreate_env
        
        if [ "$recreate_env" != "s" ] && [ "$recreate_env" != "S" ]; then
            print_info "Usando archivo .env existente"
            return
        fi
    fi
    
    # Generar SECRET_KEY
    print_info "Generando SECRET_KEY..."
    SECRET_KEY=$(generate_secret_key)
    
    # Solicitar datos
    echo -e "\n${YELLOW}Configuración de Base de Datos PostgreSQL:${NC}"
    read -p "Usuario PostgreSQL [synap_user]: " pg_user
    pg_user=${pg_user:-synap_user}
    
    read -s -p "Contraseña PostgreSQL: " pg_password
    echo
    
    read -p "Nombre de Base de Datos [synap_db]: " pg_db
    pg_db=${pg_db:-synap_db}
    
    echo -e "\n${YELLOW}Configuración de Tiendanube (opcional, presiona Enter para omitir):${NC}"
    read -p "Client ID: " tiendanube_client_id
    read -s -p "Client Secret: " tiendanube_client_secret
    echo
    
    echo -e "\n${YELLOW}Configuración de AdministraNET (opcional, presiona Enter para omitir):${NC}"
    read -p "Host MySQL: " adminet_host
    read -p "Usuario MySQL: " adminet_user
    read -s -p "Contraseña MySQL: " adminet_password
    echo
    read -p "Base de Datos [administranet]: " adminet_db
    adminet_db=${adminet_db:-administranet}
    
    # Crear archivo .env
    print_info "Creando archivo .env..."
    
    cat > .env << EOF
# Django Configuration
DEBUG=True
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=localhost,127.0.0.1
SITE_URL=http://localhost:8002

# PostgreSQL Database
POSTGRES_DB=$pg_db
POSTGRES_USER=$pg_user
POSTGRES_PASSWORD=$pg_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Tiendanube Integration
TIENDANUBE_CLIENT_ID=${tiendanube_client_id:-your_client_id_here}
TIENDANUBE_CLIENT_SECRET=${tiendanube_client_secret:-your_client_secret_here}

# AdministraNET (MySQL External)
ADMINET_HOST=${adminet_host:-localhost}
ADMINET_PORT=3306
ADMINET_DATABASE=${adminet_db:-administranet}
ADMINET_USER=${adminet_user:-root}
ADMINET_PASSWORD=${adminet_password:-}
EOF
    
    print_success "Archivo .env creado correctamente"
}

# Construir imágenes Docker
build_docker() {
    print_header "Construyendo Imágenes Docker"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    print_info "Esto puede tomar varios minutos..."
    docker-compose build
    
    print_success "Imágenes construidas correctamente"
}

# Iniciar servicios
start_services() {
    print_header "Iniciando Servicios Docker"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    print_info "Iniciando contenedores..."
    docker-compose up -d
    
    # Esperar a que los servicios estén listos
    print_info "Esperando a que los servicios estén listos..."
    sleep 10
    
    print_success "Servicios iniciados correctamente"
}

# Aplicar migraciones
run_migrations() {
    print_header "Aplicando Migraciones de Base de Datos"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    print_info "Aplicando migraciones..."
    docker exec Synap_app python manage.py migrate
    
    print_success "Migraciones aplicadas correctamente"
}

# Crear superusuario
create_superuser() {
    print_header "Creando Superusuario"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    echo -e "${YELLOW}Configuración de Superusuario:${NC}"
    read -p "¿Deseas crear un superusuario ahora? (s/n): " create_su
    
    if [ "$create_su" = "s" ] || [ "$create_su" = "S" ]; then
        docker exec -it Synap_app python manage.py createsuperuser
        print_success "Superusuario creado correctamente"
    else
        print_info "Puedes crear un superusuario más tarde con:"
        print_info "docker exec -it Synap_app python manage.py createsuperuser"
    fi
}

# Recolectar archivos estáticos
collect_static() {
    print_header "Recolectando Archivos Estáticos"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    print_info "Recolectando archivos estáticos..."
    docker exec Synap_app python manage.py collectstatic --noinput
    
    print_success "Archivos estáticos recolectados correctamente"
}

# Verificar instalación
verify_installation() {
    print_header "Verificando Instalación"
    
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    # Verificar servicios
    print_info "Estado de los servicios:"
    docker-compose ps
    
    # Verificar logs
    print_info "\nÚltimas líneas de logs:"
    docker-compose logs --tail=20 app
    
    # Verificar acceso
    echo -e "\n${GREEN}============================================================================${NC}"
    echo -e "${GREEN}✅ INSTALACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo -e "${GREEN}============================================================================${NC}"
    echo -e "\n${CYAN}Accesos:${NC}"
    echo -e "  🌐 Aplicación: ${BLUE}http://localhost:8002${NC}"
    echo -e "  🔐 Admin:      ${BLUE}http://localhost:8002/admin${NC}"
    echo -e "\n${CYAN}Comandos útiles:${NC}"
    echo -e "  Ver logs:      ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  Detener:       ${YELLOW}docker-compose down${NC}"
    echo -e "  Reiniciar:     ${YELLOW}docker-compose restart${NC}"
    echo -e "  Entrar a app:  ${YELLOW}docker exec -it Synap_app bash${NC}"
    echo -e "\n${CYAN}Directorio del proyecto:${NC}"
    echo -e "  ${YELLOW}$PROJECT_DIR${NC}"
    echo -e "\n${GREEN}============================================================================${NC}\n"
}

# Menú principal
main() {
    print_header "INSTALACIÓN DE SYNAP EN WSL2 CON DOCKER DESKTOP"
    
    echo -e "${YELLOW}Este script instalará y configurará Synap automáticamente.${NC}"
    echo -e "${YELLOW}Tiempo estimado: 10-15 minutos${NC}\n"
    
    read -p "¿Deseas continuar? (s/n): " continue_install
    
    if [ "$continue_install" != "s" ] && [ "$continue_install" != "S" ]; then
        print_info "Instalación cancelada"
        exit 0
    fi
    
    # Ejecutar pasos de instalación
    check_wsl2
    check_docker
    check_docker_compose
    install_dependencies
    configure_git
    clone_repository
    configure_env
    build_docker
    start_services
    
    # Ejecutar script de inicialización completa
    PROJECT_DIR=$(cat /tmp/synap_project_dir)
    cd "$PROJECT_DIR"
    
    print_header "Ejecutando Inicialización Completa de Synap"
    print_info "Usando script: misc/scripts/init_synap_instance.sh"
    
    chmod +x misc/scripts/init_synap_instance.sh
    ./misc/scripts/init_synap_instance.sh
    
    print_success "¡Todo listo! Disfruta de Synap 🚀"
}

# Ejecutar script
main

