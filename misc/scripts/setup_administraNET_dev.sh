#!/bin/bash

# Script de configuración inicial para desarrollo con administraNET
# Uso: ./setup_administraNET_dev.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Función para obtener input del usuario
get_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " input
        eval "$var_name=\${input:-$default}"
    else
        read -p "$prompt: " input
        eval "$var_name=\"$input\""
    fi
}

print_header "🚀 Configuración de Entorno de Desarrollo administraNET"
print_header "=" * 60

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    print_error "Este script debe ejecutarse desde el directorio raíz del proyecto Synap"
    exit 1
fi

print_message "Verificando requisitos previos..."

# Verificar Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi

print_success "Docker y Docker Compose están disponibles"

# Verificar MySQL
if ! command -v mysql &> /dev/null; then
    print_warning "MySQL no está instalado localmente"
    print_message "Se recomienda instalar MySQL 5.7 para desarrollo local"
    print_message "Alternativamente, puedes usar MySQL en Docker"
    
    read -p "¿Deseas configurar MySQL en Docker? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        USE_DOCKER_MYSQL=true
    else
        USE_DOCKER_MYSQL=false
    fi
else
    print_success "MySQL está disponible"
    USE_DOCKER_MYSQL=false
fi

# Configuración de variables de entorno
print_message "Configurando variables de entorno..."

# Verificar si existe .env
if [ ! -f ".env" ]; then
    print_message "Creando archivo .env desde env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        print_success "Archivo .env creado"
    else
        print_error "No se encontró env.example"
        exit 1
    fi
else
    print_warning "El archivo .env ya existe"
    read -p "¿Deseas sobrescribirlo? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp env.example .env
        print_success "Archivo .env actualizado"
    fi
fi

# Configurar variables de administraNET
print_message "Configurando variables de administraNET..."

get_input "Nombre de la base de datos administraNET" "administraNET_dev" "DB_NAME"
get_input "Usuario de MySQL" "root" "DB_USER"
get_input "Contraseña de MySQL" "" "DB_PASSWORD"
get_input "Host de MySQL" "localhost" "DB_HOST"
get_input "Puerto de MySQL" "3306" "DB_PORT"

# Actualizar .env con las nuevas variables
print_message "Actualizando archivo .env..."

# Función para actualizar variable en .env
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    
    if grep -q "^${var_name}=" .env; then
        # Variable existe, actualizarla
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^${var_name}=.*/${var_name}=${var_value}/" .env
        else
            # Linux
            sed -i "s/^${var_name}=.*/${var_name}=${var_value}/" .env
        fi
    else
        # Variable no existe, agregarla
        echo "${var_name}=${var_value}" >> .env
    fi
}

update_env_var "DB_NAME" "$DB_NAME"
update_env_var "DB_USER" "$DB_USER"
update_env_var "DB_PASSWORD" "$DB_PASSWORD"
update_env_var "DB_HOST" "$DB_HOST"
update_env_var "DB_PORT" "$DB_PORT"
update_env_var "ADMINISTRANET_ENVIRONMENT" "development"

print_success "Variables de entorno configuradas"

# Configurar MySQL en Docker si se solicita
if [ "$USE_DOCKER_MYSQL" = true ]; then
    print_message "Configurando MySQL en Docker..."
    
    # Verificar si ya existe la configuración en docker-compose.yml
    if grep -q "mysql_administraNET" docker-compose.yml; then
        print_warning "MySQL ya está configurado en docker-compose.yml"
    else
        print_message "Agregando MySQL al docker-compose.yml..."
        
        # Crear backup del docker-compose.yml
        cp docker-compose.yml docker-compose.yml.backup
        
        # Agregar servicio MySQL al final del archivo (antes de volumes)
        cat >> docker-compose.yml << 'EOF'

  # MySQL para administraNET
  mysql_administraNET:
    image: mysql:5.7
    container_name: mysql_administraNET
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: administraNET_dev
      MYSQL_USER: synap_user
      MYSQL_PASSWORD: synap_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_administraNET_data:/var/lib/mysql
    command: --default-authentication-plugin=mysql_native_password
    networks:
      - synap_network
EOF

        # Agregar volume al final del archivo
        sed -i '/^volumes:/a \  mysql_administraNET_data:' docker-compose.yml
        
        print_success "MySQL agregado al docker-compose.yml"
        print_message "Actualiza las variables DB_HOST=mysql_administraNET en .env"
    fi
fi

# Crear directorios necesarios
print_message "Creando directorios necesarios..."
mkdir -p misc/backups
mkdir -p misc/logs
print_success "Directorios creados"

# Hacer scripts ejecutables
print_message "Configurando scripts..."
chmod +x misc/scripts/*.sh
chmod +x misc/scripts/*.py
print_success "Scripts configurados"

# Instrucciones finales
print_header "✅ Configuración completada"
print_header "=" * 60

print_message "Próximos pasos:"
echo "1. Copia tu backup de administraNET a: misc/backups/"
echo "2. Restaura la base de datos con: ./misc/scripts/restore_administraNET.sh <backup_file>"
echo "3. Verifica la conexión con: docker exec Synap_app python manage.py test_administraNET"
echo "4. Inicia los servicios con: docker-compose up -d"

if [ "$USE_DOCKER_MYSQL" = true ]; then
    print_warning "Recuerda actualizar DB_HOST=mysql_administraNET en .env"
fi

print_success "¡Configuración completada exitosamente!" 