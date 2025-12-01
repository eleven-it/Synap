#!/bin/bash

# Script para diagnosticar y solucionar problemas de persistencia de Redis

echo "🔍 Diagnóstico de Redis..."
echo ""

# 1. Verificar estado del contenedor Redis
echo "1️⃣ Verificando estado del contenedor Redis:"
docker ps -a | grep Synap_redis || echo "   ⚠️  Contenedor Redis no encontrado"
echo ""

# 2. Verificar logs de Redis
echo "2️⃣ Últimas líneas de logs de Redis:"
docker logs --tail 50 Synap_redis 2>&1 | tail -20
echo ""

# 3. Verificar espacio en disco
echo "3️⃣ Espacio en disco disponible:"
df -h | grep -E "Filesystem|/$|/var"
echo ""

# 4. Verificar si Redis puede escribir
echo "4️⃣ Probando escritura en Redis:"
docker exec Synap_redis redis-cli CONFIG GET dir
docker exec Synap_redis redis-cli CONFIG GET dbfilename
echo ""

# 5. Verificar permisos del directorio de datos
echo "5️⃣ Verificando directorio de datos de Redis:"
docker exec Synap_redis ls -la /data 2>/dev/null || echo "   ⚠️  Directorio /data no existe o no es accesible"
echo ""

# 6. Soluciones propuestas
echo "📋 SOLUCIONES PROPUESTAS:"
echo ""
echo "Opción 1: Deshabilitar stop-writes-on-bgsave-error (solución rápida)"
echo "   docker exec Synap_redis redis-cli CONFIG SET stop-writes-on-bgsave-error no"
echo ""
echo "Opción 2: Reiniciar Redis con volumen persistente (recomendado)"
echo "   - Actualizar docker-compose.yml para usar volumen redis_data"
echo "   - Reiniciar el servicio: docker-compose restart redis"
echo ""
echo "Opción 3: Deshabilitar persistencia RDB si solo se usa como cache"
echo "   docker exec Synap_redis redis-cli CONFIG SET save \"\""
echo ""

