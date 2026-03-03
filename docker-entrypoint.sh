#!/bin/bash
set -e

echo "🚀 Iniciando Synap Reports..."

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a que PostgreSQL esté listo..."
until python manage.py shell -c "from django.db import connection; connection.ensure_connection()" 2>/dev/null; do
    echo "   PostgreSQL no está listo, esperando..."
    sleep 2
done
echo "✅ PostgreSQL está listo"

# Esperar a que Redis esté listo
echo "⏳ Esperando a que Redis esté listo..."
until python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0); r.ping()" 2>/dev/null; do
    echo "   Redis no está listo, esperando..."
    sleep 2
done
echo "✅ Redis está listo"

# Ejecutar migraciones automáticamente
echo ""
echo "📦 Aplicando migraciones..."

# SIEMPRE ejecutar fix_reports_migrations primero para limpiar migraciones huérfanas
# Esto es necesario porque pueden existir migraciones que no están en el código
# (como 0017 que intenta agregar is_visible que ya existe)
echo "🔍 Verificando y corrigiendo estado de migraciones de reports..."
python manage.py fix_reports_migrations --force 2>&1 || {
    echo "⚠️  Advertencia: Error al corregir migraciones, continuando de todas formas..."
}

# Verificar si la tabla reports_reportdefinition existe después de la corrección
echo "🔍 Verificando estado de migraciones de reports..."
TABLE_EXISTS=$(python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"\"\"
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'reports_reportdefinition'
    );
\"\"\")
result = cursor.fetchone()[0]
cursor.close()
print('YES' if result else 'NO')
" 2>&1 | tail -1)

if [ "$TABLE_EXISTS" = "YES" ]; then
    echo "✅ Tabla reports_reportdefinition existe"
else
    echo "⚠️  Tabla reports_reportdefinition NO existe, intentando crear..."
    # Eliminar entradas de migraciones de reports si existen
    python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"DELETE FROM django_migrations WHERE app = 'reports'\")
print(f'Eliminadas {cursor.rowcount} entradas de migraciones de reports')
cursor.close()
" 2>&1
    # Aplicar migración inicial explícitamente
    echo "   Aplicando migración 0001_initial..."
    python manage.py migrate reports 0001_initial --noinput 2>&1 || {
        echo "❌ Error al aplicar migración inicial"
        exit 1
    }
fi

# Aplicar todas las migraciones restantes
echo "📋 Aplicando migraciones restantes..."
python manage.py migrate --noinput || {
    echo "❌ Error al aplicar migraciones"
    exit 1
}

# Configurar instalación de Reports
echo ""
echo "🔧 Configurando módulo Reports..."
# No usar --skip-migrations para que el comando pueda aplicar 0001_initial si es necesario
python manage.py setup_reports_installation || {
    echo "⚠️  Advertencia: No se pudo configurar Reports automáticamente"
    echo "   Puedes ejecutar manualmente: python manage.py setup_reports_installation"
}

# Recolectar archivos estáticos (si es necesario)
if [ "$COLLECTSTATIC" != "false" ]; then
    echo ""
    echo "📁 Recolectando archivos estáticos..."
    python manage.py collectstatic --noinput || echo "⚠️  Advertencia: Error al recolectar archivos estáticos"
fi

# Ejecutar el comando pasado como argumento
echo ""
echo "✅ Inicialización completada"
echo "🚀 Iniciando servidor..."
exec "$@"

