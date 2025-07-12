import requests
import json
from django.conf import settings


class AIService:
    """Servicio para integración con IA"""
    
    @staticmethod
    def suggest_layout(data, report_type, target_audience):
        """Sugerir layout basado en datos y contexto"""
        try:
            # Endpoint del microservicio de IA
            ai_url = getattr(settings, 'REPORTS_AI_URL', 'http://reports-ai:8000')
            
            payload = {
                'data': data,
                'report_type': report_type,
                'target_audience': target_audience
            }
            
            response = requests.post(
                f"{ai_url}/suggest-layout",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Error en servicio IA: {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión con servicio IA: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    @staticmethod
    def generate_text(data_summary, context, tone='professional'):
        """Generar texto descriptivo usando IA"""
        try:
            ai_url = getattr(settings, 'REPORTS_AI_URL', 'http://reports-ai:8000')
            
            payload = {
                'data_summary': data_summary,
                'context': context,
                'tone': tone
            }
            
            response = requests.post(
                f"{ai_url}/generate-text",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Error en servicio IA: {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión con servicio IA: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    @staticmethod
    def detect_anomalies(data, threshold=0.95):
        """Detectar anomalías en datos"""
        try:
            ai_url = getattr(settings, 'REPORTS_AI_URL', 'http://reports-ai:8000')
            
            payload = {
                'data': data,
                'threshold': threshold
            }
            
            response = requests.post(
                f"{ai_url}/detect-anomalies",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Error en servicio IA: {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión con servicio IA: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    @staticmethod
    def recommend_charts(data_structure):
        """Recomendar tipos de gráficos basado en estructura de datos"""
        try:
            ai_url = getattr(settings, 'REPORTS_AI_URL', 'http://reports-ai:8000')
            
            payload = {
                'data_structure': data_structure
            }
            
            response = requests.post(
                f"{ai_url}/recommend-charts",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Error en servicio IA: {response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión con servicio IA: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            } 