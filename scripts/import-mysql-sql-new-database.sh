#!/usr/bin/env bash
# Importa un archivo .sql a una base NUEVA en Synap_mysql57 (nunca reemplaza otra por defecto).
#
# Uso:
#   ./scripts/import-mysql-sql-new-database.sh /ruta/al/archivo.sql [nombre_base_mysql]
#
# Si omitís el nombre de base, se usa: administranet_import_YYYYMMDD_HHMMSS
#
# Para usar explícitamente la base "administranet" (riesgo de pisar datos):
#   ALLOW_OVERWRITE_ADMINISTRANET=1 ./scripts/import-mysql-sql-new-database.sh dump.sql administranet
#
# Variables:
#   CONTAINER (default Synap_mysql57)
#   MYSQL_USER / MYSQL_PASSWORD (default administranet / administranet_local)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SQL_PATH="${1:-}"
CONTAINER="${CONTAINER:-Synap_mysql57}"
MYSQL_USER="${MYSQL_USER:-administranet}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-administranet_local}"

if [ -z "$SQL_PATH" ] || [ ! -f "$SQL_PATH" ]; then
  echo "Uso: $0 /ruta/al/archivo.sql [nombre_base_mysql]"
  exit 1
fi

if [ -n "${2:-}" ]; then
  MYSQL_DATABASE="$2"
elif [ -n "${MYSQL_DATABASE:-}" ]; then
  : # ya definida en entorno
else
  MYSQL_DATABASE="administranet_import_$(date +%Y%m%d_%H%M%S)"
fi

if [ "$MYSQL_DATABASE" = "administranet" ] && [ "${ALLOW_OVERWRITE_ADMINISTRANET:-0}" != "1" ]; then
  echo "ERROR: Importar en la base «administranet» puede sobrescribir datos existentes."
  echo "Usá otro nombre (recomendado), por ejemplo:"
  echo "  $0 \"$SQL_PATH\" administranet_jesels_$(date +%Y%m%d)"
  echo "O, solo si es intencional:"
  echo "  ALLOW_OVERWRITE_ADMINISTRANET=1 $0 \"$SQL_PATH\" administranet"
  exit 1
fi

echo "Contenedor: $CONTAINER"
echo "Base nueva: $MYSQL_DATABASE"
echo "Archivo: $SQL_PATH"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "El contenedor $CONTAINER no está en ejecución. Levantalo con:"
  echo "  docker compose -f docker-compose.mysql.yml up -d"
  exit 1
fi

docker exec "$CONTAINER" mysql -uroot -proot_local -e "
  CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
  FLUSH PRIVILEGES;
"

echo "Importando (puede tardar varios minutos)..."
docker exec -i "$CONTAINER" mysql -uroot -proot_local "$MYSQL_DATABASE" < "$SQL_PATH"

echo "Listo."
echo "  host=127.0.0.1 port=3307 user=$MYSQL_USER database=$MYSQL_DATABASE"
echo "  Desde Synap_app (Docker): host=$CONTAINER port=3306 database=$MYSQL_DATABASE"
echo "Configurá base_empresa / conexión MySQL en .env para apuntar a este nombre de base si la app lo usa por nombre."
