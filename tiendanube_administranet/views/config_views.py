"""
Vistas config views — tiendanube_administranet.
"""

import logging
import requests
import uuid
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, RedirectView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext as _, gettext_lazy as _
from django.core.paginator import Paginator

from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping,
    SyncLog, ProductMapping, ProductVariantMapping, ProductCategoryMapping,
    OrderMapping, WebhookConfig, WebhookEvent, WebhookDeliveryLog
)
from ..services.sync_service import TiendanubeAdministraNETSyncService
from ..forms import (
    TiendanubeConfigForm, AdministraNETConfigForm,
    CustomerMappingForm, CustomerMappingFilterForm,
    ProductMappingForm, ProductVariantMappingForm, ProductCategoryMappingForm,
    OrderMappingForm, WebhookConfigForm, WebhookEventFilterForm
)
from ..mixins import TiendanubeAdministranetLoginMixin
from ..mysql import resolve_mysql_base_empresa
from ..services.tiendanube_service import NUVEMSHOP_API_VERSION
from ..services.tiendanube_oauth import (
    build_tiendanube_authorize_url,
    clear_oauth_session,
    exchange_oauth_code,
)

DEFAULT_TIENDANUBE_API_URL = f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}'
OAUTH_FLOW_RENEW = 'renew'
OAUTH_FLOW_WIZARD = 'wizard'


def build_tiendanube_oauth_redirect_uri(request) -> str:
    """
    URL de callback OAuth para el wizard.
    Si SITE_URL es HTTPS (p. ej. túnel ngrok), se usa en lugar del host de la petición.
    """
    path = reverse('tiendanube_administranet:tiendanube_config_wizard_callback')
    site = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    if site.startswith('https://'):
        return f'{site}{path}'
    uri = request.build_absolute_uri(path)
    return uri.replace('http://', 'https://')

logger = logging.getLogger(__name__)

class TiendanubeConfigListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar configuraciones de Tiendanube.
    """
    model = TiendanubeConfig
    template_name = 'tiendanube_administranet/tiendanube_config_list.html'
    context_object_name = 'configs'
    permission_required = 'tiendanube_administranet.view_tiendanubeconfig'
    paginate_by = 20

    def get_queryset(self):
        return TiendanubeConfig.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar estadísticas de estado de configuración
        config_statuses = {}
        for config in context['configs']:
            # Aquí podrías agregar lógica para verificar el estado de cada configuración
            config_statuses[config.pk] = {
                'active': config.is_active,
                'message': 'Configuration is active' if config.is_active else 'Configuration is inactive'
            }
        context['config_statuses'] = config_statuses
        return context


class TiendanubeConfigCreateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear nueva configuración de Tiendanube.
    """
    model = TiendanubeConfig
    form_class = TiendanubeConfigForm
    template_name = 'tiendanube_administranet/tiendanube_config_form.html'
    permission_required = 'tiendanube_administranet.add_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tiendanube configuration created successfully.'))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _('Error creating Tiendanube configuration. Please check the form.'))
        return super().form_invalid(form)


class TiendanubeConfigUpdateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar configuración de Tiendanube.
    """
    model = TiendanubeConfig
    form_class = TiendanubeConfigForm
    template_name = 'tiendanube_administranet/tiendanube_config_form.html'
    permission_required = 'tiendanube_administranet.change_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['oauth_redirect_uri'] = build_tiendanube_oauth_redirect_uri(self.request)
        context['can_renew_access_token'] = True
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tiendanube configuration updated successfully.'))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _('Error updating Tiendanube configuration. Please check the form.'))
        return super().form_invalid(form)


class TiendanubeConfigRenewTokenStartView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, View):
    """
    Inicia OAuth para renovar el access token de una configuración existente.
    """
    permission_required = 'tiendanube_administranet.change_tiendanubeconfig'
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        config = get_object_or_404(TiendanubeConfig, pk=pk)
        app_id = (request.POST.get('app_id') or '').strip()
        client_secret = (request.POST.get('client_secret') or '').strip()

        if not app_id or not client_secret:
            messages.error(request, _('Ingrese App ID y Client Secret de la app en Partners Tienda Nube.'))
            return redirect('tiendanube_administranet:tiendanube_config_update', pk=config.pk)

        state = str(uuid.uuid4())
        request.session['tiendanube_oauth_flow'] = OAUTH_FLOW_RENEW
        request.session['tiendanube_oauth_config_pk'] = config.pk
        request.session['wizard_app_id'] = app_id
        request.session['wizard_client_secret'] = client_secret
        request.session['wizard_state'] = state
        request.session.pop('wizard_code', None)

        redirect_uri = build_tiendanube_oauth_redirect_uri(request)
        auth_url = build_tiendanube_authorize_url(app_id, redirect_uri, state)
        logger.info('Renovación OAuth TN config=%s → autorización externa', config.pk)
        return HttpResponseRedirect(auth_url)


class TiendanubeConfigDeleteView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar configuración de Tiendanube.
    """
    model = TiendanubeConfig
    template_name = 'tiendanube_administranet/tiendanube_config_confirm_delete.html'
    permission_required = 'tiendanube_administranet.delete_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Tiendanube configuration deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class TiendanubeConfigWizardCallbackView(TiendanubeAdministranetLoginMixin, View):
    """
    Callback OAuth compartido: wizard de alta y renovación desde edición de config.
    """

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return redirect('login:login')
        if 'user' not in request.session:
            return redirect('login:login')
        can_add = user.has_perm('tiendanube_administranet.add_tiendanubeconfig')
        can_change = user.has_perm('tiendanube_administranet.change_tiendanubeconfig')
        if not (can_add or can_change):
            messages.error(request, _('No tiene permiso para configurar Tienda Nube.'))
            return redirect('tiendanube_administranet:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        session = request.session
        code = request.GET.get('code')
        state = request.GET.get('state')
        oauth_flow = session.get('tiendanube_oauth_flow', OAUTH_FLOW_WIZARD)

        logger.info(
            'Tiendanube OAuth callback - flow=%s code=%s state=%s',
            oauth_flow,
            f'{code[:10]}...' if code else 'None',
            state,
        )

        if not code or not state:
            return self._handle_callback_error(
                request,
                oauth_flow,
                _('Autorización fallida. Intente nuevamente.'),
            )

        expected_state = session.get('wizard_state')
        if not expected_state or state != expected_state:
            clear_oauth_session(session)
            return self._handle_callback_error(
                request,
                oauth_flow,
                _('Estado OAuth inválido. Repita la autorización desde el inicio.'),
            )

        if oauth_flow == OAUTH_FLOW_RENEW:
            return self._complete_renew_flow(request, code)

        session['wizard_code'] = code
        session['wizard_step'] = 4
        session['wizard_message'] = 'Authorization code received successfully!'
        session['wizard_message_type'] = 'success'
        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4")

    def _handle_callback_error(self, request, oauth_flow, message):
        if oauth_flow == OAUTH_FLOW_RENEW:
            pk = request.session.get('tiendanube_oauth_config_pk')
            clear_oauth_session(request.session)
            messages.error(request, message)
            if pk:
                return redirect('tiendanube_administranet:tiendanube_config_update', pk=pk)
            return redirect('tiendanube_administranet:tiendanube_config_list')
        request.session['wizard_message'] = str(message)
        request.session['wizard_message_type'] = 'error'
        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4")

    def _complete_renew_flow(self, request, code):
        session = request.session
        pk = session.get('tiendanube_oauth_config_pk')
        config = get_object_or_404(TiendanubeConfig, pk=pk)
        redirect_uri = build_tiendanube_oauth_redirect_uri(request)

        result = exchange_oauth_code(
            app_id=session.get('wizard_app_id'),
            client_secret=session.get('wizard_client_secret'),
            code=code,
            redirect_uri=redirect_uri,
        )
        clear_oauth_session(session)

        if not result.get('success'):
            messages.error(request, result.get('message', _('No se pudo renovar el access token.')))
            return redirect('tiendanube_administranet:tiendanube_config_update', pk=config.pk)

        new_token = result['access_token']
        new_store_id = str(result.get('store_id') or '')
        config.access_token = new_token
        if new_store_id and new_store_id != str(config.store_id):
            messages.warning(
                request,
                _('Token renovado. Tienda Nube devolvió store_id %(new)s; en Synap está %(current)s. '
                  'Se actualizó solo el token; revise el Store ID si corresponde.')
                % {'new': new_store_id, 'current': config.store_id},
            )
        else:
            messages.success(request, _('Access token renovado y guardado correctamente.'))
        config.save()
        return redirect('tiendanube_administranet:tiendanube_config_update', pk=config.pk)


class TiendanubeConfigWizardView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para el wizard de configuración de Tiendanube.
    """
    template_name = 'tiendanube_administranet/tiendanube_config_wizard.html'
    permission_required = 'tiendanube_administranet.add_tiendanubeconfig'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el paso actual del wizard
        step = int(self.request.GET.get('step', 1))
        context['step'] = step
        
        logger.info(f"Wizard step: {step}, Session data: {dict(self.request.session)}")
        
        # Manejar mensajes desde la sesión
        wizard_message = self.request.session.pop('wizard_message', None)
        wizard_message_type = self.request.session.pop('wizard_message_type', None)
        
        if wizard_message:
            context['wizard_message'] = wizard_message
            context['wizard_message_type'] = wizard_message_type
        
        # Definir los pasos del wizard
        context['wizard_steps'] = [
            _('Credentials'),
            _('Validation'),
            _('Authorization'),
            _('Token'),
            _('Preferences'),
            _('Summary')
        ]
        
        # Configurar datos según el paso
        if step == 1:
            # Paso 1: Credenciales
            context['app_id'] = self.request.session.get('wizard_app_id', '')
            context['client_secret'] = self.request.session.get('wizard_client_secret', '')
            context['redirect_uri'] = build_tiendanube_oauth_redirect_uri(self.request)
            
        elif step == 3:
            # Paso 3: Autorización
            app_id = self.request.session.get('wizard_app_id')
            client_secret = self.request.session.get('wizard_client_secret')
            if app_id and client_secret:
                # Generar URL de autorización
                state = self.request.session.get('wizard_state', '')
                redirect_uri = build_tiendanube_oauth_redirect_uri(self.request)
                context['auth_url'] = f"https://www.tiendanube.com/apps/{app_id}/authorize?response_type=code&client_id={app_id}&redirect_uri={redirect_uri}&state={state}"
                context['redirect_uri'] = redirect_uri
                context['state'] = state
                
                logger.info(f"Step 3 - App ID: {app_id}, State: {state}")
                logger.info(f"Step 3 - Auth URL: {context['auth_url']}")
                logger.info(f"Step 3 - Redirect URI: {context['redirect_uri']}")
                
        elif step == 4:
            # Paso 4: Token
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            wizard_code = self.request.session.get('wizard_code')
            
            # Agregar código de autorización al contexto
            context['wizard_code'] = wizard_code
            
            # Solo mostrar datos si realmente tenemos un token válido
            if access_token and user_id and not access_token.startswith('sample_'):
                context['access_token'] = access_token
                context['user_id'] = user_id
                context['token_obtained'] = True
            else:
                context['access_token'] = None
                context['user_id'] = None
                context['token_obtained'] = False
            
        elif step == 5:
            # Paso 5: Preferencias
            context['auto_sync'] = self.request.session.get('wizard_auto_sync', True)
            context['sync_interval'] = self.request.session.get('wizard_sync_interval', 30)
            context['sync_products'] = self.request.session.get('wizard_sync_products', True)
            context['sync_stock'] = self.request.session.get('wizard_sync_stock', True)
            
            # Verificar que tenemos los datos necesarios para continuar
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            if not access_token or not user_id:
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
            
        elif step == 6:
            # Paso 6: Resumen
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            
            # Verificar que tenemos los datos necesarios
            if not access_token or not user_id:
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
            else:
                # Verificar si ya existe la tienda en Synap
                if TiendanubeConfig.objects.filter(store_id=user_id).exists():
                    context['wizard_error'] = 'This store is already registered in Synap.'
                else:
                    context['summary'] = {
                        'app_id': self.request.session.get('wizard_app_id'),
                        'user_id': user_id,
                        'access_token': access_token[:20] + '...' + access_token[-10:] if access_token else 'N/A',
                        'scopes': self.request.session.get('wizard_scopes', []),
                        'auto_sync': self.request.session.get('wizard_auto_sync', True),
                        'sync_interval': self.request.session.get('wizard_sync_interval', 30),
                        'sync_products': self.request.session.get('wizard_sync_products', True),
                        'sync_stock': self.request.session.get('wizard_sync_stock', True),
                    }
                    # Obtener datos de la tienda si están disponibles
            context['tienda_data'] = self.request.session.get('wizard_tienda_data')
            
        return context

    def post(self, request, *args, **kwargs):
        step = int(request.GET.get('step', 1))
        
        if step == 1:
            # Procesar credenciales
            app_id = request.POST.get('app_id')
            client_secret = request.POST.get('client_secret')
            
            if app_id and client_secret:
                request.session['wizard_app_id'] = app_id
                request.session['wizard_client_secret'] = client_secret
                request.session['wizard_state'] = str(uuid.uuid4())
                request.session['tiendanube_oauth_flow'] = OAUTH_FLOW_WIZARD
                request.session.pop('tiendanube_oauth_config_pk', None)
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=3")
            else:
                messages.error(request, _('Please provide both App ID and Client Secret.'))
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=1")
                
        elif step == 4:
            # Obtener token de acceso
            if 'get_token' in request.POST:
                redirect_uri = build_tiendanube_oauth_redirect_uri(request)
                result = exchange_oauth_code(
                    app_id=request.session.get('wizard_app_id'),
                    client_secret=request.session.get('wizard_client_secret'),
                    code=request.session.get('wizard_code'),
                    redirect_uri=redirect_uri,
                )
                if result.get('success'):
                    request.session['wizard_access_token'] = result['access_token']
                    request.session['wizard_user_id'] = result.get('store_id')
                    request.session['wizard_message'] = str(result.get('message', 'Access token obtained successfully!'))
                    request.session['wizard_message_type'] = 'success'
                else:
                    request.session['wizard_message'] = str(result.get('message', 'Error obtaining token'))
                    request.session['wizard_message_type'] = 'error'
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4")
            elif 'continue_prefs' in request.POST:
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=5")
                
        elif step == 5:
            # Procesar preferencias
            request.session['wizard_auto_sync'] = 'auto_sync' in request.POST
            request.session['wizard_sync_interval'] = int(request.POST.get('sync_interval', 30))
            request.session['wizard_sync_products'] = 'sync_products' in request.POST
            request.session['wizard_sync_stock'] = 'sync_stock' in request.POST
            return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
            
        elif step == 6:
            # Guardar configuración
            if 'save_store' in request.POST:
                try:
                    # Verificar que tenemos los datos necesarios
                    store_id = request.session.get('wizard_user_id')
                    access_token = request.session.get('wizard_access_token')
                    
                    if not store_id or not access_token:
                        request.session['wizard_message'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
                        request.session['wizard_message_type'] = 'error'
                        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
                    
                    # Verificar si ya existe la tienda en Synap
                    if TiendanubeConfig.objects.filter(store_id=store_id).exists():
                        request.session['wizard_message'] = 'This store is already registered in Synap.'
                        request.session['wizard_message_type'] = 'error'
                        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
                    
                    # Obtener datos de la tienda desde Tiendanube para el nombre
                    tienda_name = f"Store {store_id}"
                    try:
                        headers = {
                            'Content-Type': 'application/json',
                            'Authentication': f'bearer {access_token}',
                            'User-Agent': 'Synap-Tiendanube-Integration/1.0'
                        }
                        response = requests.get(
                            f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}/{store_id}/store',
                            headers=headers,
                            timeout=10
                        )
                        if response.status_code == 200:
                            tienda_data = response.json()
                            tienda_name = tienda_data.get('name', f"Store {store_id}")
                            logger.info(f"Tiendanube store data retrieved: {tienda_name}")
                    except Exception as e:
                        logger.warning(f"Could not retrieve store data from Tiendanube: {e}")
                    
                    # Crear la configuración de Tiendanube
                    config = TiendanubeConfig.objects.create(
                        name=tienda_name,
                        store_id=store_id,
                        access_token=access_token,
                        api_url=DEFAULT_TIENDANUBE_API_URL,
                        is_active=request.session.get('wizard_auto_sync', True),
                    )
                    
                    logger.info(f"Tiendanube configuration created successfully: {config.name} (ID: {config.id})")
                    
                    # Limpiar datos de sesión
                    session_keys_to_clean = [
                        'wizard_app_id', 'wizard_client_secret', 'wizard_state', 
                        'wizard_access_token', 'wizard_user_id', 'wizard_auto_sync',
                        'wizard_sync_interval', 'wizard_sync_products', 'wizard_sync_stock',
                        'wizard_scopes', 'wizard_tienda_data',
                        'wizard_message', 'wizard_message_type'
                    ]
                    
                    for key in session_keys_to_clean:
                        request.session.pop(key, None)
                    
                    messages.success(request, _('Tiendanube store configuration completed successfully!'))
                    logger.info(f"Wizard completed successfully for store: {store_id}")
                    return redirect('tiendanube_administranet:tiendanube_config_list')
                    
                except Exception as e:
                    error_msg = f'Error saving configuration: {str(e)}'
                    logger.error(f"Wizard error: {error_msg}")
                    request.session['wizard_message'] = error_msg
                    request.session['wizard_message_type'] = 'error'
                    return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
        
        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step={step}")
