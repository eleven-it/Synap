#!/bin/bash

# Script para limpiar el servidor de producción existente
# Elimina archivos innecesarios y libera espacio en disco

set -e

echo "================================================"
echo "   LIMPIEZA DE SERVIDOR DE PRODUCCIÓN - SYNAP"
echo "================================================"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Variables
SYNAP_DIR="/home/sparedes/Synap"

# Verificar que estamos en el directorio correcto
if [ ! -d "$SYNAP_DIR" ]; then
    echo -e "${RED}Error: Directorio $SYNAP_DIR no encontrado${NC}"
    exit 1
fi

cd "$SYNAP_DIR"

# Mostrar uso inicial
echo ""
log_info "Uso de disco ANTES de la limpieza:"
df -h / | grep -E "Filesystem|/$"
echo ""
log_info "Tamaño de Synap ANTES: $(du -sh . | awk '{print $1}')"
echo ""

# 1. Eliminar administraNET_Limpio (264 MB)
echo ""
log_info "1. Eliminando fuentes de AdministraNET..."
if [ -d "administraNET_Limpio" ]; then
    rm -rf administraNET_Limpio
    log_info "✓ administraNET_Limpio eliminado"
fi

if [ -f "administraNET_Limpio.zip" ]; then
    rm -f administraNET_Limpio.zip
    log_info "✓ administraNET_Limpio.zip eliminado"
fi

# 2. Eliminar media_bak
echo ""
log_info "2. Eliminando backups antiguos de media..."
if [ -d "media_bak" ]; then
    rm -rf media_bak
    log_info "✓ media_bak eliminado"
fi

# 3. Eliminar documentación
echo ""
log_info "3. Eliminando documentación (solo para desarrollo)..."
if [ -d "misc/documentacion" ]; then
    rm -rf misc/documentacion
    log_info "✓ misc/documentacion eliminado"
fi

# 4. Eliminar scripts de fix
echo ""
log_info "4. Eliminando scripts de fix..."
if [ -d "misc/fix" ]; then
    rm -rf misc/fix
    log_info "✓ misc/fix eliminado"
fi

# 5. Eliminar tests
echo ""
log_info "5. Eliminando tests..."
if [ -d "misc/test" ]; then
    rm -rf misc/test
    log_info "✓ misc/test eliminado"
fi

# 6. Eliminar scripts no críticos
echo ""
log_info "6. Eliminando scripts no críticos..."
if [ -d "misc/scripts" ]; then
    # Mantener solo deploy_production.sh y clean_production_server.sh
    cd misc/scripts
    for file in *; do
        if [ "$file" != "deploy_production.sh" ] && [ "$file" != "clean_production_server.sh" ]; then
            rm -f "$file"
        fi
    done
    cd ../..
    log_info "✓ Scripts no críticos eliminados"
fi

# 7. Eliminar archivos de desarrollo
echo ""
log_info "7. Eliminando archivos de desarrollo..."
find . -type f -name "test_*.py" -delete
find . -type f -name "debug_*.py" -delete
find . -type f -name "investigate_*.py" -delete
find . -type f -name "build_*.sh" -delete
find . -type f -name "*.md" -delete
find . -type f -name ".DS_Store" -delete
find . -type f -name "*.backup" -delete
find . -type f -name "*.bak" -delete
log_info "✓ Archivos de desarrollo eliminados"

# 8. Limpiar archivos Python compilados
echo ""
log_info "8. Eliminando archivos Python compilados..."
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
log_info "✓ Archivos .pyc y __pycache__ eliminados"

# 9. Limpiar logs antiguos
echo ""
log_info "9. Limpiando logs antiguos..."
if [ -d "logs" ]; then
    find logs -type f -name "*.log" -mtime +30 -delete
    log_info "✓ Logs antiguos (>30 días) eliminados"
fi

# 10. Limpiar archivos temporales
echo ""
log_info "10. Limpiando archivos temporales..."
find . -type f -name "*.tmp" -delete
find . -type f -name "*.temp" -delete
log_info "✓ Archivos temporales eliminados"

# 11. Limpiar Git
echo ""
log_info "11. Optimizando repositorio Git..."
git gc --aggressive --prune=now 2>/dev/null || log_warn "Git GC falló (puede requerir más espacio temporal)"

# 12. Limpiar Docker (si hay permisos)
echo ""
log_info "12. Limpiando Docker..."
sudo docker system prune -af || log_warn "Limpieza de Docker requiere permisos sudo"

# Mostrar uso final
echo ""
echo "================================================"
log_info "RESULTADOS DE LA LIMPIEZA"
echo "================================================"
echo ""
log_info "Uso de disco DESPUÉS de la limpieza:"
df -h / | grep -E "Filesystem|/$"
echo ""
log_info "Tamaño de Synap DESPUÉS: $(du -sh . | awk '{print $1}')"
echo ""

# Calcular espacio liberado
echo ""
echo "================================================"
echo -e "${GREEN}   ✅ LIMPIEZA COMPLETADA EXITOSAMENTE${NC}"
echo "================================================"
echo ""
echo "Archivos eliminados:"
echo "  ✓ Fuentes de AdministraNET (~264 MB)"
echo "  ✓ Media backups"
echo "  ✓ Documentación de desarrollo"
echo "  ✓ Scripts de fix y test"
echo "  ✓ Archivos de desarrollo"
echo "  ✓ Archivos compilados de Python"
echo "  ✓ Logs antiguos"
echo "  ✓ Archivos temporales"
echo ""
echo "El sistema de producción está ahora optimizado."
echo ""

