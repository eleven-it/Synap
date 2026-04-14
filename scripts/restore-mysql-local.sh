#!/usr/bin/env bash
# Restaura el backup .zip de administraNET en el MySQL 5.7 local (contenedor).
#
# Política: siempre se importa a una base NUEVA (o a un nombre que elijas), nunca se hace
# DROP de «administranet» ni de otras bases. La base por defecto del compose (administranet)
# solo debe sobrescribirse si indicás ALLOW_OVERWRITE_ADMINISTRANET=1.
#
# Uso:
#   ./scripts/restore-mysql-local.sh [ruta_al.zip] [nombre_base_mysql]
#
# Ejemplos:
#   ./scripts/restore-mysql-local.sh backups/backup.zip
#     → crea administranet_import_YYYYMMDD_HHMMSS
#   ./scripts/restore-mysql-local.sh backups/backup.zip administranet_jesels_20260409
#
# Variables de entorno:
#   MYSQL_DATABASE  — si está definida, se usa como nombre de base (salvo que pases el 2.º arg)
#   CONTAINER, MYSQL_USER, MYSQL_PASSWORD — igual que antes
#   ALLOW_OVERWRITE_ADMINISTRANET=1 — obligatorio si MYSQL_DATABASE=administranet

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ZIP_PATH="${1:-$PROJECT_DIR/backups/backup_administranet_Jesels_administranet_lunes_09_feb_2026__11_09.zip}"
CONTAINER="${CONTAINER:-Synap_mysql57}"
MYSQL_USER="${MYSQL_USER:-administranet}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-administranet_local}"

if [ -n "${2:-}" ]; then
  MYSQL_DATABASE="$2"
elif [ -z "${MYSQL_DATABASE:-}" ]; then
  MYSQL_DATABASE="administranet_import_$(date +%Y%m%d_%H%M%S)"
fi

if [ "$MYSQL_DATABASE" = "administranet" ] && [ "${ALLOW_OVERWRITE_ADMINISTRANET:-0}" != "1" ]; then
  echo "ERROR: No se importa por defecto sobre la base «administranet» (evita pisar tu DB local)."
  echo "Elegí un nombre nuevo, por ejemplo:"
  echo "  $0 \"$ZIP_PATH\" administranet_jesels_\$(date +%Y%m%d)"
  echo "O, si querés reemplazar explícitamente «administranet»:"
  echo "  ALLOW_OVERWRITE_ADMINISTRANET=1 MYSQL_DATABASE=administranet $0 \"$ZIP_PATH\""
  exit 1
fi

if [ ! -f "$ZIP_PATH" ]; then
  echo "No se encuentra el backup: $ZIP_PATH"
  echo "Coloca el .zip en backups/ o pasa la ruta como argumento."
  exit 1
fi

echo "Backup: $ZIP_PATH"
echo "Contenedor: $CONTAINER"
echo "Base (nueva o vacía): $MYSQL_DATABASE"

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

# Crear base vacía (sin DROP de nada)
docker exec "$CONTAINER" mysql -uroot -proot_local -e "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;" 2>/dev/null || true

echo "Importando ${#SQL_FILES[@]} archivo(s) SQL..."
for sql in "${SQL_FILES[@]}"; do
  echo "  -> $(basename "$sql")"
  docker exec -i "$CONTAINER" mysql -uroot -proot_local "$MYSQL_DATABASE" < "$sql"
done

echo "Restauración finalizada. Conexión local: host=127.0.0.1 port=3307 user=$MYSQL_USER database=$MYSQL_DATABASE"
echo "Actualizá .env / base_empresa si Synap debe usar este nombre de base."
