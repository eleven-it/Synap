#!/usr/bin/env python3
"""
Script de prueba simple para Ollama usando requests
"""

import requests
import json
import time

def test_ollama_simple():
    """Prueba Ollama usando requests directamente"""
    
    # URL de Ollama
    base_url = "http://192.168.65.254:11434"
    
    # Probar conexión
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Conexión a Ollama exitosa")
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            print(f"   Modelos disponibles: {models}")
        else:
            print(f"❌ Error de conexión: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando a Ollama: {e}")
        return False
    
    # Probar generación
    try:
        payload = {
            "model": "llama3.1:8b",
            "prompt": "Hola, ¿cómo estás?",
            "options": {
                "temperature": 0.7,
                "max_tokens": 100
            }
        }
        
        start_time = time.time()
        response = requests.post(f"{base_url}/api/generate", json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            # Procesar respuesta streaming
            full_response = ""
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode('utf-8'))
                    full_response += data.get('response', '')
                    if data.get('done', False):
                        break
            
            print(f"✅ Generación exitosa")
            print(f"   Respuesta: {full_response}")
            print(f"   Tiempo: {end_time - start_time:.2f}s")
            return True
        else:
            print(f"❌ Error en generación: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error en generación: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_simple()
    print(f"\n🎯 Resultado: {'✅ Exitoso' if success else '❌ Falló'}")
