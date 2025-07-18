from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib import messages
from django.utils.translation import gettext as _
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService
import logging

logger = logging.getLogger(__name__)

class TestConnectionView(CorePermissionRequiredMixin, TemplateView):
    """
    Vista completa para testing de conexión con administraNET
    Incluye test básico, test de tablas, test de queries y diagnóstico completo
    """
    template_name = "administraNET_integration/test_connection.html"
    permission_required = "core.can_manage_integrations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración actual
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        
        # Estado inicial
        context['connection_status'] = {
            'basic': False,
            'tables': False,
            'queries': False,
            'performance': False
        }
        
        # Historial de tests recientes
        context['recent_tests'] = self._get_recent_tests()
        
        return context

    def post(self, request, *args, **kwargs):
        """Manejar tests de conexión AJAX"""
        if not request.user.has_perm('core.can_manage_integrations'):
            return JsonResponse({
                'success': False,
                'message': _("No tienes permisos para esta acción.")
            })
        
        test_type = request.POST.get('test_type', 'basic')
        
        try:
            # Obtener configuración
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'message': _("No hay configuración activa. Configura la conexión primero.")
                })
            
            # Crear servicio de conexión
            connection_service = AdministraNETConnectionService(config)
            
            # Ejecutar test según tipo
            if test_type == 'basic':
                result = self._test_basic_connection(connection_service)
            elif test_type == 'tables':
                result = self._test_tables_connection(connection_service)
            elif test_type == 'queries':
                result = self._test_queries_connection(connection_service)
            elif test_type == 'performance':
                result = self._test_performance_connection(connection_service)
            elif test_type == 'full':
                result = self._test_full_connection(connection_service)
            else:
                return JsonResponse({
                    'success': False,
                    'message': _("Tipo de test no válido.")
                })
            
            # Log de auditoría
            logger.info(f"[AUDITORÍA] Usuario {request.user} ejecutó test de conexión tipo '{test_type}'. "
                       f"Resultado: {'Exitoso' if result['success'] else 'Fallido'}")
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en test de conexión: {e}")
            return JsonResponse({
                'success': False,
                'message': _("Error interno durante el test de conexión."),
                'error': str(e)
            })

    def _test_basic_connection(self, connection_service):
        """Test básico de conexión"""
        try:
            result = connection_service.test_connection(test_tables=False)
            
            if result.get('success', False):
                return {
                    'success': True,
                    'message': _("Conexión básica exitosa."),
                    'details': {
                        'server_info': result.get('server_info', {}),
                        'connection_time': result.get('connection_time', 0),
                        'database_name': result.get('database_name', ''),
                    }
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', _("Error en conexión básica.")),
                    'details': result.get('details', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': _("Error en test básico de conexión."),
                'error': str(e)
            }

    def _test_tables_connection(self, connection_service):
        """Test de conexión con verificación de tablas"""
        try:
            result = connection_service.test_connection(test_tables=True)
            
            if result.get('success', False):
                return {
                    'success': True,
                    'message': _("Test de tablas exitoso."),
                    'details': {
                        'tables_found': result.get('tables_found', 0),
                        'table_list': result.get('table_list', []),
                        'connection_time': result.get('connection_time', 0),
                    }
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', _("Error en test de tablas.")),
                    'details': result.get('details', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': _("Error en test de tablas."),
                'error': str(e)
            }

    def _test_queries_connection(self, connection_service):
        """Test de conexión con queries de prueba"""
        try:
            # Test de queries básicas
            queries_result = connection_service.test_queries()
            
            if queries_result.get('success', False):
                return {
                    'success': True,
                    'message': _("Test de queries exitoso."),
                    'details': {
                        'queries_tested': queries_result.get('queries_tested', 0),
                        'queries_successful': queries_result.get('queries_successful', 0),
                        'sample_data': queries_result.get('sample_data', {}),
                        'execution_time': queries_result.get('execution_time', 0),
                    }
                }
            else:
                return {
                    'success': False,
                    'message': queries_result.get('message', _("Error en test de queries.")),
                    'details': queries_result.get('details', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': _("Error en test de queries."),
                'error': str(e)
            }

    def _test_performance_connection(self, connection_service):
        """Test de rendimiento de conexión"""
        try:
            # Test de rendimiento
            performance_result = connection_service.test_performance()
            
            if performance_result.get('success', False):
                return {
                    'success': True,
                    'message': _("Test de rendimiento exitoso."),
                    'details': {
                        'avg_response_time': performance_result.get('avg_response_time', 0),
                        'max_response_time': performance_result.get('max_response_time', 0),
                        'min_response_time': performance_result.get('min_response_time', 0),
                        'connection_pool_size': performance_result.get('connection_pool_size', 0),
                        'active_connections': performance_result.get('active_connections', 0),
                    }
                }
            else:
                return {
                    'success': False,
                    'message': performance_result.get('message', _("Error en test de rendimiento.")),
                    'details': performance_result.get('details', {})
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': _("Error en test de rendimiento."),
                'error': str(e)
            }

    def _test_full_connection(self, connection_service):
        """Test completo de conexión"""
        try:
            results = {
                'basic': self._test_basic_connection(connection_service),
                'tables': self._test_tables_connection(connection_service),
                'queries': self._test_queries_connection(connection_service),
                'performance': self._test_performance_connection(connection_service)
            }
            
            # Calcular resultado general
            successful_tests = sum(1 for result in results.values() if result['success'])
            total_tests = len(results)
            
            if successful_tests == total_tests:
                return {
                    'success': True,
                    'message': _("Test completo exitoso. Todas las verificaciones pasaron."),
                    'details': {
                        'tests_passed': successful_tests,
                        'total_tests': total_tests,
                        'results': results
                    }
                }
            else:
                return {
                    'success': False,
                    'message': _("Test completo falló. {passed}/{total} tests exitosos.").format(
                        passed=successful_tests, total=total_tests),
                    'details': {
                        'tests_passed': successful_tests,
                        'total_tests': total_tests,
                        'results': results
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': _("Error en test completo."),
                'error': str(e)
            }

    def _get_recent_tests(self):
        """Obtener historial de tests recientes"""
        # En una implementación real, esto vendría de un modelo de logs
        # Por ahora retornamos datos de ejemplo
        return [
            {
                'timestamp': '2024-01-15 14:30:00',
                'test_type': 'basic',
                'success': True,
                'duration': 0.5,
                'user': 'admin'
            },
            {
                'timestamp': '2024-01-15 14:25:00',
                'test_type': 'full',
                'success': True,
                'duration': 2.3,
                'user': 'admin'
            },
            {
                'timestamp': '2024-01-15 14:20:00',
                'test_type': 'tables',
                'success': False,
                'duration': 1.1,
                'user': 'admin'
            }
        ]


class ConnectionDiagnosticView(CorePermissionRequiredMixin, TemplateView):
    """Vista para diagnóstico completo de conexión"""
    permission_required = "core.can_manage_integrations"
    
    def post(self, request, *args, **kwargs):
        """Ejecutar diagnóstico completo"""
        if not request.user.has_perm('core.can_manage_integrations'):
            return JsonResponse({
                'success': False,
                'message': _("No tienes permisos para esta acción.")
            })
        
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'message': _("No hay configuración activa.")
                })
            
            connection_service = AdministraNETConnectionService(config)
            
            # Ejecutar diagnóstico completo
            diagnostic_result = connection_service.run_diagnostic()
            
            return JsonResponse(diagnostic_result)
            
        except Exception as e:
            logger.error(f"Error en diagnóstico: {e}")
            return JsonResponse({
                'success': False,
                'message': _("Error durante el diagnóstico."),
                'error': str(e)
            }) 