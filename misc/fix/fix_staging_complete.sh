#!/bin/bash

# Script completo para corregir datos en staging
# Incluye creación de empresa/sucursal si no existen
# Uso: ./fix_staging_complete.sh [--dry-run] [--empresa-nombre "Nombre"] [--branch-nombre "Nombre"]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
DRY_RUN=false
EMPRESA_NOMBRE="Empresa Staging"
EMPRESA_IDENTIFICADOR="STAGING-001"
BRANCH_NOMBRE="Sucursal Principal"
BRANCH_CODIGO="STAGING-BRANCH-001"

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [OPCIONES]"
    echo ""
    echo "Opciones:"
    echo "  --dry-run                    Ejecuta sin hacer cambios reales"
    echo "  --empresa-nombre \"NOMBRE\"    Nombre de la empresa a crear"
    echo "  --empresa-identificador \"ID\" Identificador fiscal de la empresa"
    echo "  --branch-nombre \"NOMBRE\"     Nombre de la sucursal a crear"
    echo "  --branch-codigo \"CODIGO\"     Código interno de la sucursal"
    echo "  --help                       Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0                           # Ejecuta con valores por defecto"
    echo "  $0 --dry-run                 # Simula la ejecución"
    echo "  $0 --empresa-nombre \"Mi Empresa\" --branch-nombre \"Sucursal Central\""
    echo ""
}

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --empresa-nombre)
            EMPRESA_NOMBRE="$2"
            shift 2
            ;;
        --empresa-identificador)
            EMPRESA_IDENTIFICADOR="$2"
            shift 2
            ;;
        --branch-nombre)
            BRANCH_NOMBRE="$2"
            shift 2
            ;;
        --branch-codigo)
            BRANCH_CODIGO="$2"
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

echo -e "${BLUE}🚀 Script completo de corrección para staging${NC}"
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

# Paso 1: Verificar si existe empresa
echo -e "${BLUE}📋 Paso 1: Verificando empresa existente...${NC}"
EMPRESA_EXISTS=$(docker exec Synap_app python manage.py shell -c "
from core.models import Empresa
empresa = Empresa.objects.first()
if empresa:
    print(f'EXISTS:{empresa.id}:{empresa.nombre}')
else:
    print('NOT_EXISTS')
" 2>/dev/null | tail -1)

if [[ $EMPRESA_EXISTS == "NOT_EXISTS" ]]; then
    echo -e "${YELLOW}⚠️  No se encontró empresa existente${NC}"
    CREATE_EMPRESA=true
else
    echo -e "${GREEN}✅ Empresa existente encontrada${NC}"
    IFS=':' read -r EXISTS EMPRESA_ID EMPRESA_NOMBRE_EXISTING <<< "$EMPRESA_EXISTS"
    echo -e "${BLUE}   🏢 ID: $EMPRESA_ID, Nombre: $EMPRESA_NOMBRE_EXISTING${NC}"
    CREATE_EMPRESA=false
fi

# Paso 2: Verificar si existe sucursal
echo -e "${BLUE}📋 Paso 2: Verificando sucursal existente...${NC}"
BRANCH_EXISTS=$(docker exec Synap_app python manage.py shell -c "
from core.models import Empresa, Branch
empresa = Empresa.objects.first()
if empresa:
    branch = Branch.objects.filter(empresa=empresa).first()
    if branch:
        print(f'EXISTS:{branch.id}:{branch.name}')
    else:
        print('NOT_EXISTS')
else:
    print('NO_EMPRESA')
" 2>/dev/null | tail -1)

if [[ $BRANCH_EXISTS == "NOT_EXISTS" ]] || [[ $BRANCH_EXISTS == "NO_EMPRESA" ]]; then
    echo -e "${YELLOW}⚠️  No se encontró sucursal existente${NC}"
    CREATE_BRANCH=true
else
    echo -e "${GREEN}✅ Sucursal existente encontrada${NC}"
    IFS=':' read -r EXISTS BRANCH_ID BRANCH_NOMBRE_EXISTING <<< "$BRANCH_EXISTS"
    echo -e "${BLUE}   🏪 ID: $BRANCH_ID, Nombre: $BRANCH_NOMBRE_EXISTING${NC}"
    CREATE_BRANCH=false
fi

# Construir comandos
CREATE_CMD="python manage.py create_default_empresa"
if [ "$DRY_RUN" = true ]; then
    CREATE_CMD="$CREATE_CMD --dry-run"
fi
CREATE_CMD="$CREATE_CMD --empresa-nombre \"$EMPRESA_NOMBRE\" --empresa-identificador \"$EMPRESA_IDENTIFICADOR\" --branch-nombre \"$BRANCH_NOMBRE\" --branch-codigo \"$BRANCH_CODIGO\""

INIT_CMD="python manage.py initialize_empresa_branch"
if [ "$DRY_RUN" = true ]; then
    INIT_CMD="$INIT_CMD --dry-run"
fi

echo ""
echo -e "${BLUE}📋 Comandos a ejecutar:${NC}"
if [ "$CREATE_EMPRESA" = true ] || [ "$CREATE_BRANCH" = true ]; then
    echo "  1. $CREATE_CMD"
fi
echo "  2. $INIT_CMD"
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

# Paso 3: Crear empresa/sucursal si es necesario
if [ "$CREATE_EMPRESA" = true ] || [ "$CREATE_BRANCH" = true ]; then
    echo -e "${BLUE}🔄 Paso 3: Creando empresa y sucursal...${NC}"
    echo ""
    
    if docker exec Synap_app bash -c "cd /app && $CREATE_CMD"; then
        echo -e "${GREEN}✅ Empresa y sucursal creadas/verificadas exitosamente${NC}"
    else
        echo -e "${RED}❌ Error al crear empresa y sucursal${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Paso 3: Empresa y sucursal ya existen, saltando creación${NC}"
fi

# Paso 4: Inicializar datos
echo -e "${BLUE}🔄 Paso 4: Inicializando empresa_id y branch_id...${NC}"
echo ""

if docker exec Synap_app bash -c "cd /app && $INIT_CMD"; then
    echo -e "${GREEN}✅ Inicialización de datos completada exitosamente${NC}"
else
    echo -e "${RED}❌ Error durante la inicialización de datos${NC}"
    exit 1
fi

# Paso 5: Verificación final
echo -e "${BLUE}📋 Paso 5: Verificación final...${NC}"
echo ""

VERIFICATION_CMD="python manage.py shell -c \"
from core.models import Empresa, Branch
from inventory.models import Warehouse, Location, Product, StockLot, StockQuant, StockMove, InventoryAdjustment, StockReservation, ReplenishmentRule, InitialStockDraft, InitialStockDraftItem

empresa = Empresa.objects.first()
branch = Branch.objects.filter(empresa=empresa).first()

print(f'Empresa: {empresa.nombre if empresa else \"No encontrada\"} (ID: {empresa.id if empresa else \"N/A\"})')
print(f'Sucursal: {branch.name if branch else \"No encontrada\"} (ID: {branch.id if branch else \"N/A\"})')

models = [Warehouse, Location, Product, StockLot, StockQuant, StockMove, InventoryAdjustment, StockReservation, ReplenishmentRule, InitialStockDraft, InitialStockDraftItem]

print('\\nVerificación de registros nulos:')
all_ok = True
for model in models:
    empresa_nulos = model.objects.filter(empresa__isnull=True).count()
    branch_nulos = model.objects.filter(branch__isnull=True).count()
    if empresa_nulos == 0 and branch_nulos == 0:
        print(f'  ✅ {model.__name__}: OK')
    else:
        print(f'  ❌ {model.__name__}: {empresa_nulos} empresa_id nulos, {branch_nulos} branch_id nulos')
        all_ok = False

if all_ok:
    print('\\n🎉 TODOS LOS MODELOS ESTÁN CORRECTOS')
else:
    print('\\n⚠️  HAY REGISTROS NULOS QUE NECESITAN ATENCIÓN')
\""

docker exec Synap_app bash -c "cd /app && $VERIFICATION_CMD"

echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${GREEN}✅ DRY-RUN completado exitosamente${NC}"
    echo -e "${BLUE}💡 Ejecuta sin --dry-run para aplicar los cambios reales${NC}"
else
    echo -e "${GREEN}✅ Corrección completa finalizada exitosamente${NC}"
    echo ""
    echo -e "${BLUE}📋 Próximos pasos:${NC}"
    echo "  1. Verificar que no hay errores en el output anterior"
    echo "  2. Ejecutar: sudo docker exec Synap_app python manage.py migrate"
    echo "  3. Verificar que la migración se aplica correctamente"
fi

echo ""
echo -e "${BLUE}🎉 Proceso completado${NC}" 