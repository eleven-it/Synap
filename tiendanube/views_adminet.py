from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from tiendanube.models_adminet import TiendaNubeCondVentaMap, TiendaNubeAdminetConfig
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from tiendanube.services.order_to_adminet_service import OrderToAdminetService
from tiendanube.services.connection_service import MySQLConnectionService
from tiendanube.models_adminet import TiendaNubeAdminetConfig
import json
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib import messages
import logging
from tiendanube.models_synap import TiendaNubeConfig
from tiendanube.services_main import TiendaNubeService

logger = logging.getLogger(__name__)

class CondVentaMapListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'tiendanube_adminet/cond_venta_map_list.html'
    permission_required = 'tiendanube.view_tiendanubecondventamap'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración de administraNET
        adminet_config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
        if not adminet_config:
            messages.warning(self.request, "No hay configuración activa de administraNET")
            context['condiciones_venta'] = []
            context['connection_error'] = "No hay configuración activa de administraNET"
            return context

        try:
            # Conectar a administraNET y obtener condiciones de venta
            mysql_config = {
                'host': adminet_config.host,
                'port': adminet_config.port,
                'database': adminet_config.database,
                'user': adminet_config.user,
                'password': adminet_config.password,
            }
            
            mysql_service = MySQLConnectionService(mysql_config)
            
            # Obtener todas las condiciones de venta de administraNET
            query = """
                SELECT codigo, descripcion 
                FROM cond_venta 
                WHERE anulado = 'No' 
                ORDER BY codigo
            """
            
            result = mysql_service.execute_query(query)
            
            if not result.get('success'):
                context['connection_error'] = result.get('error', 'Error desconocido')
                context['condiciones_venta'] = []
                return context
            
            condiciones_venta = result.get('results', [])
            
            # Obtener mapeos existentes
            mapeos_existentes = {
                mapping.adminet_codigo: mapping 
                for mapping in TiendaNubeCondVentaMap.objects.all()
            }
            
            # Crear lista con información completa
            condiciones_completas = []
            for cond in condiciones_venta:
                codigo = cond['codigo']
                mapeo = mapeos_existentes.get(codigo)
                
                condiciones_completas.append({
                    'codigo': codigo,
                    'descripcion': cond['descripcion'],
                    'mapeado': mapeo is not None,
                    'payment_method': mapeo.payment_method if mapeo else '',
                    'activo': mapeo.activo if mapeo else False,
                    'mapeo_id': mapeo.id if mapeo else None,
                })
            
            context['condiciones_venta'] = condiciones_completas
            context['connection_success'] = True
            
        except Exception as e:
            logger.error(f"Error obteniendo condiciones de venta: {str(e)}")
            context['connection_error'] = f"Error de conexión: {str(e)}"
            context['condiciones_venta'] = []
        
        return context

class CondVentaMapCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = TiendaNubeCondVentaMap
    fields = ['payment_method', 'adminet_codigo', 'adminet_descripcion', 'activo']
    template_name = 'tiendanube_adminet/cond_venta_map_form.html'
    permission_required = 'tiendanube.add_tiendanubecondventamap'
    success_url = reverse_lazy('tiendanube:cond_venta_map_list')

class CondVentaMapUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = TiendaNubeCondVentaMap
    fields = ['payment_method', 'adminet_codigo', 'adminet_descripcion', 'activo']
    template_name = 'tiendanube_adminet/cond_venta_map_form.html'
    permission_required = 'tiendanube.change_tiendanubecondventamap'
    success_url = reverse_lazy('tiendanube:cond_venta_map_list')

class CondVentaMapDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = TiendaNubeCondVentaMap
    template_name = 'tiendanube_adminet/cond_venta_map_confirm_delete.html'
    permission_required = 'tiendanube.delete_tiendanubecondventamap'
    success_url = reverse_lazy('tiendanube:cond_venta_map_list')

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def toggle_cond_venta_mapping(request):
    """Toggle o crear mapeo de condición de venta"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo')
        payment_method = data.get('payment_method')
        method_id = data.get('method_id', '')  # Nuevo campo
        activo = data.get('activo', False)
        
        if not codigo or not payment_method:
            return JsonResponse({'success': False, 'error': 'Código y método de pago son requeridos'})
        
        # Buscar mapeo existente o crear uno nuevo
        mapeo, created = TiendaNubeCondVentaMap.objects.get_or_create(
            adminet_codigo=codigo,
            defaults={
                'payment_method': payment_method,
                'activo': activo
            }
        )
        
        if not created:
            # Actualizar mapeo existente
            mapeo.payment_method = payment_method
            mapeo.activo = activo
            mapeo.save()
        
        # Obtener descripción de administraNET
        adminet_config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
        if adminet_config:
            try:
                mysql_config = {
                    'host': adminet_config.host,
                    'port': adminet_config.port,
                    'database': adminet_config.database,
                    'user': adminet_config.user,
                    'password': adminet_config.password,
                }
                
                mysql_service = MySQLConnectionService(mysql_config)
                query = "SELECT descripcion FROM cond_venta WHERE codigo = %s AND anulado = 'No'"
                result = mysql_service.execute_query(query, (codigo,))
                
                if result.get('success') and result.get('results'):
                    mapeo.adminet_descripcion = result['results'][0]['descripcion']
                    mapeo.save()
            except Exception as e:
                logger.error(f"Error obteniendo descripción de administraNET: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Mapeo actualizado correctamente',
            'mapeo_id': mapeo.id,
            'created': created
        })
        
    except Exception as e:
        logger.error(f"Error en toggle_cond_venta_mapping: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def delete_cond_venta_mapping(request):
    """Eliminar mapeo de condición de venta"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        mapeo_id = data.get('mapeo_id')
        
        if not mapeo_id:
            return JsonResponse({'error': 'ID de mapeo es requerido'}, status=400)
        
        mapeo = TiendaNubeCondVentaMap.objects.get(id=mapeo_id)
        mapeo.delete()
        
        return JsonResponse({'success': True})
        
    except TiendaNubeCondVentaMap.DoesNotExist:
        return JsonResponse({'error': 'Mapeo no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error eliminando mapeo: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

# Aquí se agregará la lógica de sincronización con Celery y la vista para dispararla 

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def test_order_to_adminet(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        from tiendanube.services_main import TiendaNubeService
        from tiendanube.models_adminet import TiendaNubeAdminetConfig
        config_adminet = TiendaNubeAdminetConfig.objects.get(is_active=True)
        tn_service = TiendaNubeService(config_adminet)
        data = json.loads(request.body.decode('utf-8'))
        service = OrderToAdminetService(tn_service=tn_service)
        pedido_id = service.save_order(data)
        return JsonResponse({'success': True, 'pedido_id': pedido_id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500) 

@csrf_exempt
@require_POST
def webhook_order_tiendanube(request):
    try:
        from tiendanube.services_main import TiendaNubeService
        from tiendanube.models_adminet import TiendaNubeAdminetConfig
        config_adminet = TiendaNubeAdminetConfig.objects.get(is_active=True)
        tn_service = TiendaNubeService(config_adminet)
        data = json.loads(request.body.decode('utf-8'))
        service = OrderToAdminetService(tn_service=tn_service)
        pedido_id = service.save_order(data)
        return JsonResponse({'success': True, 'pedido_id': pedido_id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500) 

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def get_tiendanube_payment_methods(request):
    """Obtener métodos de pago de Tiendanube para autocomplete"""
    try:
        # Obtener configuración de Tiendanube
        config = TiendaNubeConfig.objects.first()
        if not config:
            return JsonResponse({
                'success': False,
                'error': 'No hay configuración de Tiendanube',
                'payment_methods': []
            })
        
        # Crear servicio de Tiendanube
        service = TiendaNubeService(config)
        
        # Obtener métodos de pago
        result = service.get_payment_methods()
        
        if result.get('success'):
            payment_methods = result.get('payment_methods', [])
            
            # Filtrar por query si se proporciona
            query = request.GET.get('q', '').lower()
            if query:
                filtered_methods = []
                for method in payment_methods:
                    name = method.get('name', '').lower()
                    method_id = method.get('id', '').lower()
                    if query in name or query in method_id:
                        filtered_methods.append(method)
                payment_methods = filtered_methods
            
            # Limitar resultados
            payment_methods = payment_methods[:20]
            
            return JsonResponse({
                'success': True,
                'payment_methods': payment_methods,
                'count': len(payment_methods)
            })
        else:
            # Si no se pueden obtener de la API, usar métodos simulados
            simulated_methods = [
                {"id": "credit_card", "name": "Tarjeta de Crédito"},
                {"id": "debit_card", "name": "Tarjeta de Débito"},
                {"id": "bank_transfer", "name": "Transferencia Bancaria"},
                {"id": "cash_on_delivery", "name": "Contra Reembolso"},
                {"id": "mercadopago", "name": "MercadoPago"},
                {"id": "paypal", "name": "PayPal"},
                {"id": "stripe", "name": "Stripe"},
                {"id": "check", "name": "Cheque"},
                {"id": "wire_transfer", "name": "Giro Postal"},
                {"id": "crypto", "name": "Criptomonedas"},
            ]
            
            # Filtrar por query si se proporciona
            query = request.GET.get('q', '').lower()
            if query:
                filtered_methods = []
                for method in simulated_methods:
                    name = method.get('name', '').lower()
                    method_id = method.get('id', '').lower()
                    if query in name or query in method_id:
                        filtered_methods.append(method)
                simulated_methods = filtered_methods
            
            return JsonResponse({
                'success': True,
                'payment_methods': simulated_methods,
                'count': len(simulated_methods),
                'note': 'Usando métodos simulados (API no disponible)'
            })
            
    except Exception as e:
        logger.error(f"Error obteniendo métodos de pago: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}',
            'payment_methods': []
        }) 