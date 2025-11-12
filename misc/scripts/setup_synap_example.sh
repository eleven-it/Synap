#!/bin/bash

# Script de ejemplo para puesta en marcha inicial de Synap
# Este script muestra cómo ejecutar el comando de setup inicial

echo "🚀 Iniciando puesta en marcha de Synap..."

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: No se encontró manage.py. Asegúrate de estar en el directorio raíz del proyecto."
    exit 1
fi

# Opción 1: Setup completo (recomendado para primera vez)
echo "📋 Ejecutando setup completo..."
docker exec Synap_app python manage.py initial_setup

# Opción 2: Setup sin migraciones (si ya están aplicadas)
# echo "📋 Ejecutando setup sin migraciones..."
# docker exec Synap_app python manage.py initial_setup --skip-migrations

# Opción 3: Solo datos maestros (si ya hay usuarios y permisos)
# echo "📋 Ejecutando solo datos maestros..."
# docker exec Synap_app python manage.py initial_setup --skip-migrations --skip-users --skip-permissions

echo "✅ Puesta en marcha completada!"
echo ""
echo "📝 Próximos pasos:"
echo "1. Verificar que el sistema esté funcionando: http://localhost:8002"
echo "2. Crear un usuario administrador si no existe"
echo "3. Configurar la empresa principal"
echo "4. Revisar la configuración de impuestos y formas de pago"
echo ""
echo "🔧 Para crear un superusuario:"
echo "docker exec Synap_app python manage.py createsuperuser" 