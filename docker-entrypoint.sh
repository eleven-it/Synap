#!/bin/bash
set -e

echo "🚀 Iniciando Synap..."

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

echo ""
echo "📦 Aplicando migraciones..."

# Detectar base PostgreSQL vacía (sin tabla django_migrations)
FRESH_DB=$(python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"\"\"
    SELECT NOT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'django_migrations'
    );
\"\"\")
print('YES' if cursor.fetchone()[0] else 'NO')
cursor.close()
" 2>/dev/null | tail -1)

if [ "$FRESH_DB" = "YES" ]; then
    echo "🆕 Instalación nueva detectada (PostgreSQL sin django_migrations)"
else
    echo "🔍 Base existente: verificando migraciones de reports..."
    python manage.py fix_reports_migrations --force 2>&1 || {
        echo "⚠️  Advertencia: Error al corregir migraciones de reports, continuando..."
    }

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
        echo "⚠️  Tabla reports_reportdefinition NO existe, intentando reparar..."
        python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"DELETE FROM django_migrations WHERE app = 'reports'\")
print(f'Eliminadas {cursor.rowcount} entradas de migraciones de reports')
cursor.close()
" 2>&1 || true
        python manage.py migrate reports 0001_initial --noinput 2>&1 || {
            echo "❌ Error al aplicar migración inicial de reports"
            exit 1
        }
    fi
fi

# Migraciones completas (SYNAP_MIGRATIONS_POSTGRES_ONLY evita fallos con MySQL legacy)
export SYNAP_MIGRATIONS_POSTGRES_ONLY="${SYNAP_MIGRATIONS_POSTGRES_ONLY:-1}"
echo "📋 Ejecutando migrate (Postgres)..."
python manage.py migrate --noinput || {
    echo "❌ Error al aplicar migraciones"
    exit 1
}

if [ "$FRESH_DB" = "YES" ]; then
    echo ""
    echo "🔧 Bootstrap de primera instalación (core, login, dashboard, reports)..."
    python manage.py bootstrap_instalacion || {
        echo "⚠️  Advertencia: bootstrap_instalacion falló parcialmente"
        echo "   Ejecutar manualmente: python manage.py bootstrap_instalacion --force"
    }
else
    echo ""
    echo "🔧 Verificando módulo Reports..."
    python manage.py setup_reports_installation --skip-migrations || {
        echo "⚠️  Advertencia: No se pudo configurar Reports automáticamente"
    }
    # Reparar cadena mínima si algún módulo base quedó inactivo
    python manage.py bootstrap_instalacion 2>&1 || true
fi

# Recolectar archivos estáticos
if [ "$COLLECTSTATIC" != "false" ]; then
    echo ""
    echo "📁 Recolectando archivos estáticos..."
    _out=$(mktemp)
    if python manage.py collectstatic --noinput > "$_out" 2>&1; then
        grep -v "Found another file" "$_out" || true
    else
        grep -v "Found another file" "$_out" || true
        echo "⚠️  Advertencia: Error al recolectar archivos estáticos"
    fi
    rm -f "$_out"
fi

echo ""
echo "✅ Inicialización completada"
echo "🚀 Iniciando servidor..."
exec "$@"
