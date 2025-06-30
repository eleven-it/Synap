#!/bin/bash

set -e

echo "🔧 Instalando dependencias necesarias..."
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev curl libncursesw5-dev \
xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev git

echo "📥 Instalando pyenv..."
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

if [ ! -d "$PYENV_ROOT" ]; then
  curl https://pyenv.run | bash
else
  echo "⚠️ pyenv ya está instalado en $PYENV_ROOT"
fi

# Agregar al perfil del shell si no existe
if ! grep -q 'pyenv init' ~/.bashrc; then
  echo -e '\n# PYENV CONFIG' >> ~/.bashrc
  echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
  echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
  echo 'eval "$(pyenv init -)"' >> ~/.bashrc
  echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
fi

# Recargar entorno actual para usar pyenv ahora
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

echo "🐍 Instalando Python 3.9.6 con pyenv..."
pyenv install -s 3.9.6

echo "📦 Creando entorno virtual llamado synap..."
pyenv virtualenv 3.9.6 synap

echo "✅ Activando entorno synap..."
pyenv activate synap

echo "🎉 Listo. Python en uso:"
python --version

echo "📝 Para que el entorno se active automáticamente en tu proyecto:"
echo "    pyenv local synap"
