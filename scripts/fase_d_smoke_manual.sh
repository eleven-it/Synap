#!/usr/bin/env bash
set -euo pipefail

# Smoke manual Fase D (mayoristapp) con sesión real y CSRF real.
# Uso:
#   BASE_URL="http://127.0.0.1:8000" \
#   SESSION_ID="..." \
#   CSRF_TOKEN="..." \
#   ./scripts/fase_d_smoke_manual.sh
#
# Opcional:
#   AJAX_POST_PATH="/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1"
#   AJAX_POST_BODY='{"vendedor":"true","campoBusca":"-"}'

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SESSION_ID="${SESSION_ID:-}"
CSRF_TOKEN="${CSRF_TOKEN:-}"
AJAX_POST_PATH="${AJAX_POST_PATH:-/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1}"
AJAX_POST_BODY="${AJAX_POST_BODY:-{\"vendedor\":\"true\",\"campoBusca\":\"-\"}}"

if [[ -z "${SESSION_ID}" || -z "${CSRF_TOKEN}" ]]; then
  echo "ERROR: Debes definir SESSION_ID y CSRF_TOKEN."
  echo "Ejemplo:"
  echo "  BASE_URL=\"http://127.0.0.1:8000\" SESSION_ID=\"...\" CSRF_TOKEN=\"...\" ./scripts/fase_d_smoke_manual.sh"
  exit 1
fi

echo "== Smoke Fase D =="
echo "BASE_URL=${BASE_URL}"

echo ""
echo "1) Endpoints públicos"
HEALTH_CODE="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/ecom/api/health/")"
MIGRATION_JSON="$(curl -s "${BASE_URL}/ecom/api/migration-info/")"
RELAY_JSON="$(curl -s "${BASE_URL}/ecom/api/mayoristapp/relay-inventory/")"

echo "   health status: ${HEALTH_CODE}"
echo "   migration-info (preview): $(echo "${MIGRATION_JSON}" | tr -d '\n' | cut -c1-180)"
echo "   relay-inventory (preview): $(echo "${RELAY_JSON}" | tr -d '\n' | cut -c1-180)"

echo ""
echo "2) POST con sesión + CSRF (debe responder != 403)"
POST_CODE="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${BASE_URL}${AJAX_POST_PATH}" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: ${CSRF_TOKEN}" \
  -b "sessionid=${SESSION_ID}; csrftoken=${CSRF_TOKEN}" \
  -d "${AJAX_POST_BODY}")"

echo "   POST status: ${POST_CODE}"

if [[ "${POST_CODE}" == "403" ]]; then
  echo "ERROR: CSRF/sesión inválido (403)."
  exit 2
fi

echo ""
echo "OK: smoke manual ejecutado."
