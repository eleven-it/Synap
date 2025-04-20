from django.utils import translation

class IdiomaUsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.session.get("user")
        idioma = user.get("idioma") if user else None

        if idioma in dict(translation.get_supported_language_variant(lang) for lang in ['es', 'en', 'pt']):
            translation.activate(idioma)
            request.LANGUAGE_CODE = idioma

        response = self.get_response(request)
        translation.deactivate()
        return response
