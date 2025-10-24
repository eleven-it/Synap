"""
Sistema de métricas para APIs de IA
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.core.cache import cache
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class AIMetrics:
    """
    Clase para gestionar métricas de uso de APIs de IA
    """
    
    def __init__(self):
        self.cache_prefix = "ai_metrics"
    
    def record_request(self, provider: str, model_id: str, input_tokens: int, 
                      output_tokens: int, cost: float, response_time: float,
                      success: bool = True, error_message: str = None):
        """
        Registra una solicitud a la API de IA
        """
        timestamp = datetime.now()
        date_key = timestamp.strftime("%Y-%m-%d")
        hour_key = timestamp.strftime("%Y-%m-%d-%H")
        
        # Métricas por día
        daily_key = f"{self.cache_prefix}:daily:{date_key}:{provider}:{model_id}"
        daily_metrics = cache.get(daily_key, {
            'requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'total_response_time': 0.0,
            'avg_response_time': 0.0,
            'errors': []
        })
        
        # Métricas por hora
        hourly_key = f"{self.cache_prefix}:hourly:{hour_key}:{provider}:{model_id}"
        hourly_metrics = cache.get(hourly_key, {
            'requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'total_response_time': 0.0,
            'avg_response_time': 0.0,
            'errors': []
        })
        
        # Actualizar métricas diarias
        daily_metrics['requests'] += 1
        if success:
            daily_metrics['successful_requests'] += 1
        else:
            daily_metrics['failed_requests'] += 1
            if error_message:
                daily_metrics['errors'].append({
                    'timestamp': timestamp.isoformat(),
                    'error': error_message
                })
        
        daily_metrics['total_input_tokens'] += input_tokens
        daily_metrics['total_output_tokens'] += output_tokens
        daily_metrics['total_cost'] += cost
        daily_metrics['total_response_time'] += response_time
        daily_metrics['avg_response_time'] = daily_metrics['total_response_time'] / daily_metrics['requests']
        
        # Actualizar métricas por hora
        hourly_metrics['requests'] += 1
        if success:
            hourly_metrics['successful_requests'] += 1
        else:
            hourly_metrics['failed_requests'] += 1
            if error_message:
                hourly_metrics['errors'].append({
                    'timestamp': timestamp.isoformat(),
                    'error': error_message
                })
        
        hourly_metrics['total_input_tokens'] += input_tokens
        hourly_metrics['total_output_tokens'] += output_tokens
        hourly_metrics['total_cost'] += cost
        hourly_metrics['total_response_time'] += response_time
        hourly_metrics['avg_response_time'] = hourly_metrics['total_response_time'] / hourly_metrics['requests']
        
        # Guardar en caché
        cache.set(daily_key, daily_metrics, 86400)  # 24 horas
        cache.set(hourly_key, hourly_metrics, 3600)  # 1 hora
        
        # Registrar en log
        logger.info(f"AI Request recorded - Provider: {provider}, Model: {model_id}, "
                   f"Success: {success}, Cost: ${cost:.6f}, Time: {response_time:.2f}s")
    
    def get_daily_metrics(self, date: str = None, provider: str = None, model_id: str = None) -> Dict:
        """
        Obtiene métricas diarias
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if provider and model_id:
            key = f"{self.cache_prefix}:daily:{date}:{provider}:{model_id}"
            return cache.get(key, {})
        
        # Obtener todas las métricas del día
        pattern = f"{self.cache_prefix}:daily:{date}:*"
        all_keys = cache.keys(pattern)
        
        total_metrics = {
            'date': date,
            'total_requests': 0,
            'total_successful_requests': 0,
            'total_failed_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'avg_response_time': 0.0,
            'providers': {},
            'models': {}
        }
        
        for key in all_keys:
            metrics = cache.get(key)
            if metrics:
                # Agregar a totales
                total_metrics['total_requests'] += metrics['requests']
                total_metrics['total_successful_requests'] += metrics['successful_requests']
                total_metrics['total_failed_requests'] += metrics['failed_requests']
                total_metrics['total_input_tokens'] += metrics['total_input_tokens']
                total_metrics['total_output_tokens'] += metrics['total_output_tokens']
                total_metrics['total_cost'] += metrics['total_cost']
                
                # Extraer provider y model del key
                parts = key.split(':')
                if len(parts) >= 5:
                    provider_name = parts[3]
                    model_name = parts[4]
                    
                    # Agrupar por proveedor
                    if provider_name not in total_metrics['providers']:
                        total_metrics['providers'][provider_name] = {
                            'requests': 0,
                            'cost': 0.0,
                            'models': {}
                        }
                    
                    total_metrics['providers'][provider_name]['requests'] += metrics['requests']
                    total_metrics['providers'][provider_name]['cost'] += metrics['total_cost']
                    total_metrics['providers'][provider_name]['models'][model_name] = metrics
                    
                    # Agrupar por modelo
                    if model_name not in total_metrics['models']:
                        total_metrics['models'][model_name] = {
                            'requests': 0,
                            'cost': 0.0,
                            'providers': {}
                        }
                    
                    total_metrics['models'][model_name]['requests'] += metrics['requests']
                    total_metrics['models'][model_name]['cost'] += metrics['total_cost']
                    total_metrics['models'][model_name]['providers'][provider_name] = metrics
        
        # Calcular promedio de tiempo de respuesta
        if total_metrics['total_requests'] > 0:
            total_metrics['avg_response_time'] = sum(
                cache.get(key, {}).get('total_response_time', 0) 
                for key in all_keys
            ) / total_metrics['total_requests']
        
        return total_metrics
    
    def get_hourly_metrics(self, date: str = None, hour: int = None) -> Dict:
        """
        Obtiene métricas por hora
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if hour is not None:
            hour_key = f"{date}-{hour:02d}"
        else:
            hour_key = datetime.now().strftime("%Y-%m-%d-%H")
        
        pattern = f"{self.cache_prefix}:hourly:{hour_key}:*"
        all_keys = cache.keys(pattern)
        
        total_metrics = {
            'hour': hour_key,
            'total_requests': 0,
            'total_successful_requests': 0,
            'total_failed_requests': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0,
            'avg_response_time': 0.0,
            'providers': {}
        }
        
        for key in all_keys:
            metrics = cache.get(key)
            if metrics:
                total_metrics['total_requests'] += metrics['requests']
                total_metrics['total_successful_requests'] += metrics['successful_requests']
                total_metrics['total_failed_requests'] += metrics['failed_requests']
                total_metrics['total_input_tokens'] += metrics['total_input_tokens']
                total_metrics['total_output_tokens'] += metrics['total_output_tokens']
                total_metrics['total_cost'] += metrics['total_cost']
                
                # Agrupar por proveedor
                parts = key.split(':')
                if len(parts) >= 5:
                    provider_name = parts[3]
                    if provider_name not in total_metrics['providers']:
                        total_metrics['providers'][provider_name] = {
                            'requests': 0,
                            'cost': 0.0
                        }
                    
                    total_metrics['providers'][provider_name]['requests'] += metrics['requests']
                    total_metrics['providers'][provider_name]['cost'] += metrics['total_cost']
        
        if total_metrics['total_requests'] > 0:
            total_metrics['avg_response_time'] = sum(
                cache.get(key, {}).get('total_response_time', 0) 
                for key in all_keys
            ) / total_metrics['total_requests']
        
        return total_metrics
    
    def get_cost_analysis(self, days: int = 7) -> Dict:
        """
        Análisis de costos por período
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cost_analysis = {
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'total_cost': 0.0,
            'daily_costs': {},
            'provider_costs': {},
            'model_costs': {},
            'cost_trend': []
        }
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_metrics = self.get_daily_metrics(date_str)
            
            daily_cost = daily_metrics.get('total_cost', 0.0)
            cost_analysis['total_cost'] += daily_cost
            cost_analysis['daily_costs'][date_str] = daily_cost
            
            # Agregar a tendencia
            cost_analysis['cost_trend'].append({
                'date': date_str,
                'cost': daily_cost
            })
            
            # Agrupar por proveedor
            for provider, data in daily_metrics.get('providers', {}).items():
                if provider not in cost_analysis['provider_costs']:
                    cost_analysis['provider_costs'][provider] = 0.0
                cost_analysis['provider_costs'][provider] += data['cost']
            
            # Agrupar por modelo
            for model, data in daily_metrics.get('models', {}).items():
                if model not in cost_analysis['model_costs']:
                    cost_analysis['model_costs'][model] = 0.0
                cost_analysis['model_costs'][model] += data['cost']
            
            current_date += timedelta(days=1)
        
        return cost_analysis
    
    def get_performance_metrics(self, hours: int = 24) -> Dict:
        """
        Métricas de rendimiento
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        performance_metrics = {
            'period_hours': hours,
            'total_requests': 0,
            'success_rate': 0.0,
            'avg_response_time': 0.0,
            'total_cost': 0.0,
            'hourly_performance': [],
            'error_rate': 0.0,
            'peak_hour': None,
            'peak_requests': 0
        }
        
        current_time = start_time
        total_response_time = 0.0
        total_errors = 0
        
        while current_time <= end_time:
            hour_key = current_time.strftime("%Y-%m-%d-%H")
            hourly_metrics = self.get_hourly_metrics(
                current_time.strftime("%Y-%m-%d"), 
                current_time.hour
            )
            
            requests = hourly_metrics.get('total_requests', 0)
            performance_metrics['total_requests'] += requests
            performance_metrics['total_cost'] += hourly_metrics.get('total_cost', 0.0)
            total_response_time += hourly_metrics.get('avg_response_time', 0.0) * requests
            total_errors += hourly_metrics.get('total_failed_requests', 0)
            
            # Encontrar hora pico
            if requests > performance_metrics['peak_requests']:
                performance_metrics['peak_requests'] = requests
                performance_metrics['peak_hour'] = hour_key
            
            performance_metrics['hourly_performance'].append({
                'hour': hour_key,
                'requests': requests,
                'avg_response_time': hourly_metrics.get('avg_response_time', 0.0),
                'cost': hourly_metrics.get('total_cost', 0.0)
            })
            
            current_time += timedelta(hours=1)
        
        # Calcular métricas finales
        if performance_metrics['total_requests'] > 0:
            performance_metrics['success_rate'] = (
                (performance_metrics['total_requests'] - total_errors) / 
                performance_metrics['total_requests']
            ) * 100
            performance_metrics['avg_response_time'] = total_response_time / performance_metrics['total_requests']
            performance_metrics['error_rate'] = (total_errors / performance_metrics['total_requests']) * 100
        
        return performance_metrics


# Instancia global
ai_metrics = AIMetrics() 