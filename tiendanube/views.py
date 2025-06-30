from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from .models import TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping
from core.decorators import tiene_permiso
import logging
from .services import TiendaNubeService
from django.http import HttpResponseRedirect
import requests

class TiendaNubePermissionMixin(UserPassesTestMixin):
    """Mixin to check TiendaNube access permissions."""
    
    def test_func(self):
        return self.request.user.tiene_permiso("tiendanube.access")

# Create your views here.

class TiendaNubeDashboardView(TiendaNubePermissionMixin, TemplateView):
    """Main dashboard for TiendaNube integration."""
    template_name = 'tiendanube/tiendanube_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = TiendaNubeConfig.objects.first()
        if config:
            context['env_configured'] = True
            context['store_id'] = config.store_id
            context['api_url'] = getattr(config, 'api_url', 'https://api.tiendanube.com/v1')
            context['auto_sync'] = getattr(config, 'auto_sync', False)
            context['sync_interval'] = getattr(config, 'sync_interval', 30)
            context['tiendanube_config'] = config
            logging.info(f"[TiendaNubeDashboard] Usando configuración de BD: store_id={config.store_id}, api_url={getattr(config, 'api_url', 'https://api.tiendanube.com/v1')}, auto_sync={getattr(config, 'auto_sync', False)}, sync_interval={getattr(config, 'sync_interval', 30)}")
        else:
            context['env_configured'] = bool(
                getattr(settings, 'TIENDANUBE_STORE_ID', None) and 
                getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', None)
            )
            context['store_id'] = getattr(settings, 'TIENDANUBE_STORE_ID', 'No configurado')
            context['api_url'] = getattr(settings, 'TIENDANUBE_API_URL', 'https://api.tiendanube.com/v1')
            context['auto_sync'] = getattr(settings, 'TIENDANUBE_AUTO_SYNC', False)
            context['sync_interval'] = getattr(settings, 'TIENDANUBE_SYNC_INTERVAL', 30)
            context['tiendanube_config'] = None
            logging.info(f"[TiendaNubeDashboard] Usando configuración de entorno: store_id={context['store_id']}, api_url={context['api_url']}, auto_sync={context['auto_sync']}, sync_interval={context['sync_interval']}")
        return context

class TiendaNubeConfigListView(TiendaNubePermissionMixin, ListView):
    """List all TiendaNube configurations."""
    model = TiendaNubeConfig
    template_name = 'tiendanube/tiendanube_config_list.html'
    context_object_name = 'configs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configs = context['configs']
        config_statuses = {}
        for config in configs:
            service = TiendaNubeService(config)
            ok, msg = service.test_connection()
            config_statuses[config.pk] = {
                'active': ok,
                'message': msg
            }
        context['config_statuses'] = config_statuses
        return context

class TiendaNubeConfigCreateView(TiendaNubePermissionMixin, CreateView):
    """Create a new TiendaNube configuration."""
    model = TiendaNubeConfig
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_config_form.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeConfigUpdateView(TiendaNubePermissionMixin, UpdateView):
    """Edit an existing TiendaNube configuration."""
    model = TiendaNubeConfig
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_config_form.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeConfigDeleteView(TiendaNubePermissionMixin, DeleteView):
    """Delete a TiendaNube configuration."""
    model = TiendaNubeConfig
    template_name = 'tiendanube/tiendanube_config_confirm_delete.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeSyncLogListView(TiendaNubePermissionMixin, ListView):
    """List all TiendaNube sync logs."""
    model = TiendaNubeSyncLog
    template_name = 'tiendanube/tiendanube_logs_list.html'
    context_object_name = 'logs'

class TiendaNubeSyncLogDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of a sync log."""
    model = TiendaNubeSyncLog
    template_name = 'tiendanube/tiendanube_log_detail.html'
    context_object_name = 'log'

class TiendaNubeProductMappingListView(TiendaNubePermissionMixin, ListView):
    """List all product mappings with TiendaNube."""
    model = TiendaNubeProductMapping
    template_name = 'tiendanube/tiendanube_product_mapping_list.html'
    context_object_name = 'mappings'

class TiendaNubeProductMappingDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of a product mapping."""
    model = TiendaNubeProductMapping
    template_name = 'tiendanube/tiendanube_product_mapping_detail.html'
    context_object_name = 'mapping'

class TiendaNubeConfigWizardView(TiendaNubePermissionMixin, TemplateView):
    template_name = 'tiendanube/tiendanube_config_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.request.session
        context['app_id'] = session.get('wizard_app_id', '')
        context['client_secret'] = session.get('wizard_client_secret', '')
        context['step'] = session.get('wizard_step', 1)
        context['scopes'] = session.get('wizard_scopes', ['read_products', 'write_products'])
        context['redirect_uri'] = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
        context['redirect_uri'] = context['redirect_uri'].replace('http://', 'https://')
        if context['step'] == 4:
            context['code'] = session.get('wizard_code')
            context['state'] = session.get('wizard_state')
            context['access_token'] = session.get('wizard_access_token', '')
            context['user_id'] = session.get('wizard_user_id', '')
        if context['step'] == 5:
            context['auto_sync'] = session.get('wizard_auto_sync', True)
            context['sync_interval'] = session.get('wizard_sync_interval', 30)
            context['sync_products'] = session.get('wizard_sync_products', True)
            context['sync_stock'] = session.get('wizard_sync_stock', True)
            context['sync_variants'] = session.get('wizard_sync_variants', True)
        if context['step'] == 6:
            # Resumen final con datos de la tienda desde TiendaNube
            access_token = session.get('wizard_access_token')
            user_id = session.get('wizard_user_id')
            tienda_data = session.get('wizard_tienda_data')
            if not tienda_data and access_token and user_id:
                # Consultar la API de TiendaNube
                try:
                    resp = requests.get(f'https://api.tiendanube.com/v1/{user_id}/store',
                        headers={
                            'Content-Type': 'application/json',
                            'Authentication': f'bearer {access_token}',
                            'User-Agent': 'Synap (https://synap.com.ar)'
                        })
                    if resp.status_code == 200:
                        tienda_data = resp.json()
                        session['wizard_tienda_data'] = tienda_data
                    else:
                        tienda_data = None
                except Exception:
                    tienda_data = None
            context['tienda_data'] = tienda_data
            context['summary'] = {
                'app_id': session.get('wizard_app_id'),
                'user_id': user_id,
                'access_token': access_token,
                'scopes': session.get('wizard_scopes'),
                'auto_sync': session.get('wizard_auto_sync'),
                'sync_interval': session.get('wizard_sync_interval'),
                'sync_products': session.get('wizard_sync_products'),
                'sync_stock': session.get('wizard_sync_stock'),
                'sync_variants': session.get('wizard_sync_variants'),
            }
        if context['step'] == 3:
            app_id = context['app_id']
            scopes = context['scopes']
            redirect_uri = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
            redirect_uri = redirect_uri.replace('http://', 'https://')
            scope_str = ','.join(scopes)
            state = 'synap-' + self.request.session.session_key
            auth_url = f"https://www.tiendanube.com/apps/{app_id}/authorize?response_type=code&client_id={app_id}&scope={scope_str}&redirect_uri={redirect_uri}&state={state}"
            context['auth_url'] = auth_url
            context['state'] = state
        context['wizard_steps'] = [
            'Credentials',
            'Authorize',
            'Token',
            'Preferences',
            'Summary'
        ]
        return context

    def post(self, request, *args, **kwargs):
        session = request.session
        step = int(session.get('wizard_step', 1))
        if step == 1:
            app_id = request.POST.get('app_id', '').strip()
            client_secret = request.POST.get('client_secret', '').strip()
            session['wizard_app_id'] = app_id
            session['wizard_client_secret'] = client_secret
            session['wizard_step'] = 3
            return self.get(request, *args, **kwargs)
        elif step == 4 and 'get_token' in request.POST:
            # Obtener access_token desde TiendaNube
            app_id = session.get('wizard_app_id')
            client_secret = session.get('wizard_client_secret')
            code = session.get('wizard_code')
            redirect_uri = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
            redirect_uri = redirect_uri.replace('http://', 'https://')
            data = {
                'client_id': app_id,
                'client_secret': client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri
            }
            # Logging para depuración
            logging.info(f"[TiendaNube Wizard] POST /apps/authorize/token data: {data}")
            resp = requests.post('https://www.tiendanube.com/apps/authorize/token', json=data, headers={'Content-Type': 'application/json'})
            logging.info(f"[TiendaNube Wizard] Response status: {resp.status_code}")
            logging.info(f"[TiendaNube Wizard] Response text: {resp.text}")
            if resp.status_code == 200:
                token_data = resp.json()
                session['wizard_access_token'] = token_data.get('access_token')
                session['wizard_user_id'] = token_data.get('user_id')
                session['wizard_step'] = 5
            else:
                session['wizard_access_token'] = ''
                session['wizard_user_id'] = ''
            return self.get(request, *args, **kwargs)
        elif step == 4 and 'continue_prefs' in request.POST:
            session['wizard_step'] = 5
            return self.get(request, *args, **kwargs)
        elif step == 5:
            session['wizard_auto_sync'] = bool(request.POST.get('auto_sync'))
            session['wizard_sync_interval'] = int(request.POST.get('sync_interval', 30))
            session['wizard_sync_products'] = bool(request.POST.get('sync_products'))
            session['wizard_sync_stock'] = bool(request.POST.get('sync_stock'))
            session['wizard_sync_variants'] = bool(request.POST.get('sync_variants'))
            session['wizard_step'] = 6
            return self.get(request, *args, **kwargs)
        elif step == 6 and 'save_store' in request.POST:
            from .models import TiendaNubeConfig
            # Verificar si ya existe la tienda en Synap
            store_id = session.get('wizard_user_id')
            access_token = session.get('wizard_access_token')
            if not store_id or not access_token:
                context = self.get_context_data()
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
                return self.render_to_response(context)
            if TiendaNubeConfig.objects.filter(store_id=store_id).exists():
                # Ya existe, mostrar error amigable
                context = self.get_context_data()
                context['wizard_error'] = 'This store is already registered in Synap.'
                return self.render_to_response(context)
            # Crear la nueva configuración de tienda
            TiendaNubeConfig.objects.create(
                store_id=store_id,
                access_token=access_token,
                api_url='https://api.tiendanube.com/v1',
                auto_sync=session.get('wizard_auto_sync', True),
                sync_interval=session.get('wizard_sync_interval', 30),
                sync_products=session.get('wizard_sync_products', True),
                sync_stock=session.get('wizard_sync_stock', True),
                sync_variants=session.get('wizard_sync_variants', True),
            )
            # Limpiar la sesión del wizard
            for k in list(session.keys()):
                if k.startswith('wizard_'):
                    del session[k]
            from django.urls import reverse
            return HttpResponseRedirect(reverse('tiendanube:config_list'))
        else:
            session['wizard_step'] = 1
            return self.get(request, *args, **kwargs)

class TiendaNubeConfigWizardCallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code')
        state = request.GET.get('state')
        # Guardar el code en sesión y avanzar al siguiente paso
        request.session['wizard_code'] = code
        request.session['wizard_state'] = state
        request.session['wizard_step'] = 4
        return HttpResponseRedirect('/tiendanube/config/wizard/')
