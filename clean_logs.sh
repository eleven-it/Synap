#!/bin/bash

# Script para limpiar logs de Synap
# Uso: ./clean_logs.sh [opción]

echo "🧹 Limpiador de Logs - Synap"
echo "=============================="

case "${1:-help}" in
    "container")
        echo "🗑️  Limpiando logs del contenedor Synap_app..."
        docker logs Synap_app > /dev/null 2>&1
        echo "✅ Logs del contenedor limpiados"
        ;;
    "all")
        echo "🗑️  Limpiando todos los logs de Docker..."
        docker system prune -f
        echo "✅ Todos los logs limpiados"
        ;;
    "restart")
        echo "🔄 Reiniciando contenedor para limpiar logs..."
        docker restart Synap_app
        echo "✅ Contenedor reiniciado y logs limpiados"
        ;;
    "view")
        echo "📋 Mostrando últimos 50 logs..."
        docker logs Synap_app --tail 50
        ;;
    "follow")
        echo "👀 Siguiendo logs en tiempo real (Ctrl+C para salir)..."
        docker logs Synap_app -f
        ;;
    "help"|*)
        echo "Opciones disponibles:"
        echo "  container  - Limpiar logs del contenedor Synap_app"
        echo "  all        - Limpiar todos los logs de Docker"
        echo "  restart    - Reiniciar contenedor (limpia logs)"
        echo "  view       - Ver últimos 50 logs"
        echo "  follow     - Seguir logs en tiempo real"
        echo ""
        echo "Ejemplos:"
        echo "  ./clean_logs.sh container"
        echo "  ./clean_logs.sh view"
        echo "  ./clean_logs.sh follow"
        ;;
esac 