#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f docker-compose.administranet-ecom.yml --env-file administranet-ecom.docker.env down "$@"
