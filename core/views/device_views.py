# Vista para que el cliente actualice la cookie device_hint vía POST (opcional).
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from core.middleware.base_middleware import DEVICE_HINT_COOKIE


@csrf_exempt
@require_POST
def set_device_hint(request):
    hint = (request.POST.get('hint') or '').strip().lower()
    if hint not in ('mobile', 'desktop'):
        return JsonResponse({'error': 'invalid'}, status=400)
    response = JsonResponse({'ok': True})
    response.set_cookie(
        DEVICE_HINT_COOKIE,
        hint,
        max_age=86400,
        path='/',
        samesite='Lax',
        httponly=False,
    )
    return response
