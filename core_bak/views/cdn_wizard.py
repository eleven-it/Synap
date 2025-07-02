from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from core.models import SystemConfiguration
from django.urls import reverse

CDN_PROVIDERS = [
    ('cloudflare', 'Cloudflare'),
    ('aws', 'AWS CloudFront'),
    ('bunny', 'Bunny CDN'),
    ('digitalocean', 'DigitalOcean Spaces'),
]

@method_decorator(user_passes_test(lambda u: u.is_superuser), name='dispatch')
class CDNWizardView(View):
    template_name = 'core/cdn_wizard/wizard.html'
    steps = ['provider', 'domain', 'activate', 'advanced', 'summary']

    def get(self, request):
        step = request.GET.get('step', 'provider')
        context = self.get_context(request, step)
        return render(request, self.template_name, context)

    def post(self, request):
        step = request.POST.get('step', 'provider')
        data = request.session.get('cdn_wizard', {})
        # Guardar datos del paso actual
        if step == 'provider':
            data['provider'] = request.POST.get('provider')
        elif step == 'domain':
            data['domain'] = request.POST.get('domain')
        elif step == 'activate':
            data['enabled'] = request.POST.get('enabled') == 'on'
        elif step == 'advanced':
            data['cache_headers_static'] = request.POST.get('cache_headers_static')
            data['cache_headers_media'] = request.POST.get('cache_headers_media')
            data['cache_headers_images'] = request.POST.get('cache_headers_images')
        request.session['cdn_wizard'] = data
        # Siguiente paso
        next_step = self.next_step(step)
        if next_step == 'summary':
            self.save_config(data)
        return redirect(f"{reverse('core:cdn_wizard')}?step={next_step}")

    def get_context(self, request, step):
        data = request.session.get('cdn_wizard', {})
        idx = self.steps.index(step)
        prev_step = self.steps[idx-1] if idx > 0 else None
        next_step = self.steps[idx+1] if idx+1 < len(self.steps) else None
        context = {
            'step': step,
            'steps': self.steps,
            'data': data,
            'providers': CDN_PROVIDERS,
            'prev_step': prev_step,
            'next_step': next_step,
        }
        return context

    def next_step(self, current):
        idx = self.steps.index(current)
        if idx + 1 < len(self.steps):
            return self.steps[idx + 1]
        return self.steps[-1]

    def save_config(self, data):
        # Guardar en SystemConfiguration
        SystemConfiguration.objects.update_or_create(
            key='cdn.provider', defaults={'value': data.get('provider', ''), 'is_active': True}
        )
        SystemConfiguration.objects.update_or_create(
            key='cdn.domain', defaults={'value': data.get('domain', ''), 'is_active': True}
        )
        SystemConfiguration.objects.update_or_create(
            key='cdn.enabled', defaults={'value': str(data.get('enabled', False)).lower(), 'is_active': True}
        )
        SystemConfiguration.objects.update_or_create(
            key='cdn.cache_headers.static', defaults={'value': data.get('cache_headers_static', ''), 'is_active': True}
        )
        SystemConfiguration.objects.update_or_create(
            key='cdn.cache_headers.media', defaults={'value': data.get('cache_headers_media', ''), 'is_active': True}
        )
        SystemConfiguration.objects.update_or_create(
            key='cdn.cache_headers.images', defaults={'value': data.get('cache_headers_images', ''), 'is_active': True}
        ) 