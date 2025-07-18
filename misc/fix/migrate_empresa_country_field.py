#!/usr/bin/env python
"""
Script para migrar el campo pais (CharField) al nuevo campo country (ForeignKey) en el modelo Empresa.
Este script debe ejecutarse después de aplicar la migración que agrega el campo country.
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import Empresa, Country, State
from django.db import transaction


def migrate_empresa_country_field():
    """
    Migra los datos del campo pais (legacy) al nuevo campo country (ForeignKey)
    """
    print("🔄 Iniciando migración de campo país en empresas...")
    
    # Obtener todas las empresas que tienen campo pais pero no country
    empresas_sin_country = Empresa.objects.filter(
        pais__isnull=False,
        pais__gt='',
        country__isnull=True
    )
    
    print(f"📊 Encontradas {empresas_sin_country.count()} empresas para migrar")
    
    if empresas_sin_country.count() == 0:
        print("✅ No hay empresas que requieran migración")
        return
    
    # Mapeo de nombres de países comunes
    country_mapping = {
        'argentina': 'Argentina',
        'brasil': 'Brazil', 
        'chile': 'Chile',
        'uruguay': 'Uruguay',
        'paraguay': 'Paraguay',
        'mexico': 'Mexico',
        'colombia': 'Colombia',
        'peru': 'Peru',
        'ecuador': 'Ecuador',
        'venezuela': 'Venezuela',
        'bolivia': 'Bolivia',
        'estados unidos': 'United States',
        'usa': 'United States',
        'united states': 'United States',
        'españa': 'Spain',
        'spain': 'Spain',
        'francia': 'France',
        'france': 'France',
        'alemania': 'Germany',
        'germany': 'Germany',
        'italia': 'Italy',
        'italy': 'Italy',
        'reino unido': 'United Kingdom',
        'united kingdom': 'United Kingdom',
        'uk': 'United Kingdom',
        'canada': 'Canada',
        'australia': 'Australia',
        'nueva zelanda': 'New Zealand',
        'new zealand': 'New Zealand',
    }
    
    updated_count = 0
    not_found_count = 0
    not_found_countries = set()
    
    with transaction.atomic():
        for empresa in empresas_sin_country:
            pais_nombre = empresa.pais.strip().lower()
            
            # Buscar país por mapeo
            normalized_name = country_mapping.get(pais_nombre)
            
            if normalized_name:
                try:
                    country = Country.objects.get(name__iexact=normalized_name)
                    empresa.country = country
                    empresa.save()
                    updated_count += 1
                    print(f"✅ Migrada empresa '{empresa.nombre}': {empresa.pais} -> {country.name}")
                except Country.DoesNotExist:
                    not_found_count += 1
                    not_found_countries.add(empresa.pais)
                    print(f"❌ País no encontrado: {empresa.pais} (empresa: {empresa.nombre})")
            else:
                # Intentar búsqueda directa
                try:
                    country = Country.objects.get(name__iexact=pais_nombre)
                    empresa.country = country
                    empresa.save()
                    updated_count += 1
                    print(f"✅ Migrada empresa '{empresa.nombre}': {empresa.pais} -> {country.name}")
                except Country.DoesNotExist:
                    not_found_count += 1
                    not_found_countries.add(empresa.pais)
                    print(f"❌ País no encontrado: {empresa.pais} (empresa: {empresa.nombre})")
    
    print(f"\n📊 RESUMEN DE MIGRACIÓN:")
    print(f"   - Empresas migradas exitosamente: {updated_count}")
    print(f"   - Empresas con países no encontrados: {not_found_count}")
    
    if not_found_countries:
        print(f"\n⚠️  Países no encontrados en la base de datos:")
        for pais in sorted(not_found_countries):
            print(f"   - {pais}")
        
        print(f"\n💡 SUGERENCIAS:")
        print(f"   1. Verificar que estos países existan en la tabla Country")
        print(f"   2. Ejecutar el comando populate_countries_states si no están cargados")
        print(f"   3. Agregar mapeos adicionales al script si es necesario")
    
    # Verificar empresas que aún no tienen country
    empresas_sin_country_final = Empresa.objects.filter(country__isnull=True)
    if empresas_sin_country_final.exists():
        print(f"\n⚠️  Empresas que aún no tienen país asignado: {empresas_sin_country_final.count()}")
        for empresa in empresas_sin_country_final:
            print(f"   - {empresa.nombre} (pais legacy: '{empresa.pais}')")
    
    print(f"\n✅ Migración completada!")


def verify_migration():
    """
    Verifica el estado de la migración
    """
    print("\n🔍 Verificando estado de la migración...")
    
    total_empresas = Empresa.objects.count()
    empresas_con_country = Empresa.objects.filter(country__isnull=False).count()
    empresas_sin_country = Empresa.objects.filter(country__isnull=True).count()
    
    print(f"📊 Estadísticas:")
    print(f"   - Total de empresas: {total_empresas}")
    print(f"   - Empresas con country FK: {empresas_con_country}")
    print(f"   - Empresas sin country FK: {empresas_sin_country}")
    
    if empresas_sin_country > 0:
        print(f"\n⚠️  Empresas que requieren atención:")
        for empresa in Empresa.objects.filter(country__isnull=True):
            print(f"   - {empresa.nombre} (pais legacy: '{empresa.pais}')")
    
    # Verificar consistencia entre campos legacy y nuevos
    inconsistencias = 0
    for empresa in Empresa.objects.all():
        if empresa.country and empresa.pais:
            if empresa.country.name.lower() != empresa.pais.lower():
                inconsistencias += 1
                print(f"⚠️  Inconsistencia en {empresa.nombre}: country='{empresa.country.name}' vs pais='{empresa.pais}'")
    
    if inconsistencias == 0:
        print(f"\n✅ No se encontraron inconsistencias entre campos legacy y nuevos")


if __name__ == "__main__":
    try:
        print("🚀 Script de migración de campo país en empresas")
        print("=" * 60)
        
        # Verificar que el campo country existe
        try:
            Empresa._meta.get_field('country')
            print("✅ Campo 'country' encontrado en modelo Empresa")
        except Exception as e:
            print(f"❌ Error: Campo 'country' no encontrado en modelo Empresa")
            print(f"   Asegúrate de haber aplicado la migración que agrega este campo")
            sys.exit(1)
        
        # Ejecutar migración
        migrate_empresa_country_field()
        
        # Verificar resultado
        verify_migration()
        
    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 