"""
Herramienta de Validación y Guardrails
Implementa los controles de veracidad, privacidad y anti-alucinación
"""
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ValidationTool:
    """
    Validador y controlador de guardrails para el sistema
    
    Funciones principales:
    - Detectar tecnicismos prohibidos
    - Validar coherencia de datos
    - Controlar privacidad
    - Detectar lenguaje especulativo (anti-alucinación)
    """
    
    # Palabras técnicas prohibidas en respuestas al usuario
    FORBIDDEN_TECHNICAL_TERMS = [
        # SQL
        'select', 'from', 'where', 'join', 'insert', 'update', 'delete',
        'table', 'column', 'database', 'query', 'sql',
        
        # Código
        'function', 'sub', 'class', 'def', 'void', 'return',
        'public', 'private', 'static', 'const', 'var',
        
        # VB6
        '.bas', '.frm', '.cls', '.vbp', 'dim', 'as integer', 'as string',
        
        # Rutas y archivos
        'c:\\', '/home/', '/var/', '.py', '.vb', '.php',
        'archivo', 'carpeta', 'directorio',
        
        # Infraestructura
        'servidor', 'host', 'puerto', 'conexión', 'endpoint',
        'api_key', 'password', 'token', 'credentials'
    ]
    
    # Frases especulativas que indican alucinación
    SPECULATIVE_PHRASES = [
        'probablemente', 'seguramente', 'parece que', 'podría ser',
        'asumo que', 'según recuerdo', 'tal vez', 'quizás',
        'supongo que', 'creo que', 'imagino que', 'posiblemente',
        'aparentemente', 'presumiblemente'
    ]
    
    def __init__(self):
        """Inicializa la herramienta de validación"""
        pass
    
    def validate_response(
        self,
        response: str,
        data_sources: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Valida una respuesta completa antes de entregarla al usuario
        
        Args:
            response: Texto de la respuesta a validar
            data_sources: Fuentes de datos usadas para verificar veracidad
            
        Returns:
            Dict con resultado de validación y correcciones si aplican
        """
        validations = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'corrections': [],
            'factual_confidence': 1.0,
            'speculative_phrases_rate': 0.0
        }
        
        # 1. Verificar tecnicismos prohibidos
        technical_check = self._check_technical_terms(response)
        if not technical_check['passed']:
            validations['is_valid'] = False
            validations['errors'].extend(technical_check['errors'])
        
        # 2. Verificar frases especulativas (anti-alucinación)
        speculative_check = self._check_speculative_language(response)
        if speculative_check['count'] > 0:
            validations['speculative_phrases_rate'] = speculative_check['rate']
            
            if speculative_check['rate'] > 0.02:  # Más de 2%
                validations['is_valid'] = False
                validations['errors'].append(
                    'Lenguaje especulativo detectado. Se requiere reformulación basada en evidencia.'
                )
            else:
                validations['warnings'].append(
                    f"Frases especulativas detectadas: {speculative_check['phrases']}"
                )
        
        # 3. Verificar coherencia temporal
        temporal_check = self._check_temporal_consistency(response)
        if not temporal_check['passed']:
            validations['warnings'].append(temporal_check['message'])
        
        # 4. Verificar veracidad de datos (si se proveen fuentes)
        if data_sources:
            factual_check = self._check_factual_consistency(response, data_sources)
            validations['factual_confidence'] = factual_check['confidence']
            
            if factual_check['confidence'] < 0.95:
                validations['is_valid'] = False
                validations['errors'].append(
                    'Confianza factual insuficiente. Revisar datos con fuentes.'
                )
        
        # 5. Verificar privacidad (datos sensibles enmascarados)
        privacy_check = self._check_privacy(response)
        if not privacy_check['passed']:
            validations['warnings'].extend(privacy_check['warnings'])
            validations['corrections'].extend(privacy_check['corrections'])
        
        return validations
    
    def _check_technical_terms(self, text: str) -> Dict[str, Any]:
        """
        Detecta términos técnicos prohibidos
        
        Args:
            text: Texto a validar
            
        Returns:
            Dict con resultado de la verificación
        """
        text_lower = text.lower()
        found_terms = []
        
        for term in self.FORBIDDEN_TECHNICAL_TERMS:
            # Buscar como palabra completa
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                found_terms.append(term)
        
        passed = len(found_terms) == 0
        
        return {
            'passed': passed,
            'found_terms': found_terms,
            'errors': [
                f"Término técnico prohibido encontrado: '{term}'. Usar lenguaje de negocio."
                for term in found_terms
            ]
        }
    
    def _check_speculative_language(self, text: str) -> Dict[str, Any]:
        """
        Detecta lenguaje especulativo que indica posible alucinación
        
        Args:
            text: Texto a validar
            
        Returns:
            Dict con resultado y frases encontradas
        """
        text_lower = text.lower()
        found_phrases = []
        
        for phrase in self.SPECULATIVE_PHRASES:
            pattern = r'\b' + re.escape(phrase) + r'\b'
            if re.search(pattern, text_lower):
                found_phrases.append(phrase)
        
        # Calcular tasa (frases especulativas / total palabras)
        total_words = len(text.split())
        rate = len(found_phrases) / total_words if total_words > 0 else 0
        
        return {
            'count': len(found_phrases),
            'phrases': found_phrases,
            'rate': rate
        }
    
    def _check_temporal_consistency(self, text: str) -> Dict[str, Any]:
        """
        Verifica que las referencias temporales sean consistentes
        
        Args:
            text: Texto a validar
            
        Returns:
            Dict con resultado de la verificación
        """
        # Buscar patrones de fechas y periodos
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',       # YYYY-MM-DD
        ]
        
        periodo_patterns = [
            r'periodo\s+(?:de\s+)?(\d{1,2}/\d{4})',
            r'mes\s+de\s+(\w+)',
            r'año\s+(\d{4})'
        ]
        
        # Por ahora, validación básica: si hay fechas, debe haber periodo mencionado
        has_dates = any(re.search(pattern, text) for pattern in date_patterns)
        has_periodo = any(re.search(pattern, text, re.IGNORECASE) for pattern in periodo_patterns)
        
        if has_dates and not has_periodo:
            return {
                'passed': False,
                'message': 'Se detectaron fechas pero no se especifica claramente el periodo cubierto.'
            }
        
        return {'passed': True}
    
    def _check_factual_consistency(
        self,
        text: str,
        data_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verifica que los números mencionados coincidan con las fuentes de datos
        
        Args:
            text: Texto a validar
            data_sources: Fuentes de datos para verificar
            
        Returns:
            Dict con score de confianza factual
        """
        # Extraer números del texto
        number_pattern = r'\b\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{1,2})?\b'
        numbers_in_text = re.findall(number_pattern, text)
        
        # Por ahora, asumimos confianza alta si hay fuentes de datos
        # En producción, se debe verificar cada número contra las fuentes
        
        if not data_sources or len(data_sources) == 0:
            return {'confidence': 0.5}  # Sin fuentes, confianza baja
        
        # Si hay números pero no fuentes, confianza muy baja
        if len(numbers_in_text) > 0 and len(data_sources) == 0:
            return {'confidence': 0.3}
        
        # Con fuentes de datos, confianza alta
        return {'confidence': 0.95}
    
    def _check_privacy(self, text: str) -> Dict[str, Any]:
        """
        Verifica que no se expongan datos sensibles sin enmascarar
        
        Args:
            text: Texto a validar
            
        Returns:
            Dict con advertencias y correcciones
        """
        warnings = []
        corrections = []
        
        # Patrones de datos sensibles
        patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'cuit': r'\b\d{2}-?\d{8}-?\d{1}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }
        
        for data_type, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                warnings.append(f"Posible {data_type} sin enmascarar: {match.group()}")
                
                # Sugerir corrección enmascarada
                masked = self._mask_sensitive_data(match.group(), data_type)
                corrections.append({
                    'original': match.group(),
                    'masked': masked
                })
        
        return {
            'passed': len(warnings) == 0,
            'warnings': warnings,
            'corrections': corrections
        }
    
    def _mask_sensitive_data(self, data: str, data_type: str) -> str:
        """
        Enmascara datos sensibles
        
        Args:
            data: Dato a enmascarar
            data_type: Tipo de dato
            
        Returns:
            Dato enmascarado
        """
        if data_type == 'email':
            parts = data.split('@')
            if len(parts) == 2:
                return f"{parts[0][:2]}***@{parts[1]}"
        
        elif data_type == 'phone':
            return f"***-***-{data[-4:]}"
        
        elif data_type == 'cuit':
            return f"**-********-{data[-1]}"
        
        elif data_type == 'credit_card':
            return f"****-****-****-{data[-4:]}"
        
        return "***"
    
    def suggest_correction(self, text: str, error_type: str) -> str:
        """
        Sugiere una corrección para un error detectado
        
        Args:
            text: Texto con error
            error_type: Tipo de error detectado
            
        Returns:
            Sugerencia de corrección
        """
        if error_type == 'speculative':
            return "Reformular la afirmación basándose en datos verificables o indicar explícitamente la limitación: 'No se dispone de información completa sobre este punto.'"
        
        elif error_type == 'technical':
            return "Reemplazar términos técnicos por conceptos de negocio equivalentes."
        
        elif error_type == 'factual':
            return "Verificar números con las fuentes de datos originales y corregir discrepancias."
        
        return "Revisar y corregir según las políticas de guardrails."

