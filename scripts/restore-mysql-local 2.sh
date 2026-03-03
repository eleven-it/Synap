#!/usr/bin/env bash
# Restaura el backup .zip de administraNET en el MySQL 5.7 local (contenedor).
# Uso:
#   ./scripts/restore-mysql-local.sh [ruta_al.zip]
# Ejemplo:
#   ./scripts/restore-mysql-local.sh backups/backup_administranet_Jesels_administranet_lunes_09_feb_2026__11_09.zip

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ZIP_PATH="${1:-$PROJECT_DIR/backups/backup_administranet_Jesels_administranet_lunes_09_feb_2026__11_09.zip}"
CONTAINER="${CONTAINER:-Synap_mysql57}"
MYSQL_USER="${MYSQL_USER:-administranet}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-administranet_local}"
MYSQL_DATABASE="${MYSQL_DATABASE:-administranet}"

if [ ! -f "$ZIP_PATH" ]; then
  echo "No se encuentra el backup: $ZIP_PATH"
  echo "Coloca el .zip en backups/ o pasa la ruta como argumento."
  exit 1
fi

echo "Backup: $ZIP_PATH"
echo "Contenedor: $CONTAINER"
echo "Base: $MYSQL_DATABASE"

# Comprobar que el contenedor está corriendo
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "Iniciando MySQL con docker compose..."
  (cd "$PROJECT_DIR" && docker compose -f docker-compose.mysql.yml up -d)
  echo "Esperando a que MySQL acepte conexiones..."
  sleep 5
  for i in {1..30}; do
    if docker exec "$CONTAINER" mysqladmin ping -h localhost -u root -proot_local --silent 2>/dev/null; then
      break
    fi
    sleep 2
  done
fi

RESTORE_DIR=$(mktemp -d)
trap "rm -rf $RESTORE_DIR" EXIT

echo "Descomprimiendo backup..."
unzip -o -q "$ZIP_PATH" -d "$RESTORE_DIR"

# Buscar archivo(s) .sql (puede ser uno o varios; algunos backups tienen .SQL en mayúscula)
SQL_FILES=()
while IFS= read -r -d '' f; do SQL_FILES+=("$f"); done < <(find "$RESTORE_DIR" -type f \( -name "*.sql" -o -name "*.SQL" \) -print0 | sort -z)

if [ ${#SQL_FILES[@]} -eq 0 ]; then
  echo "No se encontró ningún .sql dentro del zip."
  exit 1
fi

# Asegurar que la base existe
docker exec "$CONTAINER" mysql -uroot -proot_local -e "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\`; GRANT ALL ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;" 2>/dev/null || true

echo "Importando ${#SQL_FILES[@]} archivo(s) SQL..."
for sql in "${SQL_FILES[@]}"; do
  echo "  -> $(basename "$sql")"
  # Indicar la base para que no falle "No database selected" si el dump no trae USE
  docker exec -i "$CONTAINER" mysql -uroot -proot_local "$MYSQL_DATABASE" < "$sql"
done

echo "Restauración finalizada. Conexión local: host=127.0.0.1 port=3307 user=$MYSQL_USER database=$MYSQL_DATABASE"
