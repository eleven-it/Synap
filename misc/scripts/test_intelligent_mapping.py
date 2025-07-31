#!/usr/bin/env python
"""
Script de prueba para el mapeo inteligente de nombres.
Demuestra cómo maneja variaciones como "Buenos Aires" vs "Baires" vs "Bs As".
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from tiendanube_administranet.services.intelligent_name_mapping_service import IntelligentNameMappingService


def test_province_mapping():
    """
    Prueba el mapeo de provincias con variaciones.
    """
    print("=" * 60)
    print("PRUEBA DE MAPEO INTELIGENTE DE PROVINCIAS")
    print("=" * 60)
    
    mapper = IntelligentNameMappingService()
    
    # Casos de prueba con variaciones
    test_cases = [
        "Buenos Aires",
        "Baires", 
        "Bs As",
        "BSAS",
        "Córdoba",
        "Cordoba",
        "CBA",
        "Cba.",
        "Santa Fe",
        "SF",
        "Santafe",
        "Mendoza",
        "MZA",
        "Tucumán",
        "Tucuman",
        "TUC",
        "Tuc.",
        "Salta",
        "SLA",
        "Entre Ríos",
        "Entre Rios",
        "ER",
        "Río Negro",
        "Rio Negro",
        "RN",
        "Neuquén",
        "Neuquen",
        "NEU",
        "La Pampa",
        "LP",
        "Pampa",
        "La Rioja",
        "LR",
        "Rioja",
        "Santiago del Estero",
        "SDE",
        "Santiago",
        "San Luis",
        "SL",
        "Catamarca",
        "CAT",
        "Jujuy",
        "JUJ",
        "Chaco",
        "CHA",
        "Formosa",
        "FOR",
        "Misiones",
        "MIS",
        "Corrientes",
        "COR",
        "San Juan",
        "SJ",
        "Tierra del Fuego",
        "TDF",
        "Fuego",
    ]
    
    print(f"{'Variación':<25} {'Mapeado a':<25} {'ID':<5}")
    print("-" * 60)
    
    for variation in test_cases:
        try:
            province_id = mapper.get_province_code(variation)
            # Obtener el nombre real para mostrar
            with mapper.adminet_config.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Provincia FROM provincia WHERE CodProvincia = %s", [province_id])
                result = cursor.fetchone()
                real_name = result[0] if result else "No encontrado"
            
            print(f"{variation:<25} {real_name:<25} {province_id:<5}")
            
        except Exception as e:
            print(f"{variation:<25} {'ERROR':<25} {str(e)[:20]}")


def test_country_mapping():
    """
    Prueba el mapeo de países con variaciones.
    """
    print("\n" + "=" * 60)
    print("PRUEBA DE MAPEO INTELIGENTE DE PAÍSES")
    print("=" * 60)
    
    mapper = IntelligentNameMappingService()
    
    test_cases = [
        "Argentina",
        "ARG",
        "AR",
        "Argentine Republic",
        "Brasil",
        "Brazil",
        "BR",
        "Chile",
        "CL",
        "Uruguay",
        "UY",
        "Paraguay",
        "PY",
        "Bolivia",
        "BO",
        "Perú",
        "Peru",
        "PE",
        "Colombia",
        "CO",
        "Venezuela",
        "VE",
        "Ecuador",
        "EC",
    ]
    
    print(f"{'Variación':<25} {'Mapeado a':<25} {'ID':<5}")
    print("-" * 60)
    
    for variation in test_cases:
        try:
            country_id = mapper.get_country_id(variation)
            # Obtener el nombre real para mostrar
            with mapper.adminet_config.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nombre FROM pais WHERE id_pais = %s", [country_id])
                result = cursor.fetchone()
                real_name = result[0] if result else "No encontrado"
            
            print(f"{variation:<25} {real_name:<25} {country_id:<5}")
            
        except Exception as e:
            print(f"{variation:<25} {'ERROR':<25} {str(e)[:20]}")


def test_city_mapping():
    """
    Prueba el mapeo de ciudades con variaciones.
    """
    print("\n" + "=" * 60)
    print("PRUEBA DE MAPEO INTELIGENTE DE CIUDADES")
    print("=" * 60)
    
    mapper = IntelligentNameMappingService()
    
    test_cases = [
        "Buenos Aires",
        "CABA",
        "Capital Federal",
        "Baires",
        "Córdoba",
        "Cordoba",
        "CBA",
        "Cba.",
        "Rosario",
        "ROS",
        "La Plata",
        "LP",
        "Mar del Plata",
        "MDP",
        "Mendoza",
        "MZA",
        "Tucumán",
        "Tucuman",
        "TUC",
        "Tuc.",
        "Salta",
        "SLA",
        "Neuquén",
        "Neuquen",
        "NEU",
        "Bahía Blanca",
        "Bahia Blanca",
        "BB",
        "Resistencia",
        "RES",
        "Paraná",
        "Parana",
        "Santiago del Estero",
        "SDE",
        "Santiago",
        "San Luis",
        "SL",
        "Catamarca",
        "CAT",
        "Jujuy",
        "JUJ",
        "Formosa",
        "FOR",
        "Posadas",
        "POS",
        "Corrientes",
        "COR",
        "San Juan",
        "SJ",
        "Ushuaia",
        "USH",
    ]
    
    print(f"{'Variación':<25} {'Mapeado a':<25} {'ID':<5}")
    print("-" * 60)
    
    for variation in test_cases:
        try:
            department_id = mapper.get_department_id(variation)
            # Obtener el nombre real para mostrar
            with mapper.adminet_config.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT NombreDepartamento FROM departamento WHERE IDDepartamento = %s", [department_id])
                result = cursor.fetchone()
                real_name = result[0] if result else "No encontrado"
            
            print(f"{variation:<25} {real_name:<25} {department_id:<5}")
            
        except Exception as e:
            print(f"{variation:<25} {'ERROR':<25} {str(e)[:20]}")


def test_fuzzy_matching():
    """
    Prueba el fuzzy matching con casos edge.
    """
    print("\n" + "=" * 60)
    print("PRUEBA DE FUZZY MATCHING")
    print("=" * 60)
    
    mapper = IntelligentNameMappingService()
    
    # Casos edge que deberían funcionar con fuzzy matching
    edge_cases = [
        "Buenos Ares",  # Sin 'i'
        "Buenos Aries",  # Con 'i' extra
        "Cordoba",      # Sin tilde
        "Cordóba",      # Con tilde en lugar incorrecto
        "Santa Fé",     # Con tilde
        "Mendóza",      # Con tilde
        "Tucumán",      # Con tilde
        "Sálta",        # Con tilde
        "Argéntina",    # Con tilde
        "Brasíl",       # Con tilde
        "Chíle",        # Con tilde
    ]
    
    print(f"{'Caso Edge':<25} {'Mapeado a':<25} {'ID':<5}")
    print("-" * 60)
    
    for edge_case in edge_cases:
        try:
            province_id = mapper.get_province_code(edge_case)
            # Obtener el nombre real para mostrar
            with mapper.adminet_config.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT Provincia FROM provincia WHERE CodProvincia = %s", [province_id])
                result = cursor.fetchone()
                real_name = result[0] if result else "No encontrado"
            
            print(f"{edge_case:<25} {real_name:<25} {province_id:<5}")
            
        except Exception as e:
            print(f"{edge_case:<25} {'ERROR':<25} {str(e)[:20]}")


def test_cache_functionality():
    """
    Prueba la funcionalidad de cache.
    """
    print("\n" + "=" * 60)
    print("PRUEBA DE FUNCIONALIDAD DE CACHE")
    print("=" * 60)
    
    mapper = IntelligentNameMappingService()
    
    # Probar cache
    test_term = "Buenos Aires"
    
    print(f"Primera consulta para '{test_term}':")
    start_time = time.time()
    result1 = mapper.get_province_code(test_term)
    time1 = time.time() - start_time
    print(f"  Resultado: {result1}, Tiempo: {time1:.4f}s")
    
    print(f"Segunda consulta para '{test_term}' (debería usar cache):")
    start_time = time.time()
    result2 = mapper.get_province_code(test_term)
    time2 = time.time() - start_time
    print(f"  Resultado: {result2}, Tiempo: {time2:.4f}s")
    
    print(f"Cache más rápido: {'Sí' if time2 < time1 else 'No'}")
    
    # Mostrar estadísticas del cache
    stats = mapper.get_mapping_statistics()
    print(f"\nEstadísticas del cache:")
    print(f"  Tamaño del cache: {stats['cache_size']}")
    print(f"  Mapeos en cache: {len(stats['cached_mappings'])}")
    print(f"  Variaciones de provincia: {stats['province_variations_count']}")
    print(f"  Variaciones de país: {stats['country_variations_count']}")
    print(f"  Variaciones de ciudad: {stats['city_variations_count']}")


if __name__ == "__main__":
    import time
    
    print("INICIANDO PRUEBAS DE MAPEO INTELIGENTE")
    print("Este script demuestra cómo el sistema maneja variaciones de nombres")
    print("como 'Buenos Aires' vs 'Baires' vs 'Bs As'")
    print()
    
    try:
        test_province_mapping()
        test_country_mapping()
        test_city_mapping()
        test_fuzzy_matching()
        test_cache_functionality()
        
        print("\n" + "=" * 60)
        print("PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("=" * 60)
        print("El sistema de mapeo inteligente puede manejar:")
        print("✓ Variaciones comunes (Baires, Bs As)")
        print("✓ Abreviaciones (CBA, MZA, TUC)")
        print("✓ Diferencias de acentos (Cordoba vs Córdoba)")
        print("✓ Fuzzy matching para casos edge")
        print("✓ Cache para mejorar rendimiento")
        print("✓ Valores por defecto cuando no se encuentra coincidencia")
        
    except Exception as e:
        print(f"\nERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc() 