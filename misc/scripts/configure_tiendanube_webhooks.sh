#!/bin/bash

# =============================================================================
# Script para Configurar Webhooks de TiendaNube
# =============================================================================
# 
# IMPORTANTE: Según la documentación oficial de TiendaNube,
# los webhooks están disponibles automáticamente y se configuran vía API.
#
# Documentación: https://tiendanube.github.io/api-documentation/webhooks/
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración (CAMBIAR ESTOS VALORES)
STORE_ID="TU_STORE_ID"
ACCESS_TOKEN="TU_ACCESS_TOKEN"
WEBHOOK_URL="https://tu-dominio.com/tiendanube-adminet/webhook/"

# Función para mostrar mensajes
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

# Verificar configuración
check_config() {
    if [ "$STORE_ID" = "TU_STORE_ID" ] || [ "$ACCESS_TOKEN" = "TU_ACCESS_TOKEN" ] || [ "$WEBHOOK_URL" = "https://tu-dominio.com/tiendanube-adminet/webhook/" ]; then
        print_error "Por favor, configura las variables al inicio del script:"
        print_error "  - STORE_ID: Tu ID de tienda"
        print_error "  - ACCESS_TOKEN: Tu token de acceso"
        print_error "  - WEBHOOK_URL: La URL de tu webhook"
        exit 1
    fi
}

# Función para crear un webhook
create_webhook() {
    local event=$1
    local description=$2
    
    print_message "Creando webhook para: $event"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "https://api.tiendanube.com/2025-03/${STORE_ID}/webhooks" \
        -H "Authentication: bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "User-Agent: Synap-Administranet/1.0" \
        -d "{
            \"url\": \"${WEBHOOK_URL}\",
            \"event\": \"${event}\"
        }")
    
    # Extraer código de respuesta
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        print_success "✅ Webhook $event creado exitosamente"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        print_error "❌ Error creando webhook $event (HTTP $http_code)"
        echo "$body"
    fi
    
    echo ""
}

# Función para listar webhooks existentes
list_webhooks() {
    print_message "Listando webhooks existentes..."
    
    response=$(curl -s -w "\n%{http_code}" -X GET \
        "https://api.tiendanube.com/2025-03/${STORE_ID}/webhooks" \
        -H "Authentication: bearer ${ACCESS_TOKEN}" \
        -H "User-Agent: Synap-Administranet/1.0")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Webhooks existentes:"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        print_error "Error listando webhooks (HTTP $http_code)"
        echo "$body"
    fi
    
    echo ""
}

# Función para probar un webhook
test_webhook() {
    local webhook_id=$1
    
    if [ -z "$webhook_id" ]; then
        print_error "ID de webhook requerido para la prueba"
        return 1
    fi
    
    print_message "Probando webhook ID: $webhook_id"
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "https://api.tiendanube.com/2025-03/${STORE_ID}/webhooks/${webhook_id}/test" \
        -H "Authentication: bearer ${ACCESS_TOKEN}" \
        -H "User-Agent: Synap-Administranet/1.0")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        print_success "✅ Webhook probado exitosamente"
        echo "$body"
    else
        print_error "❌ Error probando webhook (HTTP $http_code)"
        echo "$body"
    fi
    
    echo ""
}

# Función principal
main() {
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                    📡 CONFIGURADOR DE WEBHOOKS TIENDANUBE                   ║"
    echo "║                        (Basado en documentación oficial)                     ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Verificar configuración
    check_config
    
    print_message "Configuración:"
    print_message "  Store ID: $STORE_ID"
    print_message "  Webhook URL: $WEBHOOK_URL"
    print_message "  Access Token: ${ACCESS_TOKEN:0:10}..."
    echo ""
    
    # Listar webhooks existentes
    list_webhooks
    
    # Crear webhooks para eventos de órdenes
    print_message "Creando webhooks para eventos de órdenes..."
    echo ""
    
    # Eventos de órdenes (en orden de importancia)
    create_webhook "order/paid" "Webhook CRÍTICO - Crea pedido en AdministraNET cuando se paga"
    create_webhook "order/created" "Registra órdenes creadas"
    create_webhook "order/updated" "Actualiza cambios en órdenes"
    create_webhook "order/fulfilled" "Registra órdenes entregadas"
    create_webhook "order/cancelled" "Anula órdenes canceladas"
    
    # Listar webhooks después de la creación
    print_message "Verificando webhooks creados..."
    list_webhooks
    
    print_success "🎉 Configuración de webhooks completada!"
    echo ""
    print_message "Próximos pasos:"
    print_message "1. Verifica que tu endpoint esté funcionando: $WEBHOOK_URL"
    print_message "2. Crea una orden de prueba en tu tienda"
    print_message "3. Verifica los logs en Synap: docker logs -f Synap_app | grep webhook"
    print_message "4. Revisa el dashboard: http://tu-dominio.com/tiendanube-adminet/"
    echo ""
    print_warning "IMPORTANTE: El webhook 'order/paid' es el más crítico -"
    print_warning "este es el que crea automáticamente el pedido en AdministraNET"
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [opción]"
    echo ""
    echo "Opciones:"
    echo "  -h, --help     Mostrar esta ayuda"
    echo "  -l, --list     Listar webhooks existentes"
    echo "  -t ID, --test ID  Probar webhook por ID"
    echo "  -c, --create   Crear todos los webhooks (por defecto)"
    echo ""
    echo "Ejemplos:"
    echo "  $0                    # Crear todos los webhooks"
    echo "  $0 --list            # Listar webhooks existentes"
    echo "  $0 --test 12345      # Probar webhook con ID 12345"
    echo ""
    echo "Configuración:"
    echo "  Edita las variables al inicio del script:"
    echo "    STORE_ID, ACCESS_TOKEN, WEBHOOK_URL"
}

# Procesar argumentos
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -l|--list)
        check_config
        list_webhooks
        exit 0
        ;;
    -t|--test)
        check_config
        test_webhook "$2"
        exit 0
        ;;
    -c|--create|"")
        main
        exit 0
        ;;
    *)
        print_error "Opción desconocida: $1"
        show_help
        exit 1
        ;;
esac



