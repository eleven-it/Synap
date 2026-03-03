#!/usr/bin/env bash
# Asocia la empresa "jesels Test" con la base administranet local.
# Requiere: base `empresas` existente (ej. ./scripts/pull-empresas-from-remote.sh)
# Uso: ./scripts/associate-empresa-local.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOCAL_HOST="${LOCAL_DB_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_DB_PORT:-3307}"
LOCAL_USER="${LOCAL_DB_USER:-administranet}"
LOCAL_PASSWORD="${LOCAL_DB_PASSWORD:-administranet_local}"
CONTAINER="${MYSQL_CONTAINER:-Synap_mysql57}"
BASE_EMPRESA="${BASE_EMPRESA:-administranet}"
NOMBRE_EMPRESA="${NOMBRE_EMPRESA:-jesels Test}"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env" 2>/dev/null || true
  set +a
  LOCAL_PORT="${DB_PORT:-$LOCAL_PORT}"
  LOCAL_USER="${DB_USER:-$LOCAL_USER}"
  LOCAL_PASSWORD="${DB_PASSWORD:-$LOCAL_PASSWORD}"
  BASE_EMPRESA="${DB_NAME:-$BASE_EMPRESA}"
fi

SQL="
USE empresas;

-- Actualizar 'jesel Test' (remoto) o 'jesels Test' si existe
UPDATE empresas
SET nombre_empresa = '$NOMBRE_EMPRESA', dsn_empresa = '$BASE_EMPRESA', base_empresa = '$BASE_EMPRESA'
WHERE nombre_empresa IN ('jesel Test', 'jesels Test');

-- Si no existía ninguna fila con esa base, insertar nueva
INSERT INTO empresas (nombre_empresa, dsn_empresa, base_empresa, web_base_defecto, version, web_disponible)
SELECT '$NOMBRE_EMPRESA', '$BASE_EMPRESA', '$BASE_EMPRESA', 'No', '1.0.18', 'Si'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM empresas WHERE base_empresa = '$BASE_EMPRESA' LIMIT 1);
"

echo "📌 Asociando '$NOMBRE_EMPRESA' con base '$BASE_EMPRESA' en empresas..."
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER}$"; then
  echo "   Usando contenedor: $CONTAINER"
  docker exec "$CONTAINER" mysql -u"$LOCAL_USER" -p"$LOCAL_PASSWORD" -e "$SQL"
else
  mysql -h"$LOCAL_HOST" -P"$LOCAL_PORT" -u"$LOCAL_USER" -p"$LOCAL_PASSWORD" -e "$SQL"
fi

echo "✅ Listo. La empresa '$NOMBRE_EMPRESA' apunta a la base '$BASE_EMPRESA' (administranet_local)."
