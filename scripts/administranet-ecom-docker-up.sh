#!/usr/bin/env bash
# Levanta el contenedor PHP administraNET-ecom (puerto 8050) con variables Synap.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.administranet-ecom.yml --env-file administranet-ecom.docker.env up -d --build "$@"
