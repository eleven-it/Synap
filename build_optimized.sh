#!/bin/bash

# Script para construir imágenes Docker optimizadas
# Uso: ./build_optimized.sh [--no-cache] [--parallel]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
NO_CACHE=""
PARALLEL=false
BUILD_ARGS=""

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        *)
            echo "Argumento desconocido: $1"
            echo "Uso: $0 [--no-cache] [--parallel]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 Iniciando construcción optimizada de imágenes Docker${NC}"
echo -e "${YELLOW}Configuración:${NC}"
echo -e "  - No cache: ${NO_CACHE:-false}"
echo -e "  - Paralelo: ${PARALLEL}"
echo ""

# Función para construir imagen
build_image() {
    local service=$1
    local dockerfile=$2
    local context=$3
    
    echo -e "${BLUE}🔨 Construyendo $service...${NC}"
    
    if [ "$PARALLEL" = true ]; then
        docker build $NO_CACHE $BUILD_ARGS \
            -f "$dockerfile" \
            -t "synap_$service" \
            "$context" &
    else
        docker build $NO_CACHE $BUILD_ARGS \
            -f "$dockerfile" \
            -t "synap_$service" \
            "$context"
    fi
    
    echo -e "${GREEN}✅ $service construido exitosamente${NC}"
}

# Función para construir imagen con cache
build_with_cache() {
    local service=$1
    local dockerfile=$2
    local context=$3
    local cache_from=$4
    
    echo -e "${BLUE}🔨 Construyendo $service con cache...${NC}"
    
    if [ "$PARALLEL" = true ]; then
        docker build $NO_CACHE $BUILD_ARGS \
            --cache-from "$cache_from" \
            -f "$dockerfile" \
            -t "synap_$service" \
            "$context" &
    else
        docker build $NO_CACHE $BUILD_ARGS \
            --cache-from "$cache_from" \
            -f "$dockerfile" \
            -t "synap_$service" \
            "$context"
    fi
    
    echo -e "${GREEN}✅ $service construido exitosamente${NC}"
}

# Limpiar imágenes anteriores (opcional)
echo -e "${YELLOW}🧹 Limpiando imágenes anteriores...${NC}"
docker system prune -f --volumes=false

# Construir imágenes base primero para cache
echo -e "${BLUE}📦 Descargando imágenes base para cache...${NC}"
docker pull python:3.10-slim
docker pull pytorch/pytorch:latest
docker pull postgres:15-alpine
docker pull redis:7-alpine

# Construir imágenes de servicios
echo -e "${BLUE}🏗️  Construyendo servicios...${NC}"

# Construir imagen principal de Django
build_with_cache "web" "Dockerfile" "." "python:3.10-slim"


# Esperar a que terminen las construcciones paralelas
if [ "$PARALLEL" = true ]; then
    echo -e "${YELLOW}⏳ Esperando que terminen las construcciones paralelas...${NC}"
    wait
fi

# Verificar que las imágenes se construyeron correctamente
echo -e "${BLUE}🔍 Verificando imágenes construidas...${NC}"
docker images | grep synap_

# Mostrar estadísticas de construcción
echo -e "${GREEN}📊 Estadísticas de construcción:${NC}"
docker system df

echo -e "${GREEN}🎉 ¡Construcción completada exitosamente!${NC}"
echo -e "${YELLOW}💡 Para iniciar los servicios: docker-compose up -d${NC}"
echo -e "${YELLOW}💡 Para ver logs: docker-compose logs -f${NC}" 