#!/usr/bin/env bash
# Prepara el directorio de WAL archivados (volumen compartido con Synap_app)
# y delega al entrypoint oficial de la imagen postgres.
set -euo pipefail

WAL_DIR="${SYNAP_PG_WAL_ARCHIVE_DIR:-/var/lib/postgresql/wal_archive}"
mkdir -p "$WAL_DIR"
# En volúmenes nuevos el owner suele ser root; postgres necesita escribir el archive.
if [ "$(id -u)" = "0" ]; then
  chown -R postgres:postgres "$WAL_DIR" || true
  chmod 700 "$WAL_DIR" || true
fi

exec docker-entrypoint.sh "$@"
