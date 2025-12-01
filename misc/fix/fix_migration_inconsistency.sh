#!/bin/bash
# Script para resolver inconsistencia de migraciones
# Resuelve dos problemas:
# 1. reports.0001_initial aplicada antes que core.0007_increase_permiso_codigo_length
# 2. reports.0001_initial marcada como aplicada pero las tablas no existen

echo "🔧 Resolviendo inconsistencias de migraciones..."

# Paso 1: Verificar y corregir tablas faltantes de reports
echo ""
echo "📋 Paso 1: Verificando tablas de reports..."
docker exec Synap_app python /app/misc/fix/fix_reports_tables_missing.py

# Paso 2: Corregir orden de migraciones
echo ""
echo "📋 Paso 2: Corrigiendo orden de migraciones..."
docker exec Synap_app python /app/misc/fix/fix_migration_order.py

if [ $? -eq 0 ]; then
    echo ""
    echo "📋 Paso 3: Aplicando migraciones pendientes..."
    docker exec Synap_app python manage.py migrate
    echo ""
    echo "✅ Migraciones resueltas"
else
    echo ""
    echo "❌ Error al corregir el orden. Intentando método alternativo..."
    
    # Opción alternativa: Deshacer reports.0001_initial y reaplicar
    echo "Deshaciendo reports.0001_initial (fake)..."
    docker exec Synap_app python manage.py migrate reports zero --fake
    
    echo "Aplicando core.0007_increase_permiso_codigo_length (fake)..."
    docker exec Synap_app python manage.py migrate core 0007_increase_permiso_codigo_length --fake
    
    echo "Aplicando reports.0001_initial realmente..."
    docker exec Synap_app python manage.py migrate reports 0001_initial
    
    echo "Aplicando todas las migraciones pendientes..."
    docker exec Synap_app python manage.py migrate
    echo "✅ Migraciones resueltas"
fi

