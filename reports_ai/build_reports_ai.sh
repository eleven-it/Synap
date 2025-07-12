#!/bin/bash

echo "🚀 Construyendo microservicio de IA con imagen base optimizada..."

# Opciones disponibles
echo "Selecciona la versión de PyTorch:"
echo "1) PyTorch CPU (recomendado para desarrollo)"
echo "2) PyTorch CUDA (para GPU)"
echo "3) Cancelar"

read -p "Opción (1-3): " choice

case $choice in
    1)
        echo "📦 Construyendo con PyTorch CPU..."
        # Usar imagen CPU
        sed -i.bak 's|FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime|FROM pytorch/pytorch:2.0.1-cpu|' reports_ai/Dockerfile
        docker-compose build reports-ai
        # Restaurar configuración original
        mv reports_ai/Dockerfile.bak reports_ai/Dockerfile 2>/dev/null || true
        ;;
    2)
        echo "📦 Construyendo con PyTorch CUDA..."
        # Usar imagen CUDA (configuración por defecto)
        docker-compose build reports-ai
        ;;
    3)
        echo "❌ Construcción cancelada"
        exit 0
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo "✅ Microservicio de IA construido exitosamente!"
    echo "🌐 URL del servicio: http://localhost:8003"
    echo "📊 Vector DB: http://localhost:6333"
    
    echo ""
    echo "Para iniciar el servicio completo:"
    echo "docker-compose up reports-ai qdrant"
    
    echo ""
    echo "Para verificar que funciona:"
    echo "curl http://localhost:8003/health"
else
    echo "❌ Error en la construcción"
    exit 1
fi 