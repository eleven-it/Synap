#!/bin/bash

echo "=================================================================================="
echo "🔧 CONFIGURANDO PARTNER TOKEN PARA TIENDANUBE"
echo "=================================================================================="
echo

# Verificar si el archivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Archivo .env no encontrado"
    echo "📝 Creando archivo .env desde env.example..."
    cp env.example .env
    echo "✅ Archivo .env creado"
    echo
fi

# Agregar Partner Token al .env
echo "🔑 Agregando TIENDANUBE_PARTNER_TOKEN al archivo .env..."
echo "" >> .env
echo "# TiendaNube Partners API" >> .env
echo "TIENDANUBE_PARTNER_TOKEN=your_partner_token_here" >> .env
echo "✅ Variable agregada al .env"
echo

echo "📋 CONFIGURACIÓN COMPLETADA:"
echo "----------------------------------------"
echo "• Variable: TIENDANUBE_PARTNER_TOKEN"
echo "• Ubicación: .env"
echo "• Valor: your_partner_token_here (REEMPLAZAR)"
echo

echo "🚀 PRÓXIMOS PASOS:"
echo "--------------------"
echo "1. 🔑 Obtener Partner Token de TiendaNube Partners"
echo "2. 📝 Reemplazar 'your_partner_token_here' con el token real"
echo "3. 🔄 Reiniciar el contenedor Docker"
echo "4. 🧪 Probar el wizard corregido"
echo

echo "💡 INSTRUCCIONES:"
echo "------------------"
echo "• Ve a: https://partners.tiendanube.com/"
echo "• Inicia sesión con tu cuenta de Partners"
echo "• Obtén el Partner Token"
echo "• Reemplaza el valor en .env"
echo "• Reinicia: docker compose restart app"
echo

echo "=================================================================================="


