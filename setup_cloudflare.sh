#!/bin/bash

echo "🚀 Configuración de Cloudflare CDN para Synap"
echo "=============================================="
echo ""

# Verificar que Docker esté corriendo
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    exit 1
fi

echo "✅ Docker está corriendo"
echo ""

# Paso 1: Verificar configuración actual
echo "📋 Paso 1: Verificando configuración actual..."
docker exec Synap_app python manage.py test_cdn
echo ""

# Paso 2: Instrucciones para configurar Cloudflare
echo "📋 Paso 2: Configuración en Cloudflare"
echo "======================================"
echo ""
echo "1. 🌐 Crear cuenta en Cloudflare:"
echo "   - Ve a https://cloudflare.com"
echo "   - Crea una cuenta gratuita"
echo ""
echo "2. 🔗 Agregar tu dominio:"
echo "   - En el dashboard de Cloudflare, haz clic en 'Add a Site'"
echo "   - Ingresa tu dominio (ej: synap.com)"
echo "   - Selecciona el plan 'Free'"
echo ""
echo "3. ⚙️  Configurar DNS:"
echo "   - Cloudflare te mostrará los nameservers"
echo "   - Actualiza los nameservers en tu proveedor de dominio"
echo "   - Ejemplo de nameservers:"
echo "     * nina.ns.cloudflare.com"
echo "     * rick.ns.cloudflare.com"
echo ""
echo "4. 🎯 Configurar subdominio CDN:"
echo "   - En DNS > Records, agrega un registro CNAME:"
echo "     * Nombre: cdn"
echo "     * Contenido: tu-dominio.com"
echo "     * Proxy status: Proxied (nube naranja)"
echo ""
echo "5. ⚡ Activar optimizaciones:"
echo "   - Ve a Speed > Optimization"
echo "   - Activa 'Auto Minify' para JS, CSS, HTML"
echo "   - Activa 'Brotli' compression"
echo "   - Activa 'Rocket Loader'"
echo ""
echo "6. 🖼️  Configurar Image Optimization:"
echo "   - Ve a Speed > Optimization > Image"
echo "   - Activa 'Polish' (Lossy o Lossless)"
echo "   - Activa 'WebP' format"
echo "   - Activa 'Lazy Loading'"
echo ""
echo "7. 📊 Configurar Page Rules (opcional):"
echo "   - Ve a Rules > Page Rules"
echo "   - Crea una regla para imágenes:"
echo "     * URL: cdn.tudominio.com/media/products/*"
echo "     * Settings: Cache Level > Cache Everything"
echo "     * Settings: Edge Cache TTL > 1 week"
echo ""

# Paso 3: Verificar configuración del sistema
echo "📋 Paso 3: Verificando configuración del sistema..."
echo ""

# Verificar configuración de SystemConfiguration
echo "🔍 Verificando configuración en base de datos..."
docker exec Synap_app python manage.py shell -c "
from core.models import SystemConfiguration
configs = SystemConfiguration.objects.filter(key__startswith='cdn.')
for config in configs:
    print(f'  {config.key}: {config.value} ({config.is_active})')
"
echo ""

# Paso 4: Instrucciones para producción
echo "📋 Paso 4: Configuración para producción"
echo "========================================"
echo ""
echo "1. 🌍 Actualizar dominio real:"
echo "   - Cambia 'cdn.synap.com' por tu dominio real"
echo "   - Ejemplo: cdn.tudominio.com"
echo ""
echo "2. 🔒 Configurar SSL:"
echo "   - Cloudflare proporciona SSL automático"
echo "   - Ve a SSL/TLS > Overview"
echo "   - Selecciona 'Full (strict)' para máxima seguridad"
echo ""
echo "3. 📈 Monitoreo:"
echo "   - Ve a Analytics > Traffic"
echo "   - Monitorea el tráfico del CDN"
echo "   - Revisa las métricas de rendimiento"
echo ""
echo "4. 🛡️  Seguridad adicional:"
echo "   - Ve a Security > Settings"
echo "   - Activa 'Always Use HTTPS'"
echo "   - Configura 'Security Level' según necesites"
echo ""

# Paso 5: Comandos útiles
echo "📋 Paso 5: Comandos útiles"
echo "=========================="
echo ""
echo "🔍 Probar configuración CDN:"
echo "   docker exec Synap_app python manage.py test_cdn"
echo ""
echo "📊 Probar rendimiento:"
echo "   docker exec Synap_app python manage.py test_cdn --test-performance"
echo ""
echo "🔧 Ver configuración detallada:"
echo "   docker exec Synap_app python manage.py test_cdn --verbose"
echo ""
echo "🔄 Limpiar cache de configuración:"
echo "   docker exec Synap_app python manage.py shell -c \"from core.models import SystemConfiguration; SystemConfiguration.clear_cache()\""
echo ""

# Paso 6: Verificación final
echo "📋 Paso 6: Verificación final"
echo "============================="
echo ""
echo "✅ Configuración actual:"
docker exec Synap_app python manage.py test_cdn
echo ""
echo "🎉 ¡Cloudflare CDN está configurado!"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Configura tu dominio en Cloudflare"
echo "   2. Actualiza el dominio en la configuración"
echo "   3. Prueba la carga de imágenes"
echo "   4. Monitorea el rendimiento"
echo ""
echo "📞 Soporte:"
echo "   - Documentación Cloudflare: https://developers.cloudflare.com/"
echo "   - Soporte técnico: https://support.cloudflare.com/"
echo "" 