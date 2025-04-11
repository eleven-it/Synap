#!/bin/bash

# Nombre: actualizar_repo_servidor.sh
# Descripción: Sube los cambios del repositorio FixSync a GitHub solo si hay modificaciones
# Repositorio: https://github.com/eleven-it/FixSync.git

# Mensaje de commit (por defecto)
mensaje_commit=${1:-"Actualización automática desde el servidor"}

# Archivo de log
log_dir="./logs"
log_file="$log_dir/actualizaciones.log"

# Fecha y hora actual
timestamp=$(date +"%Y-%m-%d %H:%M:%S")

echo "----------------------------------------"
echo "  ACTUALIZANDO REPOSITORIO FixSync"
echo "  Fecha: $timestamp"
echo "----------------------------------------"

# Verificar si estamos en un repositorio git
if [ ! -d ".git" ]; then
  echo "❌ Error: Este directorio no es un repositorio Git."
  exit 1
fi

# Verificar si hay cambios para commitear
if git diff --quiet && git diff --cached --quiet; then
  echo "✅ No hay cambios para subir. El repositorio está limpio."
  exit 0
fi

# Crear directorio de logs si no existe
mkdir -p "$log_dir"

# Agregar todos los archivos modificados
echo "➕ Agregando cambios..."
git add .

# Realizar el commit
echo "📝 Realizando commit con mensaje: \"$mensaje_commit\""
git commit -m "$mensaje_commit"

# Subir los cambios
echo "🚀 Subiendo al repositorio remoto..."
git push origin main

# Registrar en log
echo "$timestamp - Cambios subidos con mensaje: \"$mensaje_commit\"" >> "$log_file"

echo "✅ CAMBIOS SUBIDOS CORRECTAMENTE"
