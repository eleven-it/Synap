"""
Utilidades para el sistema de soporte IA
"""
import re
from typing import Dict, List, Tuple
from datetime import datetime


def analyze_sentiment(message: str) -> Dict[str, any]:
    """
    Análisis básico de sentimientos basado en palabras clave
    """
    message_lower = message.lower()
    
    # Palabras positivas
    positive_words = [
        'gracias', 'excelente', 'perfecto', 'genial', 'bueno', 'bien', 
        'funciona', 'resuelto', 'satisfecho', 'contento', 'feliz', 'ayuda'
    ]
    
    # Palabras negativas
    negative_words = [
        'problema', 'error', 'falla', 'no funciona', 'roto', 'malo', 
        'frustrado', 'enojado', 'molesto', 'urgente', 'crítico', 'desesperado'
    ]
    
    # Palabras de urgencia
    urgent_words = [
        'urgente', 'crítico', 'emergencia', 'inmediato', 'ahora', 
        'desesperado', 'no puedo', 'bloqueado', 'parado'
    ]
    
    # Contar ocurrencias
    positive_count = sum(1 for word in positive_words if word in message_lower)
    negative_count = sum(1 for word in negative_words if word in message_lower)
    urgent_count = sum(1 for word in urgent_words if word in message_lower)
    
    # Determinar sentimiento
    if urgent_count > 0:
        sentiment = 'urgent'
        priority = 'high'
    elif negative_count > positive_count:
        sentiment = 'negative'
        priority = 'medium'
    elif positive_count > negative_count:
        sentiment = 'positive'
        priority = 'low'
    else:
        sentiment = 'neutral'
        priority = 'low'
    
    # Detectar emociones específicas
    emotions = []
    if any(word in message_lower for word in ['frustrado', 'molesto', 'enojado']):
        emotions.append('frustration')
    if any(word in message_lower for word in ['confundido', 'no entiendo', 'perdido']):
        emotions.append('confusion')
    if any(word in message_lower for word in ['feliz', 'contento', 'satisfecho']):
        emotions.append('satisfaction')
    
    return {
        'sentiment': sentiment,
        'priority': priority,
        'emotions': emotions,
        'confidence': min(0.9, (positive_count + negative_count + urgent_count) / 10),
        'positive_score': positive_count,
        'negative_score': negative_count,
        'urgent_score': urgent_count
    }


def extract_keywords(message: str) -> List[str]:
    """
    Extrae palabras clave del mensaje
    """
    # Palabras comunes a ignorar
    stop_words = {
        'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero',
        'si', 'no', 'que', 'como', 'cuando', 'donde', 'por', 'para', 'con', 'sin',
        'sobre', 'entre', 'detrás', 'delante', 'encima', 'debajo', 'dentro', 'fuera',
        'antes', 'después', 'ahora', 'entonces', 'siempre', 'nunca', 'a veces',
        'muy', 'más', 'menos', 'poco', 'mucho', 'todo', 'nada', 'algo', 'nadie',
        'yo', 'tú', 'él', 'ella', 'nosotros', 'vosotros', 'ellos', 'ellas',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
        'mi', 'tu', 'su', 'nuestro', 'vuestro', 'su', 'mío', 'tuyo', 'suyo'
    }
    
    # Limpiar y tokenizar
    words = re.findall(r'\b\w+\b', message.lower())
    
    # Filtrar palabras cortas y stop words
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    return list(set(keywords))  # Eliminar duplicados


def generate_contextual_response(message: str, sentiment_data: Dict, ticket=None) -> Dict[str, any]:
    """
    Genera una respuesta contextual basada en el análisis de sentimientos
    """
    sentiment = sentiment_data['sentiment']
    emotions = sentiment_data['emotions']
    
    # Respuestas base según sentimiento
    responses = {
        'urgent': {
            'response': 'Entiendo que esto es urgente. Voy a ayudarte inmediatamente.',
            'tone': 'empathetic_urgent',
            'suggestions': ['¿Puedes darme más detalles específicos?', '¿Has intentado reiniciar el sistema?']
        },
        'negative': {
            'response': 'Lamento que estés teniendo problemas. Estoy aquí para ayudarte a resolverlo.',
            'tone': 'empathetic_supportive',
            'suggestions': ['¿Cuándo empezó este problema?', '¿Has intentado alguna solución?']
        },
        'positive': {
            'response': '¡Me alegra saber que todo va bien! ¿En qué puedo ayudarte hoy?',
            'tone': 'friendly_positive',
            'suggestions': ['¿Hay algo específico que quieras mejorar?', '¿Te gustaría explorar nuevas funcionalidades?']
        },
        'neutral': {
            'response': 'Hola, ¿en qué puedo ayudarte hoy?',
            'tone': 'professional_neutral',
            'suggestions': ['¿Tienes alguna pregunta específica?', '¿Necesitas ayuda con alguna configuración?']
        }
    }
    
    base_response = responses.get(sentiment, responses['neutral'])
    
    # Personalizar según emociones específicas
    if 'frustration' in emotions:
        base_response['response'] = 'Entiendo tu frustración. Vamos a resolver esto paso a paso.'
        base_response['tone'] = 'calming_supportive'
    elif 'confusion' in emotions:
        base_response['response'] = 'No te preocupes, te voy a explicar de manera clara y sencilla.'
        base_response['tone'] = 'explanatory_patient'
    elif 'satisfaction' in emotions:
        base_response['response'] = '¡Excelente! Me alegra saber que estás satisfecho.'
        base_response['tone'] = 'celebratory_positive'
    
    return base_response


def format_timestamp(timestamp: datetime) -> str:
    """
    Formatea timestamp para mostrar en el chat
    """
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return timestamp.strftime("%d/%m/%Y %H:%M")
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"hace {hours} hora{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        return "ahora mismo"


def categorize_message(message: str) -> str:
    """
    Categoriza el tipo de mensaje
    """
    message_lower = message.lower()
    
    categories = {
        'billing': ['factura', 'pago', 'cobro', 'tarjeta', 'precio', 'costo', 'cuenta'],
        'technical': ['error', 'problema', 'no funciona', 'bug', 'falla', 'crash'],
        'configuration': ['configurar', 'ajustar', 'personalizar', 'configuración', 'setup'],
        'feature_request': ['nueva función', 'mejora', 'sugerencia', 'idea', 'propuesta'],
        'general_help': ['ayuda', 'cómo', 'dónde', 'cuándo', 'qué', 'por qué']
    }
    
    for category, keywords in categories.items():
        if any(keyword in message_lower for keyword in keywords):
            return category
    
    return 'general_help' 