#!/bin/bash

set -e

# Script de inicialización completa de Synap
# Ejecuta migraciones, setup inicial y carga de datos básicos
# Debe ejecutarse desde el host donde está corriendo el contenedor Synap_app

COLOR_OK='\033[1;32m'
COLOR_WARN='\033[1;33m'
COLOR_ERR='\033[1;31m'
COLOR_RESET='\033[0m'

function ok() { echo -e "${COLOR_OK}$1${COLOR_RESET}"; }
function warn() { echo -e "${COLOR_WARN}$1${COLOR_RESET}"; }
function err() { echo -e "${COLOR_ERR}$1${COLOR_RESET}"; }

ok "\n🚀 Iniciando inicialización completa de Synap...\n"

warn "1️⃣ Aplicando migraciones de base de datos..."
docker exec Synap_app python manage.py migrate
ok "✔️ Migraciones aplicadas.\n"

warn "2️⃣ Setup inicial del sistema (usuarios, empresa, permisos)..."
docker exec Synap_app python manage.py initial_setup --skip-migrations
ok "✔️ Setup inicial completado.\n"

warn "3️⃣ Cargando datos iniciales (países, monedas, unidades, impuestos, lista de precios, etc.)..."
docker exec Synap_app python manage.py load_initial_data
ok "✔️ Datos iniciales cargados (incluyendo lista de precios predeterminada).\n"

ok "🎉 Synap está listo para usarse. Puedes acceder con el usuario administrador creado.\n" 