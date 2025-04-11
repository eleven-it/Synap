#!/bin/bash

# Nombre: actualizar_repo_servidor.sh
# Descripción: Actualiza y sincroniza cambios de FixSync en la rama 1.0 usando merge, con resolución asistida de conflictos.
# Repositorio: https://github.com/eleven-it/FixSync.git

mensaje_commit=${1:-"Actualización automática desde el servidor"}
log_dir="./logs"
log_file="$log_dir/actualizaciones.log"
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
fecha_slug=$(date +"%Y%m%d_%H%M")

echo ""
echo "========================================"
echo "  🚀 ACTUALIZANDO REPOSITORIO FixSync"
echo "  📅 Fecha: $timestamp"
echo "========================================"
echo ""

# Verificar si estamos en un repositorio git
if [ ! -d ".git" ]; then
  echo "❌ Error: Este directorio no es un repositorio Git."
  echo ""
  exit 1
fi

echo "📌 Cambiando a la rama 1.0..."
git checkout 1.0
echo ""

backup_branch="respaldo_$fecha_slug"
echo "🛡️  Creando rama de respaldo: $backup_branch"
git checkout -b "$backup_branch"
git checkout 1.0
echo ""

# Verificar si hay archivos modificados sin agregar
if ! git diff --quiet; then
  echo "⚠️  Se detectaron archivos modificados sin agregar (unstaged)."
  echo ""
  echo "🔍 Archivos modificados:"
  echo "-----------------------------"
  git status --short
  echo "-----------------------------"
  echo ""
  echo "➕ Agregando automáticamente todos los cambios con: git add ."
  git add .
  echo ""
fi

# Hacer pull con merge
echo "🔄 Haciendo pull (con merge)..."
if ! git pull; then
  echo ""
  echo "❌ Conflicto detectado durante el merge."
  echo ""
  echo "📂 Archivos en conflicto:"
  echo "-----------------------------"
  conflict_files=$(git diff --name-only --diff-filter=U)
  echo "$conflict_files"
  echo "-----------------------------"
  echo ""

  for file in $conflict_files; do
    echo "🧩 Conflicto en: $file"
    echo "[1] Usar mi versión (ours)"
    echo "[2] Usar la versión del servidor (theirs)"
    echo "[3] Editar manualmente"
    read -p "Elegí una opción (1/2/3): " opcion

    case $opcion in
      1)
        git checkout --ours "$file"
        git add "$file"
        echo "✔ Usada tu versión local."
        ;;
      2)
        git checkout --theirs "$file"
        git add "$file"
        echo "✔ Usada la versión remota."
        ;;
      3)
        echo "✏️ Abrí el archivo en tu editor, resolvé el conflicto y luego ejecutá:"
        echo "   git add $file"
        echo ""
        read -p "Presioná Enter cuando lo hayas resuelto..."
        ;;
      *)
        echo "⚠️ Opción inválida. Saltando $file."
        ;;
    esac

    echo ""
  done

  echo "✅ Todos los conflictos fueron tratados."

  read -p "¿Querés confirmar el commit de merge ahora? (s/n): " confirmar_merge
  if [[ "$confirmar_merge" == "s" ]]; then
    git commit
    echo "✔ Merge confirmado."
  else
    echo "⚠️ No se confirmó el commit. Podés hacerlo luego con 'git commit'."
    exit 1
  fi
fi
echo ""

# Verificar si hay cambios para commitear
if git diff --quiet && git diff --cached --quiet; then
  echo "✅ No hay cambios nuevos para subir. El repositorio está limpio."
  echo ""
  exit 0
fi

mkdir -p "$log_dir"

echo "➕ Agregando archivos..."
git add .
echo ""

echo "📝 Realizando commit con mensaje: \"$mensaje_commit\""
git commit -m "$mensaje_commit"
echo ""

echo "🚀 Subiendo cambios al repositorio remoto..."
git push origin 1.0
echo ""

echo "$timestamp - Cambios subidos a rama 1.0 con mensaje: \"$mensaje_commit\"" >> "$log_file"

echo "✅ CAMBIOS SUBIDOS CORRECTAMENTE"
echo ""
