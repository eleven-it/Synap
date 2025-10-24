#!/bin/bash

# Script de Deploy para Producción Synap
# Este script clona solo los archivos necesarios para el entorno productivo

set -e

echo "================================================"
echo "   DEPLOY OPTIMIZADO PARA PRODUCCIÓN - SYNAP"
echo "================================================"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
REPO_URL="git@github.com:eleven-it/Synap.git"
BRANCH="1.0"
DEPLOY_DIR="/home/sparedes/Synap"
BACKUP_DIR="/home/sparedes/Synap_backups"

# Función para logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Verificar espacio en disco
echo ""
log_info "1. Verificando espacio en disco..."
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
log_info "Uso actual del disco: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 85 ]; then
    log_warn "Disco con más del 85% de uso. Limpiando..."
    sudo docker system prune -f
fi

# 2. Crear backup si existe instalación previa
echo ""
log_info "2. Creando backup de configuración..."
if [ -d "$DEPLOY_DIR" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"
    
    # Backup solo de archivos críticos
    if [ -f "$DEPLOY_DIR/.env" ]; then
        cp "$DEPLOY_DIR/.env" "$BACKUP_DIR/.env.$TIMESTAMP"
        log_info "Backup de .env creado"
    fi
    
    if [ -d "$DEPLOY_DIR/media" ]; then
        tar -czf "$BACKUP_DIR/media.$TIMESTAMP.tar.gz" -C "$DEPLOY_DIR" media/
        log_info "Backup de media creado"
    fi
fi

# 3. Clonar o actualizar repositorio
echo ""
log_info "3. Actualizando código desde GitHub..."

if [ -d "$DEPLOY_DIR/.git" ]; then
    log_info "Actualizando repositorio existente..."
    cd "$DEPLOY_DIR"
    
    # Guardar cambios locales si existen
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "Hay cambios locales. Guardando stash..."
        git stash
    fi
    
    # Actualizar
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    log_info "Clonando repositorio..."
    git clone -b "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# 4. Limpiar archivos innecesarios para producción
echo ""
log_info "4. Limpiando archivos innecesarios para producción..."

# Eliminar directorios de desarrollo
DIRS_TO_REMOVE=(
    "administraNET_Limpio"
    "media_bak"
    "misc/documentacion"
    "misc/fix"
    "misc/test"
)

for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [ -d "$DEPLOY_DIR/$dir" ]; then
        rm -rf "$DEPLOY_DIR/$dir"
        log_info "Eliminado: $dir"
    fi
done

# Eliminar archivos de desarrollo
find "$DEPLOY_DIR" -type f \( -name "test_*.py" -o -name "debug_*.py" -o -name "investigate_*.py" \) -delete
find "$DEPLOY_DIR" -type f -name "*.md" -delete
find "$DEPLOY_DIR" -type f -name ".DS_Store" -delete

log_info "Archivos de desarrollo eliminados"

# 5. Verificar/restaurar .env
echo ""
log_info "5. Verificando configuración..."
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    if [ -f "$BACKUP_DIR/.env.$TIMESTAMP" ]; then
        cp "$BACKUP_DIR/.env.$TIMESTAMP" "$DEPLOY_DIR/.env"
        log_info ".env restaurado desde backup"
    else
        log_error ".env no encontrado. Debes crear uno manualmente."
        exit 1
    fi
fi

# 6. Actualizar contenedores Docker
echo ""
log_info "6. Actualizando contenedores Docker..."
sudo docker-compose down
sudo docker-compose up -d --build

# 7. Aplicar migraciones
echo ""
log_info "7. Aplicando migraciones de base de datos..."
sleep 10  # Esperar a que los contenedores estén listos
docker exec Synap_app python manage.py migrate --noinput

# 8. Recolectar archivos estáticos
echo ""
log_info "8. Recolectando archivos estáticos..."
docker exec Synap_app python manage.py collectstatic --noinput

# 9. Verificar servicios
echo ""
log_info "9. Verificando servicios..."
sleep 5
docker-compose ps

# 10. Mostrar estadísticas finales
echo ""
log_info "10. Estadísticas finales..."
DISK_USAGE_FINAL=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
log_info "Uso final del disco: ${DISK_USAGE_FINAL}%"

DEPLOY_SIZE=$(du -sh "$DEPLOY_DIR" | awk '{print $1}')
log_info "Tamaño de la instalación: $DEPLOY_SIZE"

echo ""
echo "================================================"
echo -e "${GREEN}   ✅ DEPLOY COMPLETADO EXITOSAMENTE${NC}"
echo "================================================"
echo ""
echo "Servicios disponibles en:"
echo "  - Web: http://localhost:8000"
echo "  - Admin: http://localhost:8000/admin"
echo ""
echo "Para ver logs:"
echo "  docker-compose logs -f"
echo ""

