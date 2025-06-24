#!/bin/bash

# Nombre: actualizar_repo_synap.sh
# Descripción: Actualiza Synap en la rama 1.0 con autenticación SSH, merge, backup y resolución asistida de conflictos.
# Autor: Sebastián Paredes

mensaje_commit=${1:-"Actualización automática desde el servidor"}
log_dir="./logs"
log_file="$log_dir/actualizaciones.log"
timestamp=$(date +"%Y-%m-%d %H:%M:%S")
fecha_slug=$(date +"%Y%m%d_%H%M")
rama_principal="1.0"
remoto_esperado="git@github.com:eleven-it/Synap.git"

echo ""
echo "========================================"
echo "  🚀 ACTUALIZANDO REPOSITORIO Synap"
echo "  📅 Fecha: $timestamp"
echo "========================================"
echo ""

# Verificar si estamos en un repositorio git
if [ ! -d ".git" ]; then
  echo "❌ Error: Este directorio no es un repositorio Git."
  echo ""
  exit 1
fi

# Verificar y corregir URL remota si es necesario
remote_url=$(git remote get-url origin 2>/dev/null)

if [[ "$remote_url" != "$remoto_esperado" ]]; then
  echo "🔄 Actualizando el remoto 'origin' a: $remoto_esperado"
  git remote remove origin 2>/dev/null
  git remote add origin "$remoto_esperado"
  echo "✅ URL del remoto configurada correctamente."
  echo ""
fi

# Cambiar a la rama principal
echo "📌 Cambiando a la rama principal: $rama_principal..."
git checkout "$rama_principal" || {
  echo "❌ Error: No se pudo cambiar a la rama '$rama_principal'."
  exit 1
}
echo ""

# Crear rama de respaldo
backup_branch="respaldo_$fecha_slug"
echo "🛡️  Creando rama de respaldo: $backup_branch"
git checkout -b "$backup_branch"
git checkout "$rama_principal"
echo ""

# Detectar archivos modificados sin agregar (unstaged)
if ! git diff --quiet; then
  echo "⚠️  Archivos modificados sin agregar (unstaged):"
  git status --short
  echo "➕ Agregando automáticamente todos los cambios con: git add ."
  git add .
  echo ""
fi

# Hacer pull con merge
echo "🔄 Haciendo pull de origin/$rama_principal (con merge)..."
if ! git pull origin "$rama_principal"; then
  echo ""
  echo "❌ Conflicto detectado durante el merge."
  echo "📂 Archivos en conflicto:"
  conflict_files=$(git diff --name-only --diff-filter=U)
  echo "$conflict_files"
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
        echo "✏️ Editá el archivo y ejecutá: git add $file"
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

echo "🚀 Subiendo cambios a la rama '$rama_principal'..."
if git push origin "$rama_principal"; then
  echo ""
  echo "$timestamp - Cambios subidos a rama '$rama_principal' con mensaje: \"$mensaje_commit\"" >> "$log_file"
  echo "✅ CAMBIOS SUBIDOS CORRECTAMENTE"
else
  echo ""
  echo "❌ Error: El push al repositorio remoto falló."
  echo "🧾 Verificá si estás autenticado correctamente con GitHub."
  echo ""
  exit 1
fi

echo ""
