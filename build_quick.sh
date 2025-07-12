#!/bin/bash

# Nombre: build_quick.sh
# Descripción: Construcción rápida de Synap con opciones para el microservicio IA
# Autor: Sebastián Paredes

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() {
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

show_help() {
    echo -e "${CYAN}=== CONSTRUCCIÓN RÁPIDA DE SYNAP ===${NC}"
    echo ""
    echo "Uso: ./build_quick.sh [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  cpu       - Construir con microservicio IA CPU (más rápido)"
    echo "  cuda      - Construir con microservicio IA CUDA (más lento, requiere GPU)"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./build_quick.sh cpu    # Construcción rápida con CPU"
    echo "  ./build_quick.sh cuda   # Construcción con CUDA para GPU"
    echo ""
}

build_with_option() {
    local option=$1
    
    echo -e "${PURPLE}========================================"
    echo -e "  🚀 CONSTRUCCIÓN RÁPIDA DE SYNAP"
    echo -e "  🤖 Opción IA: $option"
    echo -e "  📅 Fecha: $(date +"%Y-%m-%d %H:%M:%S")"
    echo -e "========================================${NC}"
    echo ""
    
    # Verificar Docker
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker no está ejecutándose"
        exit 1
    fi
    
    # Detener servicios existentes
    print_status "Deteniendo servicios existentes..."
    docker-compose down --remove-orphans 2>/dev/null || true
    cd reports_ai && docker-compose down 2>/dev/null || true && cd ..
    
    # Construir proyecto principal
    print_status "Construyendo proyecto principal..."
    docker-compose build --no-cache
    
    # Construir microservicio IA con la opción especificada
    print_status "Construyendo microservicio IA ($option)..."
    cd reports_ai
    chmod +x build_reports_ai.sh
    ./build_reports_ai.sh $option
    cd ..
    
    # Levantar todos los servicios
    print_status "Levantando servicios..."
    docker-compose up -d
    sleep 5
    cd reports_ai && docker-compose up -d && cd ..
    
    # Verificar estado
    print_status "Verificando estado de servicios..."
    docker-compose ps
    echo ""
    cd reports_ai && docker-compose ps && cd ..
    
    print_success "🎉 Construcción completada!"
    echo ""
    echo -e "${CYAN}=== ACCESO ===${NC}"
    echo "🌐 Synap: http://localhost:8000"
    echo "🤖 IA API: http://localhost:8001/docs"
    echo ""
    echo -e "${YELLOW}Comandos útiles:${NC}"
    echo "  Logs: docker-compose logs -f"
    echo "  Estado: docker-compose ps"
    echo "  Detener: docker-compose down"
    echo ""
}

# Función principal
main() {
    local option=${1:-cpu}
    
    case $option in
        cpu)
            build_with_option "cpu"
            ;;
        cuda)
            build_with_option "cuda"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Opción desconocida: $option"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@" 