#!/bin/bash

# Nombre: rollback_actualizacion_git.sh
# Descripción: Vuelve a la última rama de respaldo generada automáticamente

echo "----------------------------------------"
echo "  ROLLBACK DE ACTUALIZACIÓN GIT"
echo "----------------------------------------"

# Verificar si estamos en un repositorio git
if [ ! -d ".git" ]; then
  echo "❌ Error: Este directorio no es un repositorio Git."
  exit 1
fi

# Buscar la última rama de respaldo
ultima_respaldo=$(git branch --list "respaldo_*" | sort | tail -n 1 | sed 's/* //g')

if [ -z "$ultima_respaldo" ]; then
  echo "⚠️ No se encontró ninguna rama de respaldo (respaldo_*)"
  exit 1
fi

echo "🔙 Última rama de respaldo encontrada: $ultima_respaldo"
read -p "¿Querés volver a esa versión ahora? (s/n): " confirmar

if [[ "$confirmar" != "s" ]]; then
  echo "❌ Rollback cancelado."
  exit 0
fi

# Cambiar a la rama de respaldo
echo "⏪ Cambiando a la rama: $ultima_respaldo"
git checkout "$ultima_respaldo"

# Preguntar si desea reemplazar la rama 1.0 con la de respaldo
read -p "¿Querés reemplazar la rama '1.0' por este respaldo? (s/n): " reemplazar

if [[ "$reemplazar" == "s" ]]; then
  echo "♻️ Reemplazando la rama 1.0 con la rama $ultima_respaldo..."

  # Eliminar la rama 1.0 y crearla desde la actual
  git branch -D 1.0
  git checkout -b 1.0
  echo "✅ Rama 1.0 ahora apunta a $ultima_respaldo"
fi

echo "📍 Ahora estás en la rama: $(git branch --show-current)"
echo "🛠️ Recordá revisar y testear los cambios antes de hacer push de nuevo."
