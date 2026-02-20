#!/usr/bin/env bash
# Descarga la base `empresas` del servidor remoto y la restaura en MySQL local.
# Uso:
#   ./scripts/pull-empresas-from-remote.sh
#
# Variables de entorno (opcionales):
#   REMOTE_DB_HOST, REMOTE_DB_PORT, REMOTE_DB_USER, REMOTE_DB_PASSWORD
#   LOCAL_DB_HOST, LOCAL_DB_PORT, LOCAL_DB_USER, LOCAL_DB_PASSWORD
#   MYSQL_CONTAINER (para importar vía docker exec)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Remote (servidor administraNET)
REMOTE_HOST="${REMOTE_DB_HOST:-190.15.214.142}"
REMOTE_PORT="${REMOTE_DB_PORT:-3306}"
REMOTE_USER="${REMOTE_DB_USER:-administranet}"
REMOTE_PASSWORD="${REMOTE_DB_PASSWORD:-a7v8xx0805}"
REMOTE_DB="${REMOTE_DB_NAME:-empresas}"

# Local (contenedor MySQL o host)
LOCAL_HOST="${LOCAL_DB_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_DB_PORT:-3307}"
LOCAL_USER="${LOCAL_DB_USER:-administranet}"
LOCAL_PASSWORD="${LOCAL_DB_PASSWORD:-administranet_local}"
LOCAL_DB="empresas"
CONTAINER="${MYSQL_CONTAINER:-Synap_mysql57}"

DUMP_FILE="$PROJECT_DIR/backups/empresas_dump.sql"

echo "📥 Descargando base '$REMOTE_DB' de $REMOTE_HOST:$REMOTE_PORT..."
echo "   Usuario: $REMOTE_USER"

# Cargar .env si existe (para sobrescribir LOCAL_*)
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env" 2>/dev/null || true
  set +a
  LOCAL_PORT="${DB_PORT:-$LOCAL_PORT}"
  LOCAL_USER="${DB_USER:-$LOCAL_USER}"
  LOCAL_PASSWORD="${DB_PASSWORD:-$LOCAL_PASSWORD}"
fi

# Crear directorio backups si no existe
mkdir -p "$PROJECT_DIR/backups"

# mysqldump: usar el del contenedor MySQL 5.7 si está corriendo
# (evita error "mysql_native_password cannot be loaded" con MySQL 9 client en host)
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
  echo "   Usando mysqldump del contenedor (MySQL 5.7, compatible con mysql_native_password)"
  docker exec "$CONTAINER" mysqldump -h"$REMOTE_HOST" -P"$REMOTE_PORT" -u"$REMOTE_USER" -p"$REMOTE_PASSWORD" \
    --single-transaction --routines --triggers --set-gtid-purged=OFF \
    "$REMOTE_DB" > "$DUMP_FILE"
else
  mysqldump -h"$REMOTE_HOST" -P"$REMOTE_PORT" -u"$REMOTE_USER" -p"$REMOTE_PASSWORD" \
    --single-transaction --routines --triggers --set-gtid-purged=OFF \
    "$REMOTE_DB" > "$DUMP_FILE"
fi

echo "✅ Dump guardado en $DUMP_FILE"

# Crear base empresas si no existe e importar
echo "📤 Importando en MySQL local ($LOCAL_HOST:$LOCAL_PORT)..."

if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
  echo "   Usando contenedor: $CONTAINER"
  docker exec "$CONTAINER" mysql -uroot -proot_local -e "CREATE DATABASE IF NOT EXISTS \`$LOCAL_DB\`; GRANT ALL ON \`$LOCAL_DB\`.* TO '$LOCAL_USER'@'%'; FLUSH PRIVILEGES;" 2>/dev/null || true
  # Importar como root para evitar "Access denied; need SUPER" (DEFINER, triggers, etc.)
  docker exec -i "$CONTAINER" mysql -uroot -proot_local "$LOCAL_DB" < "$DUMP_FILE"
else
  mysql -h"$LOCAL_HOST" -P"$LOCAL_PORT" -u"$LOCAL_USER" -p"$LOCAL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS \`$LOCAL_DB\`;" 2>/dev/null || true
  mysql -h"$LOCAL_HOST" -P"$LOCAL_PORT" -u"$LOCAL_USER" -p"$LOCAL_PASSWORD" "$LOCAL_DB" < "$DUMP_FILE"
fi

echo "✅ Base '$LOCAL_DB' restaurada en local. Ya puedes usar el login con la misma lista de empresas que en el servidor remoto."
