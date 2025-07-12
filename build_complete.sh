#!/bin/bash

# Nombre: build_complete.sh
# Descripción: Construcción completa de Synap incluyendo el microservicio IA de reportes
# Autor: Sebastián Paredes

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
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

print_header() {
    echo -e "${PURPLE}========================================"
    echo -e "  🚀 CONSTRUCCIÓN COMPLETA DE SYNAP"
    echo -e "  📅 Fecha: $(date +"%Y-%m-%d %H:%M:%S")"
    echo -e "========================================${NC}"
    echo ""
}

# Función para verificar si Docker está ejecutándose
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker no está ejecutándose. Por favor inicia Docker Desktop."
        exit 1
    fi
    print_success "Docker está ejecutándose"
}

# Función para construir el proyecto principal
build_main_project() {
    print_header
    print_status "Iniciando construcción del proyecto principal Synap..."
    
    # Verificar si existe el archivo docker-compose.yml
    if [ ! -f "docker-compose.yml" ]; then
        print_error "No se encontró docker-compose.yml en el directorio actual"
        exit 1
    fi
    
    # Detener contenedores existentes si están ejecutándose
    print_status "Deteniendo contenedores existentes..."
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Construir y levantar el proyecto principal
    print_status "Construyendo proyecto principal..."
    docker-compose build --no-cache
    
    print_success "Proyecto principal construido correctamente"
}

# Función para construir el microservicio IA
build_ai_service() {
    print_status "Iniciando construcción del microservicio IA de reportes..."
    
    # Verificar si existe el directorio reports_ai
    if [ ! -d "reports_ai" ]; then
        print_error "No se encontró el directorio reports_ai"
        exit 1
    fi
    
    cd reports_ai
    
    # Verificar si existe el script de construcción
    if [ ! -f "build_reports_ai.sh" ]; then
        print_error "No se encontró build_reports_ai.sh en reports_ai/"
        exit 1
    fi
    
    # Hacer el script ejecutable
    chmod +x build_reports_ai.sh
    
    # Construir el microservicio IA (CPU por defecto)
    print_status "Construyendo microservicio IA (versión CPU)..."
    ./build_reports_ai.sh cpu
    
    # Verificar si la construcción fue exitosa
    if [ $? -eq 0 ]; then
        print_success "Microservicio IA construido correctamente"
    else
        print_error "Error al construir el microservicio IA"
        exit 1
    fi
    
    cd ..
}

# Función para levantar todos los servicios
start_all_services() {
    print_status "Levantando todos los servicios..."
    
    # Levantar el proyecto principal
    print_status "Levantando proyecto principal..."
    docker-compose up -d
    
    # Esperar un momento para que el proyecto principal esté listo
    sleep 10
    
    # Levantar el microservicio IA
    print_status "Levantando microservicio IA..."
    cd reports_ai
    docker-compose up -d
    cd ..
    
    print_success "Todos los servicios están ejecutándose"
}

# Función para verificar el estado de los servicios
check_services_status() {
    print_status "Verificando estado de los servicios..."
    
    # Verificar proyecto principal
    print_status "Estado del proyecto principal:"
    docker-compose ps
    
    echo ""
    
    # Verificar microservicio IA
    print_status "Estado del microservicio IA:"
    cd reports_ai
    docker-compose ps
    cd ..
    
    echo ""
}

# Función para mostrar logs
show_logs() {
    print_status "Mostrando logs de los servicios..."
    
    echo -e "${CYAN}=== Logs del proyecto principal ===${NC}"
    docker-compose logs --tail=20
    
    echo ""
    echo -e "${CYAN}=== Logs del microservicio IA ===${NC}"
    cd reports_ai
    docker-compose logs --tail=20
    cd ..
}

# Función para mostrar información de acceso
show_access_info() {
    print_success "🎉 Construcción completada exitosamente!"
    echo ""
    echo -e "${CYAN}=== INFORMACIÓN DE ACCESO ===${NC}"
    echo "🌐 Proyecto principal: http://localhost:8000"
    echo "🤖 Microservicio IA: http://localhost:8001"
    echo "📊 API IA: http://localhost:8001/docs"
    echo ""
    echo -e "${YELLOW}Comandos útiles:${NC}"
    echo "  Ver logs: ./build_complete.sh logs"
    echo "  Ver estado: ./build_complete.sh status"
    echo "  Detener todo: ./build_complete.sh stop"
    echo "  Reiniciar: ./build_complete.sh restart"
    echo ""
}

# Función para detener todos los servicios
stop_all_services() {
    print_status "Deteniendo todos los servicios..."
    
    # Detener microservicio IA
    cd reports_ai
    docker-compose down 2>/dev/null || true
    cd ..
    
    # Detener proyecto principal
    docker-compose down 2>/dev/null || true
    
    print_success "Todos los servicios han sido detenidos"
}

# Función para reiniciar todos los servicios
restart_all_services() {
    print_status "Reiniciando todos los servicios..."
    
    stop_all_services
    sleep 2
    start_all_services
    check_services_status
}

# Función para limpiar recursos Docker
cleanup_docker() {
    print_warning "¿Estás seguro de que quieres limpiar todos los recursos Docker? (s/n)"
    read -r response
    if [[ "$response" =~ ^[Ss]$ ]]; then
        print_status "Limpiando recursos Docker..."
        
        # Detener todos los servicios
        stop_all_services
        
        # Limpiar contenedores, redes e imágenes no utilizadas
        docker system prune -f
        docker volume prune -f
        
        print_success "Limpieza completada"
    else
        print_status "Limpieza cancelada"
    fi
}

# Función para mostrar ayuda
show_help() {
    echo -e "${CYAN}=== AYUDA - CONSTRUCCIÓN COMPLETA DE SYNAP ===${NC}"
    echo ""
    echo "Uso: ./build_complete.sh [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  build     - Construir todo el proyecto (proyecto principal + IA)"
    echo "  start     - Levantar todos los servicios"
    echo "  stop      - Detener todos los servicios"
    echo "  restart   - Reiniciar todos los servicios"
    echo "  status    - Verificar estado de los servicios"
    echo "  logs      - Mostrar logs de los servicios"
    echo "  cleanup   - Limpiar recursos Docker"
    echo "  help      - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  ./build_complete.sh build    # Construir todo"
    echo "  ./build_complete.sh start    # Levantar servicios"
    echo "  ./build_complete.sh logs     # Ver logs"
    echo ""
}

# Función principal
main() {
    local action=${1:-build}
    
    case $action in
        build)
            check_docker
            build_main_project
            build_ai_service
            start_all_services
            check_services_status
            show_access_info
            ;;
        start)
            check_docker
            start_all_services
            check_services_status
            ;;
        stop)
            stop_all_services
            ;;
        restart)
            check_docker
            restart_all_services
            ;;
        status)
            check_services_status
            ;;
        logs)
            show_logs
            ;;
        cleanup)
            cleanup_docker
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Opción desconocida: $action"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@" 