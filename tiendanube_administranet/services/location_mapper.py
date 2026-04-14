"""
Servicio de mapeo inteligente de ubicaciones entre Tiendanube y AdministraNET.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from difflib import SequenceMatcher
from ..models import AdministraNETConfig
from .adminet_service import AdministraNETService

logger = logging.getLogger(__name__)


class LocationMapper:
    """
    Mapeador inteligente de ubicaciones entre Tiendanube y AdministraNET.
    """
    
    def __init__(self, adminet_config: AdministraNETConfig, base_empresa: Optional[str] = None):
        self.adminet_config = adminet_config
        be = (base_empresa or (adminet_config.database or "")).strip()
        self.adminet_service = AdministraNETService(adminet_config, base_empresa=be)
        self._provinces_cache = None
        self._departments_cache = None
    
    def _get_provinces(self) -> Dict[str, Any]:
        """Obtener cache de provincias."""
        if self._provinces_cache is None:
            try:
                result = self.adminet_service.execute_query('SELECT * FROM provincia WHERE anulado = "No"')
                if result['success']:
                    self._provinces_cache = {p['Provincia'].lower(): p for p in result['results']}
                else:
                    self._provinces_cache = {}
                    logger.error(f"Error obteniendo provincias: {result['message']}")
            except Exception as e:
                self._provinces_cache = {}
                logger.error(f"Error obteniendo provincias: {e}")
        return self._provinces_cache
    
    def _get_departments(self) -> Dict[str, Any]:
        """Obtener cache de departamentos."""
        if self._departments_cache is None:
            try:
                result = self.adminet_service.execute_query('SELECT * FROM departamento WHERE anulado = "No"')
                if result['success']:
                    self._departments_cache = {d['NombreDepartamento'].lower(): d for d in result['results']}
                else:
                    self._departments_cache = {}
                    logger.error(f"Error obteniendo departamentos: {result['message']}")
            except Exception as e:
                self._departments_cache = {}
                logger.error(f"Error obteniendo departamentos: {e}")
        return self._departments_cache
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para comparación."""
        if not text:
            return ""
        
        # Convertir a minúsculas y limpiar
        normalized = text.lower().strip()
        
        # Reemplazar caracteres especiales
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u',
            'de': ' ', 'del': ' ', 'la': ' ', 'el': ' ', 'los': ' ', 'las': ' '
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Limpiar espacios múltiples
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcular similitud entre dos textos."""
        if not text1 or not text2:
            return 0.0
        
        normalized1 = self._normalize_text(text1)
        normalized2 = self._normalize_text(text2)
        
        return SequenceMatcher(None, normalized1, normalized2).ratio()
    
    def find_province(self, province_name: str) -> Optional[Dict[str, Any]]:
        """
        Encontrar provincia por nombre usando análisis predictivo.
        
        Args:
            province_name: Nombre de la provincia desde Tiendanube
            
        Returns:
            Diccionario con datos de la provincia o None si no se encuentra
        """
        if not province_name:
            return None
        
        provinces = self._get_provinces()
        if not provinces:
            return None
        
        # Mapeos específicos para abreviaciones comunes
        abbreviation_mappings = {
            'cba': 'cordoba',
            'cba.': 'cordoba',
            'cordoba': 'cordoba',
            'caba': 'caba',
            'c.a.b.a': 'caba',
            'buenos aires': 'buenos aires',
            'bs as': 'buenos aires',
            'bs. as.': 'buenos aires',
            'mendoza': 'mendoza',
            'santa fe': 'santa fe',
            'sfe': 'santa fe',
            'tucuman': 'tucuman',
            'tuc': 'tucuman',
            'salta': 'salta',
            'jujuy': 'jujuy',
            'la rioja': 'la rioja',
            'san juan': 'san juan',
            'san luis': 'san luis',
            'catamarca': 'catamarca',
            'santiago del estero': 'sgo. del estero',
            'sgo del estero': 'sgo. del estero',
            'formosa': 'formosa',
            'chaco': 'chaco',
            'corrientes': 'corrientes',
            'misiones': 'misiones',
            'entre rios': 'entre rios',
            'neuquen': 'neuquen',
            'rio negro': 'rio negro',
            'chubut': 'chubut',
            'santa cruz': 'santa cruz',
            'tierra del fuego': 'tierra del fuego',
            'la pampa': 'la pampa'
        }
        
        # Normalizar nombre de provincia
        normalized_input = self._normalize_text(province_name)
        
        # Verificar mapeos de abreviaciones
        if normalized_input in abbreviation_mappings:
            mapped_name = abbreviation_mappings[normalized_input]
            if mapped_name in provinces:
                logger.info(f"Provincia '{province_name}' mapeada por abreviación a '{mapped_name}'")
                return provinces[mapped_name]
        
        # Buscar coincidencia exacta
        if normalized_input in provinces:
            return provinces[normalized_input]
        
        # Buscar por similitud
        best_match = None
        best_similarity = 0.0
        threshold = 0.6  # Umbral de similitud mínimo
        
        for stored_name, province_data in provinces.items():
            similarity = self._calculate_similarity(province_name, stored_name)
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = province_data
        
        if best_match:
            logger.info(f"Provincia '{province_name}' mapeada a '{best_match['Provincia']}' (similitud: {best_similarity:.2f})")
            return best_match
        
        logger.warning(f"No se encontró provincia para '{province_name}'")
        return None
    
    def find_department(self, city_name: str, province_code: int = None) -> Optional[Dict[str, Any]]:
        """
        Encontrar departamento por nombre de ciudad usando análisis predictivo.
        
        Args:
            city_name: Nombre de la ciudad desde Tiendanube
            province_code: Código de provincia para filtrar (opcional)
            
        Returns:
            Diccionario con datos del departamento o None si no se encuentra
        """
        if not city_name:
            return None
        
        departments = self._get_departments()
        if not departments:
            return None
        
        # Filtrar por provincia si se proporciona
        if province_code:
            departments = {k: v for k, v in departments.items() if v['CodProvincia'] == province_code}
        
        # Buscar coincidencia exacta
        normalized_name = self._normalize_text(city_name)
        if normalized_name in departments:
            return departments[normalized_name]
        
        # Buscar por similitud
        best_match = None
        best_similarity = 0.0
        threshold = 0.6  # Umbral de similitud mínimo
        
        for stored_name, dept_data in departments.items():
            similarity = self._calculate_similarity(city_name, stored_name)
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = dept_data
        
        if best_match:
            logger.info(f"Ciudad '{city_name}' mapeada a departamento '{best_match['NombreDepartamento']}' (similitud: {best_similarity:.2f})")
            return best_match
        
        logger.warning(f"No se encontró departamento para ciudad '{city_name}'")
        return None
    
    def find_department_by_city_and_state(self, city_name: str, state_name: str) -> Optional[Dict[str, Any]]:
        """
        Encontrar departamento usando tanto ciudad como estado para mayor precisión.
        Si no se encuentra en la provincia especificada, buscar en todas las provincias.
        
        Args:
            city_name: Nombre de la ciudad desde Tiendanube
            state_name: Nombre del estado/provincia desde Tiendanube
            
        Returns:
            Diccionario con datos del departamento o None si no se encuentra
        """
        if not city_name:
            return None
        
        # Primero intentar mapear el estado a provincia
        province_data = self.find_province(state_name)
        if not province_data:
            logger.warning(f"No se encontró provincia para estado '{state_name}'")
            return None
        
        province_code = province_data['CodProvincia']
        logger.info(f"Estado '{state_name}' mapeado a provincia {province_code} ({province_data['Provincia']})")
        
        # Buscar departamento en esa provincia
        departments = self._get_departments()
        if not departments:
            return None
        
        # Filtrar por provincia
        province_departments = {k: v for k, v in departments.items() if v['CodProvincia'] == province_code}
        
        if not province_departments:
            logger.warning(f"No hay departamentos para provincia {province_code}")
            return None
        
        # Buscar coincidencia exacta
        normalized_name = self._normalize_text(city_name)
        if normalized_name in province_departments:
            return province_departments[normalized_name]
        
        # Buscar por similitud
        best_match = None
        best_similarity = 0.0
        threshold = 0.6  # Umbral de similitud mínimo
        
        for stored_name, dept_data in province_departments.items():
            similarity = self._calculate_similarity(city_name, stored_name)
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = dept_data
        
        if best_match:
            logger.info(f"Ciudad '{city_name}' en provincia {province_code} mapeada a departamento '{best_match['NombreDepartamento']}' (similitud: {best_similarity:.2f})")
            return best_match
        
        # Si no se encuentra en la provincia especificada, buscar en todas las provincias
        logger.warning(f"No se encontró departamento para ciudad '{city_name}' en provincia {province_code}")
        logger.info(f"Buscando '{city_name}' en todas las provincias...")
        
        # Buscar en todas las provincias
        best_match_all = None
        best_similarity_all = 0.0
        threshold_all = 0.8  # Umbral más alto para búsqueda global
        
        for stored_name, dept_data in departments.items():
            similarity = self._calculate_similarity(city_name, stored_name)
            if similarity > best_similarity_all and similarity >= threshold_all:
                best_similarity_all = similarity
                best_match_all = dept_data
        
        if best_match_all:
            logger.info(f"Ciudad '{city_name}' encontrada en provincia {best_match_all['CodProvincia']} - departamento '{best_match_all['NombreDepartamento']}' (similitud: {best_similarity_all:.2f})")
            logger.warning(f"DATOS INCONSISTENTES: Ciudad '{city_name}' está en provincia {best_match_all['CodProvincia']}, no en {province_data['Provincia']}")
            return best_match_all
        
        logger.warning(f"No se encontró departamento para ciudad '{city_name}' en ninguna provincia")
        return None
    
    def map_location(self, province_name: str, city_name: str) -> Tuple[Optional[int], Optional[int], str]:
        """
        Mapear ubicación completa (provincia y ciudad) a códigos de AdministraNET.
        
        Args:
            province_name: Nombre de la provincia desde Tiendanube
            city_name: Nombre de la ciudad desde Tiendanube
            
        Returns:
            Tupla con (cod_provincia, id_departamento, calle_completa)
        """
        # Buscar departamento usando el método inteligente
        if province_name and city_name:
            department_data = self.find_department_by_city_and_state(city_name, province_name)
        else:
            # Buscar provincia
            province_data = self.find_province(province_name)
            cod_provincia = province_data['CodProvincia'] if province_data else None
            department_data = self.find_department(city_name, cod_provincia)
        
        # Si se encontró departamento, usar su provincia real
        if department_data:
            cod_provincia = department_data['CodProvincia']
            id_departamento = department_data['IDDepartamento']
        else:
            # Fallback: usar provincia del usuario
            province_data = self.find_province(province_name)
            cod_provincia = province_data['CodProvincia'] if province_data else None
            id_departamento = None
        
        # Construir calle completa con información de ubicación
        calle_parts = []
        if city_name:
            calle_parts.append(city_name)
        if province_name:
            calle_parts.append(province_name)
        
        calle_completa = ', '.join(calle_parts) if calle_parts else ''
        
        logger.info(f"Mapeo de ubicación: '{city_name}, {province_name}' -> Prov: {cod_provincia}, Depto: {id_departamento}")
        
        return cod_provincia, id_departamento, calle_completa
    
    def build_complete_address(self, street: str, number: str, floor: str, locality: str, 
                              city: str, province: str) -> str:
        """
        Construir dirección completa incluyendo información de ubicación.
        
        Args:
            street: Calle
            number: Número
            floor: Piso/Dpto
            locality: Localidad/Barrio
            city: Ciudad
            province: Provincia
            
        Returns:
            Dirección completa formateada
        """
        address_parts = []
        
        # Dirección básica
        if street and number:
            address_parts.append(f"{street} {number}")
        elif street:
            address_parts.append(street)
        
        # Piso/Dpto
        if floor:
            address_parts.append(floor)
        
        # Localidad/Barrio
        if locality:
            address_parts.append(locality)
        
        # Ciudad
        if city:
            address_parts.append(city)
        
        # Provincia
        if province:
            address_parts.append(province)
        
        return ', '.join(address_parts)
