#!/usr/bin/env bash
# Restaura el backup de administranet92 en el servidor remoto de pruebas.
#
# Uso (en el servidor remoto):
#   ./scripts/restore-administranet92.sh
#
# O con parámetros personalizados:
#   DB_HOST=localhost DB_PORT=3306 DB_USER=root DB_PASSWORD=secret ./scripts/restore-administranet92.sh
#
# El script busca el .zip en backups/ y lo restaura en la base administranet92.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

ZIP_FILE="${1:-$PROJECT_DIR/backups/administranet92_20260316.zip}"
TARGET_DB="administranet92"

# Conexión MySQL — se pueden sobrescribir con variables de entorno o .env
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env" 2>/dev/null || true
  set +a
fi

MYSQL_HOST="${DB_HOST:-127.0.0.1}"
MYSQL_PORT="${DB_PORT:-3306}"
MYSQL_USER="${DB_USER:-administranet}"
MYSQL_PASSWORD="${DB_PASSWORD:-a7v8xx0805}"
CONTAINER="${MYSQL_CONTAINER:-}"

if [ ! -f "$ZIP_FILE" ]; then
  echo "ERROR: No se encuentra el backup: $ZIP_FILE"
  echo "Asegurate de que el archivo existe en backups/"
  exit 1
fi

echo "============================================"
echo "  Restauración de $TARGET_DB"
echo "============================================"
echo "Backup:     $ZIP_FILE"
echo "Host:       $MYSQL_HOST:$MYSQL_PORT"
echo "Usuario:    $MYSQL_USER"
echo "Base:       $TARGET_DB"
echo ""

RESTORE_DIR=$(mktemp -d)
trap "rm -rf $RESTORE_DIR" EXIT

echo "[1/4] Descomprimiendo backup..."
unzip -o -q "$ZIP_FILE" -d "$RESTORE_DIR"

SQL_FILES=()
while IFS= read -r -d '' f; do
  SQL_FILES+=("$f")
done < <(find "$RESTORE_DIR" -type f \( -name "*.sql" -o -name "*.SQL" \) -print0 | sort -z)

if [ ${#SQL_FILES[@]} -eq 0 ]; then
  echo "ERROR: No se encontró ningún .sql dentro del zip."
  exit 1
fi

echo "   Encontrados ${#SQL_FILES[@]} archivo(s) SQL"

run_mysql() {
  if [ -n "$CONTAINER" ] && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
    docker exec -i "$CONTAINER" mysql "$@"
  else
    mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$@"
  fi
}

echo "[2/4] Creando base $TARGET_DB si no existe..."
run_mysql -e "CREATE DATABASE IF NOT EXISTS \`$TARGET_DB\` CHARACTER SET latin1 COLLATE latin1_swedish_ci;" 2>/dev/null || true

echo "[3/4] Importando SQL..."
for sql in "${SQL_FILES[@]}"; do
  echo "   -> $(basename "$sql") ($(du -h "$sql" | cut -f1))"
  run_mysql "$TARGET_DB" < "$sql"
done

echo "[4/4] Verificando..."
TABLE_COUNT=$(run_mysql "$TARGET_DB" -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$TARGET_DB';" 2>/dev/null)
echo "   Tablas en $TARGET_DB: $TABLE_COUNT"

echo ""
echo "============================================"
echo "  Restauración completada"
echo "============================================"
echo "Conexión: mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p*** $TARGET_DB"
