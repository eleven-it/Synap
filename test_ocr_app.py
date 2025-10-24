#!/usr/bin/env python3
"""
Script para probar el procesador OCR de la aplicación
"""

import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from support_ai.ocr_processor import ocr_processor

def test_ocr_processor():
    """Prueba el procesador OCR"""
    print("🧪 Probando procesador OCR de la aplicación...")
    
    try:
        # Probar con la imagen de prueba
        image_path = "/app/test_invoice.png"
        
        if not os.path.exists(image_path):
            print(f"❌ Imagen de prueba no encontrada: {image_path}")
            return False
        
        print(f"✅ Imagen encontrada: {image_path}")
        
        # Probar extracción de texto
        print("\n📝 Extrayendo texto...")
        ocr_result = ocr_processor.extract_text_from_image(image_path)
        
        print(f"✅ Texto extraído: {ocr_result['text'][:100]}...")
        print(f"✅ Confianza: {ocr_result['confidence']:.2f}")
        print(f"✅ Palabras: {ocr_result['word_count']}")
        
        # Probar extracción de datos estructurados
        print("\n🏗️ Extrayendo datos estructurados...")
        structured_data = ocr_processor.extract_structured_data(image_path)
        
        print(f"✅ Datos estructurados: {structured_data}")
        
        # Probar extracción de tablas
        print("\n📊 Extrayendo tablas...")
        tables = ocr_processor.extract_tables_from_image(image_path)
        
        print(f"✅ Tablas encontradas: {len(tables)}")
        
        # Verificar formatos soportados
        print("\n📋 Formatos soportados:")
        formats = ocr_processor.get_supported_formats()
        for fmt in formats:
            print(f"  ✅ {fmt}")
        
        print("\n🎉 ¡Procesador OCR funciona correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en procesador OCR: {e}")
        return False

if __name__ == "__main__":
    test_ocr_processor() 