from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode
import requests
import json
import logging
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from core.decorators import tiene_permiso
from .models_synap import (
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping,
    TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeRestockRule,
    TiendaNubeRestockLog, TiendaNubeProductRestockPolicy
)
from .services_main import TiendaNubeService
from inventory.models import Product, Warehouse
from sales.models import Client

logger = logging.getLogger(__name__)

class TiendaNubePermissionMixin(UserPassesTestMixin):
    """Mixin to check TiendaNube access permissions."""
    
    def test_func(self):
        return self.request.user.tiene_permiso("tiendanube.access")

class TiendaNubeConfigWizardView(TiendaNubePermissionMixin, TemplateView):
    """Enhanced configuration wizard for TiendaNube integration."""
    template_name = 'tiendanube/tiendanube_config_wizard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        step = self.request.GET.get('step', '1')
        context['current_step'] = int(step)
        context['total_steps'] = 4
        
        # Step 1: App Registration
        if step == '1':
            context['app_id'] = self.request.session.get('wizard_app_id', '')
            context['client_secret'] = self.request.session.get('wizard_client_secret', '')
            context['redirect_uri'] = self.request.build_absolute_uri(
                reverse('tiendanube:tiendanube_config_wizard_callback')
            )
            
        # Step 2: Authorization
        elif step == '2':
            app_id = self.request.session.get('wizard_app_id')
            client_secret = self.request.session.get('wizard_client_secret')
            if not app_id or not client_secret:
                messages.error(self.request, _('Please complete step 1 first.'))
                return redirect('tiendanube:tiendanube_config_wizard?step=1')
            
            context['app_id'] = app_id
            context['client_secret'] = client_secret
            context['authorization_url'] = self._build_authorization_url(app_id)
            
        # Step 3: Callback Processing
        elif step == '3':
            code = self.request.session.get('wizard_code')
            if not code:
                messages.error(self.request, _('Authorization code not found. Please complete step 2.'))
                return redirect('tiendanube:tiendanube_config_wizard?step=2')
            
            context['code'] = code
            context['app_id'] = self.request.session.get('wizard_app_id')
            context['client_secret'] = self.request.session.get('wizard_client_secret')
            
        # Step 4: Token Exchange
        elif step == '4':
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            
            # Check if we have valid tokens (not sample data)
            if access_token and user_id and not access_token.startswith('sample_'):
                context['token_obtained'] = True
                context['access_token'] = access_token
                context['user_id'] = user_id
                context['store_id'] = self.request.session.get('wizard_store_id', '')
            else:
                context['token_obtained'] = False
                context['access_token'] = access_token or ''
                context['user_id'] = user_id or ''
                context['store_id'] = self.request.session.get('wizard_store_id', '')
            
            context['app_id'] = self.request.session.get('wizard_app_id')
            context['client_secret'] = self.request.session.get('wizard_client_secret')
            context['code'] = self.request.session.get('wizard_code')
        
        return context
    
    def _build_authorization_url(self, app_id):
        """Build TiendaNube authorization URL."""
        redirect_uri = self.request.build_absolute_uri(
            reverse('tiendanube:tiendanube_config_wizard_callback')
        )
        redirect_uri = redirect_uri.replace('http://', 'https://')
        
        params = {
            'client_id': app_id,
            'redirect_uri': redirect_uri,
            'scope': 'read_products write_products read_orders write_orders read_customers write_customers',
            'response_type': 'code'
        }
        
        return f"https://www.tiendanube.com/apps/authorize/token?{urlencode(params)}"
    
    def post(self, request, *args, **kwargs):
        step = request.GET.get('step', '1')
        
        # Step 1: Save app credentials
        if step == '1':
            app_id = request.POST.get('app_id', '').strip()
            client_secret = request.POST.get('client_secret', '').strip()
            
            if not app_id or not client_secret:
                messages.error(request, _('App ID and Client Secret are required.'))
                return redirect('tiendanube:tiendanube_config_wizard?step=1')
            
            request.session['wizard_app_id'] = app_id
            request.session['wizard_client_secret'] = client_secret
            messages.success(request, _('App credentials saved successfully.'))
            return redirect('tiendanube:tiendanube_config_wizard?step=2')
        
        # Step 2: Generate authorization URL
        elif step == '2':
            if 'authorize' in request.POST:
                app_id = request.session.get('wizard_app_id')
                if not app_id:
                    messages.error(request, _('App ID not found. Please complete step 1.'))
                    return redirect('tiendanube:tiendanube_config_wizard?step=1')
                
                auth_url = self._build_authorization_url(app_id)
                return redirect(auth_url)
        
        # Step 3: Process authorization code
        elif step == '3':
            if 'continue' in request.POST:
                code = request.session.get('wizard_code')
                if not code:
                    messages.error(request, _('Authorization code not found.'))
                    return redirect('tiendanube:tiendanube_config_wizard?step=2')
                
                messages.success(request, _('Authorization code processed successfully.'))
                return redirect('tiendanube:tiendanube_config_wizard?step=4')
        
        # Step 4: Exchange code for access token
        elif step == '4':
            if 'get_token' in request.POST:
                # Clear previous token data
                request.session['wizard_access_token'] = None
                request.session['wizard_user_id'] = None
                logger.info("Cleared wizard_access_token and wizard_user_id from session.")
                
                # Exchange authorization code for access token
                app_id = request.session.get('wizard_app_id')
                client_secret = request.session.get('wizard_client_secret')
                code = request.session.get('wizard_code')
                redirect_uri = request.build_absolute_uri(
                    reverse('tiendanube:tiendanube_config_wizard_callback')
                )
                redirect_uri = redirect_uri.replace('http://', 'https://')
                
                try:
                    token_response = requests.post(
                        'https://www.tiendanube.com/apps/authorize/token',
                        data={
                            'client_id': app_id,
                            'client_secret': client_secret,
                            'grant_type': 'authorization_code',
                            'code': code,
                            'redirect_uri': redirect_uri
                        },
                        timeout=30
                    )
                    
                    if token_response.status_code == 200:
                        token_data = token_response.json()
                        access_token = token_data.get('access_token')
                        user_id = token_data.get('user_id')
                        
                        if access_token and user_id:
                            request.session['wizard_access_token'] = access_token
                            request.session['wizard_user_id'] = user_id
                            
                            # Get store information
                            try:
                                store_response = requests.get(
                                    f'https://api.tiendanube.com/v1/{user_id}/store',
                                    headers={
                                        'Content-Type': 'application/json',
                                        'Authentication': f'bearer {access_token}',
                                        'User-Agent': 'synap_tiendanube - tiendanube@synap.com'
                                    },
                                    timeout=30
                                )
                                
                                if store_response.status_code == 200:
                                    store_data = store_response.json()
                                    request.session['wizard_store_id'] = store_data.get('id', '')
                                    messages.success(request, _('Access token obtained successfully!'))
                                else:
                                    logger.warning(f"Failed to get store info: {store_response.status_code}")
                                    messages.warning(request, _('Token obtained but could not fetch store information.'))
                                    
                            except Exception as e:
                                logger.error(f"Error getting store info: {e}")
                                messages.warning(request, _('Token obtained but could not fetch store information.'))
                        else:
                            messages.error(request, _('Invalid token response from TiendaNube.'))
                    else:
                        error_msg = _('Failed to obtain access token.')
                        try:
                            error_data = token_response.json()
                            if 'error' in error_data:
                                error_msg = f"{error_msg} {error_data['error']}"
                        except:
                            pass
                        messages.error(request, error_msg)
                        logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                        
                except requests.exceptions.RequestException as e:
                    messages.error(request, _('Network error while obtaining access token.'))
                    logger.error(f"Network error in token exchange: {e}")
                except Exception as e:
                    messages.error(request, _('Unexpected error while obtaining access token.'))
                    logger.error(f"Unexpected error in token exchange: {e}")
            
            elif 'save_config' in request.POST:
                # Save configuration to database
                access_token = request.session.get('wizard_access_token')
                user_id = request.session.get('wizard_user_id')
                store_id = request.session.get('wizard_store_id', '')
                
                if not access_token or not user_id:
                    messages.error(request, _('Access token and user ID are required.'))
                    return redirect('tiendanube:tiendanube_config_wizard?step=4')
                
                try:
                    with transaction.atomic():
                        # Check if config already exists
                        existing_config = TiendaNubeConfig.objects.filter(store_id=store_id).first()
                        if existing_config:
                            existing_config.access_token = access_token
                            existing_config.save()
                            messages.success(request, _('TiendaNube configuration updated successfully!'))
                        else:
                            TiendaNubeConfig.objects.create(
                                store_id=store_id or user_id,
                                access_token=access_token,
                                auto_sync=True,
                                sync_interval=30,
                                sync_products=True,
                                sync_stock=True,
                                sync_orders=True,
                                sync_customers=True
                            )
                            messages.success(request, _('TiendaNube configuration created successfully!'))
                    
                    # Clear wizard session data
                    for key in ['wizard_app_id', 'wizard_client_secret', 'wizard_code', 
                               'wizard_access_token', 'wizard_user_id', 'wizard_store_id']:
                        request.session.pop(key, None)
                    
                    return redirect('tiendanube:dashboard')
                    
                except Exception as e:
                    messages.error(request, _('Error saving configuration.'))
                    logger.error(f"Error saving TiendaNube config: {e}")
        
        return redirect('tiendanube:tiendanube_config_wizard?step=' + step)

class TiendaNubeConfigWizardCallbackView(View):
    """Handle OAuth callback from TiendaNube."""
    
    def get(self, request, *args, **kwargs):
        error = request.GET.get('error')
        code = request.GET.get('code')
        
        if error:
            messages.error(request, f'OAuth Error: {error}')
            return redirect('tiendanube:tiendanube_config_wizard?step=2')
        
        if not code:
            messages.error(request, _('Authorization code not received.'))
            return redirect('tiendanube:tiendanube_config_wizard?step=2')
        
        # Store the authorization code
        request.session['wizard_code'] = code
        messages.success(request, _('Authorization successful! You can now proceed to step 3.'))
        
        return redirect('tiendanube:tiendanube_config_wizard?step=3')

class TiendaNubeDashboardView(TiendaNubePermissionMixin, TemplateView):
    """Enhanced dashboard for TiendaNube integration."""
    template_name = 'tiendanube/tiendanube_dashboard.html'

    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        return TiendaNubeService(config)

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
            
            # Get service statistics
            service = self.get_tiendanube_service(config)
            context['sync_status'] = service.get_sync_status()
            context['recent_logs'] = service.get_recent_logs(limit=10)
            
            # Get mapping statistics
            context['product_mappings'] = TiendaNubeProductMapping.objects.count()
            context['customer_mappings'] = TiendaNubeCustomerMapping.objects.count()
            context['order_mappings'] = TiendaNubeOrderMapping.objects.count()
            
            # Get recent activity
            context['recent_syncs'] = TiendaNubeSyncLog.objects.filter(
                started_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-started_at')[:5]
            
            context['pending_syncs'] = TiendaNubeProductMapping.objects.filter(
                sync_status='pending'
            ).count()
            
            context['error_syncs'] = TiendaNubeProductMapping.objects.filter(
                sync_status='error'
            ).count()
            
        else:
            context['env_configured'] = False
            context['store_id'] = 'No configurado'
            context['api_url'] = 'https://api.tiendanube.com/v1'
            context['auto_sync'] = False
            context['sync_interval'] = 30
            context['tiendanube_config'] = None
            
        return context

class TiendaNubeManualSyncView(TiendaNubePermissionMixin, View):
    """Enhanced manual sync view with better UX."""
    template_name = 'tiendanube/tiendanube_manual_sync.html'

    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        return TiendaNubeService(config)

    def get(self, request):
        config = TiendaNubeConfig.objects.first()
        if not config:
            messages.error(request, _('TiendaNube configuration not found.'))
            return redirect('tiendanube:dashboard')
        
        context = {
            'config': config,
            'recent_logs': TiendaNubeSyncLog.objects.order_by('-started_at')[:10],
            'sync_stats': self._get_sync_stats(),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        config = TiendaNubeConfig.objects.first()
        if not config:
            return JsonResponse({'success': False, 'message': _('Configuration not found.')})
        
        sync_type = request.POST.get('sync_type')
        service = self.get_tiendanube_service(config)
        
        try:
            if sync_type == 'products':
                result = service.sync_products()
            elif sync_type == 'customers':
                result = service.sync_customers()
            elif sync_type == 'orders':
                result = service.sync_orders()
            elif sync_type == 'stock':
                result = service.sync_stock()
            elif sync_type == 'full':
                result = service.full_sync()
            else:
                return JsonResponse({'success': False, 'message': _('Invalid sync type.')})
            
            return JsonResponse({
                'success': True,
                'message': _('Sync completed successfully.'),
                'details': result
            })
            
        except Exception as e:
            logger.error(f"Manual sync error: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    def _get_sync_stats(self):
        """Get sync statistics for the dashboard."""
        last_24h = timezone.now() - timedelta(hours=24)
        
        return {
            'total_syncs_24h': TiendaNubeSyncLog.objects.filter(
                started_at__gte=last_24h
            ).count(),
            'successful_syncs_24h': TiendaNubeSyncLog.objects.filter(
                started_at__gte=last_24h,
                status='success'
            ).count(),
            'failed_syncs_24h': TiendaNubeSyncLog.objects.filter(
                started_at__gte=last_24h,
                status='error'
            ).count(),
            'pending_mappings': TiendaNubeProductMapping.objects.filter(
                sync_status='pending'
            ).count(),
        }

# Additional enhanced views can be added here... 