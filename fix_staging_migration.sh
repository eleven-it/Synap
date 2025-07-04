#!/bin/bash

# Script para corregir datos en staging antes de aplicar la migración 0013
# Uso: ./fix_staging_migration.sh [--dry-run] [--empresa-id ID] [--branch-id ID]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
DRY_RUN=false
EMPRESA_ID=""
BRANCH_ID=""

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [OPCIONES]"
    echo ""
    echo "Opciones:"
    echo "  --dry-run           Ejecuta sin hacer cambios reales"
    echo "  --empresa-id ID     Usa una empresa específica por ID"
    echo "  --branch-id ID      Usa una sucursal específica por ID"
    echo "  --help              Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0                    # Ejecuta con la primera empresa/sucursal"
    echo "  $0 --dry-run          # Simula la ejecución"
    echo "  $0 --empresa-id 1     # Usa la empresa con ID 1"
    echo ""
}

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --empresa-id)
            EMPRESA_ID="$2"
            shift 2
            ;;
        --branch-id)
            BRANCH_ID="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Opción desconocida $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🚀 Script de corrección de datos para staging${NC}"
echo "=================================================="

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 MODO DRY-RUN: No se harán cambios reales${NC}"
fi

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: No se encontró manage.py. Ejecuta desde el directorio raíz del proyecto.${NC}"
    exit 1
fi

# Verificar que Docker esté corriendo
if ! docker ps | grep -q "Synap_app"; then
    echo -e "${RED}❌ Error: El contenedor Synap_app no está corriendo${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Contenedor Synap_app encontrado${NC}"

# Construir comando Django
DJANGO_CMD="python manage.py initialize_empresa_branch"

if [ "$DRY_RUN" = true ]; then
    DJANGO_CMD="$DJANGO_CMD --dry-run"
fi

if [ ! -z "$EMPRESA_ID" ]; then
    DJANGO_CMD="$DJANGO_CMD --empresa-id $EMPRESA_ID"
fi

if [ ! -z "$BRANCH_ID" ]; then
    DJANGO_CMD="$DJANGO_CMD --branch-id $BRANCH_ID"
fi

echo -e "${BLUE}📋 Comando a ejecutar:${NC}"
echo "  $DJANGO_CMD"
echo ""

# Confirmar ejecución
if [ "$DRY_RUN" = false ]; then
    echo -e "${YELLOW}⚠️  ADVERTENCIA: Esto modificará datos en la base de datos${NC}"
    read -p "¿Continuar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}❌ Operación cancelada${NC}"
        exit 0
    fi
fi

echo -e "${BLUE}🔄 Ejecutando comando...${NC}"
echo ""

# Ejecutar comando Django
if docker exec Synap_app bash -c "cd /app && $DJANGO_CMD"; then
    echo ""
    if [ "$DRY_RUN" = true ]; then
        echo -e "${GREEN}✅ DRY-RUN completado exitosamente${NC}"
        echo -e "${BLUE}💡 Ejecuta sin --dry-run para aplicar los cambios reales${NC}"
    else
        echo -e "${GREEN}✅ Corrección de datos completada exitosamente${NC}"
        echo ""
        echo -e "${BLUE}📋 Próximos pasos:${NC}"
        echo "  1. Verificar que no hay errores en el output anterior"
        echo "  2. Ejecutar: docker exec Synap_app python manage.py migrate"
        echo "  3. Verificar que la migración se aplica correctamente"
    fi
else
    echo ""
    echo -e "${RED}❌ Error durante la ejecución del comando${NC}"
    echo -e "${YELLOW}💡 Revisa el output anterior para más detalles${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🎉 Proceso completado${NC}" 