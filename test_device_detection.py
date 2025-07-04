#!/usr/bin/env python3
"""
Script de prueba para verificar la detección de dispositivos
"""

import re

def test_device_detection():
    """
    Prueba la lógica de detección de dispositivos
    """
    
    # Patrones para detectar dispositivos móviles
    mobile_patterns = [
        r'Android',
        r'iPhone',
        r'iPad',
        r'iPod',
        r'BlackBerry',
        r'Windows Phone',
        r'Mobile',
        r'Opera Mini',
        r'IEMobile',
        r'webOS',
        r'Kindle',
        r'Silk',
        r'PlayBook',
        r'BB10',
        r'RIM Tablet OS'
    ]
    
    # User agents de prueba
    test_user_agents = [
        # Móviles
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.74 Mobile Safari/534.11+",
        "Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; Lumia 950) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Mobile Safari/537.36 Edge/15.14977",
        
        # Desktop
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
    ]
    
    print("🧪 Probando detección de dispositivos...")
    print("=" * 60)
    
    for i, user_agent in enumerate(test_user_agents, 1):
        # Verificar si es móvil
        is_mobile = any(re.search(pattern, user_agent, re.IGNORECASE) for pattern in mobile_patterns)
        
        # Detectar tipo específico de dispositivo
        device_type = 'desktop'
        if 'Android' in user_agent:
            device_type = 'android'
        elif 'iPhone' in user_agent:
            device_type = 'iphone'
        elif 'iPad' in user_agent:
            device_type = 'ipad'
        elif 'Windows Phone' in user_agent:
            device_type = 'windows_phone'
        elif is_mobile:
            device_type = 'mobile'
        
        # Mostrar resultado
        status = "📱 MÓVIL" if is_mobile else "💻 DESKTOP"
        print(f"{i:2d}. {status} | {device_type:12s} | {user_agent[:80]}...")
    
    print("=" * 60)
    print("✅ Prueba completada")

def test_template_selection():
    """
    Prueba la lógica de selección de templates
    """
    
    print("\n🎨 Probando selección de templates...")
    print("=" * 60)
    
    templates = [
        ('login/login', 'login/login_mobile'),
        ('login/register', 'login/register_mobile'),
        ('login/index', 'login/index_mobile'),
    ]
    
    for base_template, mobile_template in templates:
        print(f"Base: {base_template}")
        print(f"Mobile: {mobile_template}")
        print(f"Desktop: {base_template}.html")
        print(f"Mobile: {mobile_template}.html")
        print("-" * 40)

if __name__ == "__main__":
    test_device_detection()
    test_template_selection() 