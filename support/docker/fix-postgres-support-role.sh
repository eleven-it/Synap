#!/usr/bin/env bash
# Reparar Postgres cuando ves: role "support" does not exist.
#
# El volumen de Postgres se inicializa solo la primera vez. Si alguna vez se creó
# con otras credenciales (ej. POSTGRES_USER=myuser), el rol "support" no existirá.
#
# Opción A (recomendada si no necesitás los datos): borrar volumen y recrear.
#   cd support/docker && docker compose down -v && docker compose up -d
#
# Opción B: si en el contenedor existe el superuser "postgres", este script crea support.
#   ./fix-postgres-support-role.sh
#
set -e
CONTAINER="${SUPPORT_DB_CONTAINER:-support_db}"

echo "Intentando crear rol/base 'support' en $CONTAINER..."

if ! docker exec "$CONTAINER" psql -U postgres -v ON_ERROR_STOP=1 -c "
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'support') THEN
    CREATE USER support WITH PASSWORD 'support' LOGIN;
    RAISE NOTICE 'Rol support creado.';
  ELSE
    RAISE NOTICE 'Rol support ya existe.';
  END IF;
END \$\$;
" 2>/dev/null; then
  echo ""
  echo "No se pudo conectar como 'postgres' (este volumen se creó con otro usuario)."
  echo "Solución: borrar el volumen y levantar de nuevo (se pierden datos de Support):"
  echo "  cd support/docker && docker compose down -v && docker compose up -d"
  echo ""
  exit 1
fi

docker exec "$CONTAINER" psql -U postgres -c "CREATE DATABASE support OWNER support;" 2>/dev/null || true
docker exec "$CONTAINER" psql -U postgres -d support -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

echo "Listo. Reiniciá el backend: docker compose restart backend"
exit 0
