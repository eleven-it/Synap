"""
Servicio de Mapeo Inteligente de Nombres para AdministraNET ↔ Tiendanube.
Maneja variaciones, sinónimos y búsquedas fuzzy para convertir nombres a IDs.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
from django.db import connections
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class IntelligentNameMappingService:
    """
    Servicio para mapeo inteligente de nombres con variaciones y sinónimos.
    Maneja casos como "Buenos Aires" vs "Baires" vs "Bs As".
    """
    
    def __init__(self, adminet_config=None):
        self.adminet_config = adminet_config
        self._cache = {}  # Cache para evitar consultas repetidas
        
        # Diccionarios de sinónimos y variaciones
        self.province_variations = {
            'buenos aires': ['baires', 'bs as', 'bsas', 'buenos aires', 'caba', 'capital federal'],
            'córdoba': ['cordoba', 'cba', 'cba.'],
            'santa fe': ['santa fe', 'sf', 'santafe'],
            'mendoza': ['mza', 'mendoza'],
            'tucumán': ['tucuman', 'tuc', 'tuc.'],
            'salta': ['salta', 'sla'],
            'entre ríos': ['entre rios', 'er', 'entre ríos'],
            'río negro': ['rio negro', 'rn', 'río negro'],
            'chubut': ['chubut', 'chu'],
            'neuquén': ['neuquen', 'neu', 'neuquén'],
            'la pampa': ['la pampa', 'lp', 'pampa'],
            'la rioja': ['la rioja', 'lr', 'rioja'],
            'santiago del estero': ['santiago del estero', 'sde', 'santiago'],
            'san luis': ['san luis', 'sl'],
            'catamarca': ['catamarca', 'cat'],
            'jujuy': ['jujuy', 'juj'],
            'chaco': ['chaco', 'cha'],
            'formosa': ['formosa', 'for'],
            'misiones': ['misiones', 'mis'],
            'corrientes': ['corrientes', 'cor'],
            'san juan': ['san juan', 'sj'],
            'tierra del fuego': ['tierra del fuego', 'tdf', 'fuego'],
        }
        
        self.country_variations = {
            'argentina': ['argentina', 'arg', 'ar', 'argentine republic'],
            'brasil': ['brasil', 'brazil', 'br'],
            'chile': ['chile', 'cl'],
            'uruguay': ['uruguay', 'uy'],
            'paraguay': ['paraguay', 'py'],
            'bolivia': ['bolivia', 'bo'],
            'perú': ['peru', 'pe', 'perú'],
            'colombia': ['colombia', 'co'],
            'venezuela': ['venezuela', 've'],
            'ecuador': ['ecuador', 'ec'],
        }
        
        self.city_variations = {
            'buenos aires': ['caba', 'capital federal', 'buenos aires', 'baires'],
            'córdoba': ['cordoba', 'cba', 'cba.'],
            'rosario': ['rosario', 'ros'],
            'la plata': ['la plata', 'lp'],
            'mar del plata': ['mar del plata', 'mdp', 'mar del plata'],
            'mendoza': ['mza', 'mendoza'],
            'tucumán': ['tucuman', 'tuc', 'tuc.'],
            'salta': ['salta', 'sla'],
            'neuquén': ['neuquen', 'neu', 'neuquén'],
            'bahía blanca': ['bahia blanca', 'bb', 'bahía blanca'],
            'resistencia': ['resistencia', 'res'],
            'paraná': ['parana', 'paraná'],
            'santiago del estero': ['santiago del estero', 'sde', 'santiago'],
            'san luis': ['san luis', 'sl'],
            'catamarca': ['catamarca', 'cat'],
            'jujuy': ['jujuy', 'juj'],
            'formosa': ['formosa', 'for'],
            'posadas': ['posadas', 'pos'],
            'corrientes': ['corrientes', 'cor'],
            'san juan': ['san juan', 'sj'],
            'ushuaia': ['ushuaia', 'ush'],
        }
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto para comparaciones: lowercase, sin acentos, sin espacios extra.
        """
        if not text:
            return ''
        
        # Convertir a minúsculas
        text = text.lower().strip()
        
        # Remover acentos
        text = text.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        text = text.replace('ñ', 'n')
        
        # Remover caracteres especiales y espacios extra
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def find_best_match(self, search_term: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Encuentra la mejor coincidencia usando fuzzy matching.
        """
        if not search_term or not candidates:
            return None
        
        normalized_search = self.normalize_text(search_term)
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            normalized_candidate = self.normalize_text(candidate)
            
            # Verificar si es una coincidencia exacta después de normalización
            if normalized_search == normalized_candidate:
                return candidate
            
            # Verificar variaciones conocidas
            if normalized_search in self._get_all_variations(candidate):
                return candidate
            
            # Fuzzy matching
            score = SequenceMatcher(None, normalized_search, normalized_candidate).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate
        
        return best_match
    
    def _get_all_variations(self, name: str) -> List[str]:
        """
        Obtiene todas las variaciones conocidas de un nombre.
        """
        normalized_name = self.normalize_text(name)
        all_variations = []
        
        # Buscar en provincia_variations
        for main_name, variations in self.province_variations.items():
            if normalized_name == self.normalize_text(main_name):
                all_variations.extend([self.normalize_text(v) for v in variations])
        
        # Buscar en country_variations
        for main_name, variations in self.country_variations.items():
            if normalized_name == self.normalize_text(main_name):
                all_variations.extend([self.normalize_text(v) for v in variations])
        
        # Buscar en city_variations
        for main_name, variations in self.city_variations.items():
            if normalized_name == self.normalize_text(main_name):
                all_variations.extend([self.normalize_text(v) for v in variations])
        
        return all_variations
    
    def get_province_code(self, province_name: str) -> Optional[int]:
        """
        Obtiene el código de provincia desde el nombre con manejo de variaciones.
        """
        cache_key = f"province_{province_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todas las provincias
                cursor.execute("SELECT CodProvincia, Provincia FROM provincia ORDER BY Provincia")
                provinces = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                province_names = [row[1] for row in provinces]
                best_match = self.find_best_match(province_name, province_names)
                
                if best_match:
                    # Encontrar el código correspondiente
                    for cod_provincia, nombre_provincia in provinces:
                        if self.normalize_text(nombre_provincia) == self.normalize_text(best_match):
                            self._cache[cache_key] = cod_provincia
                            logger.info(f"Provincia '{province_name}' mapeada a '{best_match}' (ID: {cod_provincia})")
                            return cod_provincia
                
                # Si no se encuentra, usar valor por defecto (Buenos Aires)
                logger.warning(f"Provincia '{province_name}' no encontrada, usando Buenos Aires por defecto")
                self._cache[cache_key] = 2  # Buenos Aires
                return 2
                
        except Exception as e:
            logger.error(f"Error obteniendo código de provincia para '{province_name}': {e}")
            return 2  # Buenos Aires por defecto
    
    def get_country_id(self, country_name: str) -> Optional[int]:
        """
        Obtiene el ID de país desde el nombre con manejo de variaciones.
        """
        cache_key = f"country_{country_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todos los países
                cursor.execute("SELECT id_pais, nombre FROM pais ORDER BY nombre")
                countries = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                country_names = [row[1] for row in countries]
                best_match = self.find_best_match(country_name, country_names)
                
                if best_match:
                    # Encontrar el ID correspondiente
                    for id_pais, nombre_pais in countries:
                        if self.normalize_text(nombre_pais) == self.normalize_text(best_match):
                            self._cache[cache_key] = id_pais
                            logger.info(f"País '{country_name}' mapeado a '{best_match}' (ID: {id_pais})")
                            return id_pais
                
                # Si no se encuentra, usar Argentina por defecto
                logger.warning(f"País '{country_name}' no encontrado, usando Argentina por defecto")
                self._cache[cache_key] = 1  # Argentina
                return 1
                
        except Exception as e:
            logger.error(f"Error obteniendo ID de país para '{country_name}': {e}")
            return 1  # Argentina por defecto
    
    def get_department_id(self, city_name: str) -> Optional[int]:
        """
        Obtiene el ID de departamento desde el nombre de ciudad con manejo de variaciones.
        """
        cache_key = f"department_{city_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todos los departamentos
                cursor.execute("SELECT IDDepartamento, NombreDepartamento FROM departamento ORDER BY NombreDepartamento")
                departments = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                department_names = [row[1] for row in departments]
                best_match = self.find_best_match(city_name, department_names)
                
                if best_match:
                    # Encontrar el ID correspondiente
                    for id_departamento, nombre_departamento in departments:
                        if self.normalize_text(nombre_departamento) == self.normalize_text(best_match):
                            self._cache[cache_key] = id_departamento
                            logger.info(f"Ciudad '{city_name}' mapeada a departamento '{best_match}' (ID: {id_departamento})")
                            return id_departamento
                
                # Si no se encuentra, usar CABA por defecto
                logger.warning(f"Ciudad '{city_name}' no encontrada, usando CABA por defecto")
                self._cache[cache_key] = 1  # CABA
                return 1
                
        except Exception as e:
            logger.error(f"Error obteniendo ID de departamento para '{city_name}': {e}")
            return 1  # CABA por defecto
    
    def get_district_id(self, city_name: str) -> Optional[int]:
        """
        Obtiene el ID de distrito desde el nombre de ciudad con manejo de variaciones.
        """
        cache_key = f"district_{city_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todos los distritos
                cursor.execute("SELECT IDDistrito, Distrito FROM distrito ORDER BY Distrito")
                districts = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                district_names = [row[1] for row in districts]
                best_match = self.find_best_match(city_name, district_names)
                
                if best_match:
                    # Encontrar el ID correspondiente
                    for id_distrito, nombre_distrito in districts:
                        if self.normalize_text(nombre_distrito) == self.normalize_text(best_match):
                            self._cache[cache_key] = id_distrito
                            logger.info(f"Ciudad '{city_name}' mapeada a distrito '{best_match}' (ID: {id_distrito})")
                            return id_distrito
                
                # Si no se encuentra, usar valor por defecto
                logger.warning(f"Ciudad '{city_name}' no encontrada en distritos, usando valor por defecto")
                self._cache[cache_key] = 1
                return 1
                
        except Exception as e:
            logger.error(f"Error obteniendo ID de distrito para '{city_name}': {e}")
            return 1
    
    def get_customer_type_id(self, type_name: str) -> Optional[int]:
        """
        Obtiene el ID de tipo de cliente desde el nombre con manejo de variaciones.
        """
        cache_key = f"customer_type_{type_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todos los tipos de cliente
                cursor.execute("SELECT id_tipo_cliente, nombre_tipo_cliente FROM tipo_cliente ORDER BY nombre_tipo_cliente")
                types = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                type_names = [row[1] for row in types]
                best_match = self.find_best_match(type_name, type_names)
                
                if best_match:
                    # Encontrar el ID correspondiente
                    for id_tipo, nombre_tipo in types:
                        if self.normalize_text(nombre_tipo) == self.normalize_text(best_match):
                            self._cache[cache_key] = id_tipo
                            logger.info(f"Tipo cliente '{type_name}' mapeado a '{best_match}' (ID: {id_tipo})")
                            return id_tipo
                
                # Si no se encuentra, usar valor por defecto
                logger.warning(f"Tipo cliente '{type_name}' no encontrado, usando valor por defecto")
                self._cache[cache_key] = 1
                return 1
                
        except Exception as e:
            logger.error(f"Error obteniendo ID de tipo cliente para '{type_name}': {e}")
            return 1
    
    def get_viajante_id(self, viajante_name: str = None) -> Optional[int]:
        """
        Obtiene el ID de viajante por defecto o por nombre.
        """
        if not viajante_name:
            return 1  # Viajante por defecto
        
        cache_key = f"viajante_{viajante_name.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            with connections['adminet'].cursor() as cursor:
                # Obtener todos los viajantes
                cursor.execute("SELECT CodViajante, NombreViajante FROM viajantes ORDER BY NombreViajante")
                viajantes = cursor.fetchall()
                
                # Buscar coincidencia exacta o fuzzy
                viajante_names = [row[1] for row in viajantes]
                best_match = self.find_best_match(viajante_name, viajante_names)
                
                if best_match:
                    # Encontrar el ID correspondiente
                    for cod_viajante, nombre_viajante in viajantes:
                        if self.normalize_text(nombre_viajante) == self.normalize_text(best_match):
                            self._cache[cache_key] = cod_viajante
                            logger.info(f"Viajante '{viajante_name}' mapeado a '{best_match}' (ID: {cod_viajante})")
                            return cod_viajante
                
                # Si no se encuentra, usar valor por defecto
                logger.warning(f"Viajante '{viajante_name}' no encontrado, usando valor por defecto")
                self._cache[cache_key] = 1
                return 1
                
        except Exception as e:
            logger.error(f"Error obteniendo ID de viajante para '{viajante_name}': {e}")
            return 1
    
    def clear_cache(self):
        """
        Limpia el cache de mapeos.
        """
        self._cache.clear()
        logger.info("Cache de mapeo inteligente limpiado")
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del mapeo inteligente.
        """
        return {
            'cache_size': len(self._cache),
            'cached_mappings': list(self._cache.keys()),
            'province_variations_count': len(self.province_variations),
            'country_variations_count': len(self.country_variations),
            'city_variations_count': len(self.city_variations),
        } 