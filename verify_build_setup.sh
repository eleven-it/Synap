#!/bin/bash

# Nombre: verify_build_setup.sh
# Descripción: Verificar que toda la configuración de construcción esté correcta
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

print_header() {
    echo -e "${PURPLE}========================================"
    echo -e "  🔍 VERIFICACIÓN DE CONFIGURACIÓN"
    echo -e "  📅 Fecha: $(date +"%Y-%m-%d %H:%M:%S")"
    echo -e "========================================${NC}"
    echo ""
}

# Contador de verificaciones
total_checks=0
passed_checks=0
failed_checks=0

# Función para verificar archivo
check_file() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -f "$file" ]; then
        print_success "✓ $description: $file"
        passed_checks=$((passed_checks + 1))
    else
        print_error "✗ $description: $file (NO ENCONTRADO)"
        failed_checks=$((failed_checks + 1))
    fi
}

# Función para verificar directorio
check_directory() {
    local dir=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -d "$dir" ]; then
        print_success "✓ $description: $dir"
        passed_checks=$((passed_checks + 1))
    else
        print_error "✗ $description: $dir (NO ENCONTRADO)"
        failed_checks=$((failed_checks + 1))
    fi
}

# Función para verificar script ejecutable
check_executable() {
    local file=$1
    local description=$2
    total_checks=$((total_checks + 1))
    
    if [ -f "$file" ] && [ -x "$file" ]; then
        print_success "✓ $description: $file (EJECUTABLE)"
        passed_checks=$((passed_checks + 1))
    elif [ -f "$file" ]; then
        print_warning "⚠ $description: $file (NO EJECUTABLE)"
        chmod +x "$file"
        print_success "  → Permisos corregidos"
        passed_checks=$((passed_checks + 1))
    else
        print_error "✗ $description: $file (NO ENCONTRADO)"
        failed_checks=$((failed_checks + 1))
    fi
}

# Función para verificar Docker
check_docker() {
    total_checks=$((total_checks + 1))
    
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            print_success "✓ Docker está instalado y ejecutándose"
            passed_checks=$((passed_checks + 1))
        else
            print_error "✗ Docker está instalado pero no ejecutándose"
            failed_checks=$((failed_checks + 1))
        fi
    else
        print_error "✗ Docker no está instalado"
        failed_checks=$((failed_checks + 1))
    fi
}

# Función para verificar Docker Compose
check_docker_compose() {
    total_checks=$((total_checks + 1))
    
    if command -v docker-compose >/dev/null 2>&1; then
        print_success "✓ Docker Compose está instalado"
        passed_checks=$((passed_checks + 1))
    else
        print_error "✗ Docker Compose no está instalado"
        failed_checks=$((failed_checks + 1))
    fi
}

# Función para verificar puertos
check_ports() {
    total_checks=$((total_checks + 1))
    
    local port_8000=$(lsof -i :8000 2>/dev/null | wc -l)
    local port_8001=$(lsof -i :8001 2>/dev/null | wc -l)
    
    if [ "$port_8000" -eq 0 ] && [ "$port_8001" -eq 0 ]; then
        print_success "✓ Puertos 8000 y 8001 están libres"
        passed_checks=$((passed_checks + 1))
    else
        print_warning "⚠ Puertos ocupados:"
        if [ "$port_8000" -gt 0 ]; then
            echo "  - Puerto 8000 está en uso"
        fi
        if [ "$port_8001" -gt 0 ]; then
            echo "  - Puerto 8001 está en uso"
        fi
        passed_checks=$((passed_checks + 1))
    fi
}

# Función principal
main() {
    print_header
    
    print_status "Verificando configuración de construcción..."
    echo ""
    
    # Verificar archivos principales
    check_file "docker-compose.yml" "Docker Compose principal"
    check_file "Dockerfile" "Dockerfile principal"
    check_file ".env" "Archivo de variables de entorno"
    
    # Verificar scripts de construcción
    check_executable "build_complete.sh" "Script de construcción completa"
    check_executable "build_quick.sh" "Script de construcción rápida"
    
    # Verificar microservicio IA
    check_directory "reports_ai" "Directorio del microservicio IA"
    check_file "reports_ai/docker-compose.yml" "Docker Compose del microservicio IA"
    check_file "reports_ai/Dockerfile" "Dockerfile del microservicio IA"
    check_file "reports_ai/Dockerfile.cpu" "Dockerfile CPU del microservicio IA"
    check_executable "reports_ai/build_reports_ai.sh" "Script de construcción del microservicio IA"
    check_file "reports_ai/requirements.txt" "Dependencias del microservicio IA"
    check_file "reports_ai/main.py" "Aplicación principal del microservicio IA"
    
    # Verificar módulo reports
    check_directory "reports" "Módulo de reportes"
    check_file "reports/models.py" "Modelos de reportes"
    check_file "reports/views.py" "Vistas de reportes"
    check_file "reports/urls.py" "URLs de reportes"
    
    # Verificar documentación
    check_file "BUILD_GUIDE.md" "Guía de construcción"
    check_file "README.md" "README principal"
    
    echo ""
    print_status "Verificando entorno del sistema..."
    echo ""
    
    # Verificar herramientas del sistema
    check_docker
    check_docker_compose
    check_ports
    
    # Verificar espacio en disco
    total_checks=$((total_checks + 1))
    available_space=$(df . | awk 'NR==2 {print $4}')
    available_gb=$((available_space / 1024 / 1024))
    
    if [ "$available_gb" -ge 20 ]; then
        print_success "✓ Espacio disponible: ${available_gb}GB (suficiente)"
        passed_checks=$((passed_checks + 1))
    else
        print_warning "⚠ Espacio disponible: ${available_gb}GB (recomendado: 20GB+)"
        passed_checks=$((passed_checks + 1))
    fi
    
    # Verificar memoria RAM
    total_checks=$((total_checks + 1))
    total_memory=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    total_gb=$((total_memory / 1024 / 1024 / 1024))
    
    if [ "$total_gb" -ge 8 ]; then
        print_success "✓ Memoria RAM: ${total_gb}GB (suficiente)"
        passed_checks=$((passed_checks + 1))
    else
        print_warning "⚠ Memoria RAM: ${total_gb}GB (recomendado: 8GB+)"
        passed_checks=$((passed_checks + 1))
    fi
    
    echo ""
    print_status "Resumen de verificación:"
    echo "  Total de verificaciones: $total_checks"
    echo "  Exitosas: $passed_checks"
    echo "  Fallidas: $failed_checks"
    echo ""
    
    if [ "$failed_checks" -eq 0 ]; then
        print_success "🎉 ¡Toda la configuración está correcta!"
        echo ""
        echo -e "${CYAN}Próximos pasos:${NC}"
        echo "  1. Ejecutar: ./build_quick.sh cpu"
        echo "  2. Esperar a que termine la construcción"
        echo "  3. Acceder a: http://localhost:8000"
        echo ""
    else
        print_error "❌ Hay $failed_checks problema(s) que deben resolverse antes de construir."
        echo ""
        echo -e "${YELLOW}Recomendaciones:${NC}"
        echo "  - Instalar Docker Desktop si no está instalado"
        echo "  - Verificar que Docker esté ejecutándose"
        echo "  - Liberar puertos si están ocupados"
        echo "  - Verificar archivos faltantes"
        echo ""
    fi
}

# Ejecutar verificación
main "$@" 