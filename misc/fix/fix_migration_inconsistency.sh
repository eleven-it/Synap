#!/bin/bash
# Script para resolver inconsistencia de migraciones
# Cuando reports.0001_initial está aplicada pero core.0007_increase_permiso_codigo_length no

echo "🔧 Resolviendo inconsistencia de migraciones..."

# Opción 1: Usar script Python para corregir el orden en la base de datos
echo "Corrigiendo orden de migraciones en la base de datos..."
docker exec Synap_app python /app/misc/fix/fix_migration_order.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Aplicando migraciones pendientes..."
    docker exec Synap_app python manage.py migrate
    echo "✅ Migraciones resueltas"
else
    echo ""
    echo "❌ Error al corregir el orden. Intentando método alternativo..."
    
    # Opción 2: Deshacer reports.0001_initial y reaplicar
    echo "Deshaciendo reports.0001_initial (fake)..."
    docker exec Synap_app python manage.py migrate reports 0001_initial --fake
    
    echo "Aplicando core.0007_increase_permiso_codigo_length (fake)..."
    docker exec Synap_app python manage.py migrate core 0007_increase_permiso_codigo_length --fake
    
    echo "Reaplicando reports.0001_initial (fake)..."
    docker exec Synap_app python manage.py migrate reports 0001_initial --fake
    
    echo "Aplicando todas las migraciones pendientes..."
    docker exec Synap_app python manage.py migrate
    echo "✅ Migraciones resueltas"
fi

