// Script de debug para el botón de toggle
console.log('🔍 DEBUG: Iniciando análisis del botón de toggle...');

// 1. Verificar si el botón existe
const button = document.querySelector('button[onclick*="toggleWebhook(1"]');
console.log('📋 Botón encontrado:', button);

if (button) {
    console.log('✅ Botón encontrado correctamente');
    console.log('📋 HTML del botón:', button.outerHTML);
    console.log('📋 onclick del botón:', button.getAttribute('onclick'));
    
    // 2. Verificar si la función toggleWebhook existe
    if (typeof toggleWebhook === 'function') {
        console.log('✅ Función toggleWebhook existe');
    } else {
        console.log('❌ Función toggleWebhook NO existe');
    }
    
    // 3. Verificar CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        console.log('✅ CSRF token encontrado:', csrfToken.value.substring(0, 20) + '...');
    } else {
        console.log('❌ CSRF token NO encontrado');
    }
    
    // 4. Simular clic en el botón
    console.log('🎯 Simulando clic en el botón...');
    button.click();
    
} else {
    console.log('❌ Botón NO encontrado');
    console.log('📋 Todos los botones en la página:');
    const allButtons = document.querySelectorAll('button');
    allButtons.forEach((btn, index) => {
        console.log(`  ${index + 1}. ${btn.outerHTML}`);
    });
}

// 5. Verificar si hay errores de JavaScript
window.addEventListener('error', function(e) {
    console.error('❌ Error de JavaScript:', e.error);
});

console.log('🔍 DEBUG: Análisis completado. Revisa los logs arriba.');
