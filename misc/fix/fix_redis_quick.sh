#!/bin/bash

# Solución rápida para el error de persistencia de Redis
# Este script deshabilita stop-writes-on-bgsave-error para permitir que Redis funcione
# incluso si no puede guardar snapshots RDB

echo "🔧 Aplicando solución rápida para Redis..."
echo ""

# Verificar que el contenedor existe
if ! docker ps -a | grep -q Synap_redis; then
    echo "❌ Error: Contenedor Synap_redis no encontrado"
    exit 1
fi

# Aplicar configuración
echo "1️⃣ Deshabilitando stop-writes-on-bgsave-error..."
docker exec Synap_redis redis-cli CONFIG SET stop-writes-on-bgsave-error no

if [ $? -eq 0 ]; then
    echo "   ✅ Configuración aplicada correctamente"
else
    echo "   ❌ Error al aplicar configuración"
    exit 1
fi

echo ""
echo "2️⃣ Verificando configuración..."
docker exec Synap_redis redis-cli CONFIG GET stop-writes-on-bgsave-error

echo ""
echo "✅ Solución aplicada. Redis debería funcionar ahora."
echo ""
echo "⚠️  NOTA: Esta es una solución temporal."
echo "   Para una solución permanente, actualiza docker-compose.yml y reinicia Redis."
echo "   El archivo docker-compose.yml ya ha sido actualizado con persistencia."

