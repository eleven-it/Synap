from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.middleware.csrf import get_token
from django.views.generic import TemplateView


class CapturaMovilView(LoginRequiredMixin, TemplateView):
    """
    Shell móvil mínimo (Fase 2): cámara/archivo + subida a la API.
    Requiere sesión; ajustar empresa en query ?empresa=ID.
    """

    template_name = "factura_compra_captura/captura_movil.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["empresa_id_query"] = self.request.GET.get("empresa", "")
        ctx["csrf_token_value"] = get_token(self.request)
        return ctx


class RevisionExpedienteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Pantalla de revisión cabecera/líneas (Fase 3): mobile-first, panel documento + formulario.
    Requiere permiso editar (analista) o superusuario.
    """

    template_name = "factura_compra_captura/revision_expediente.html"

    def test_func(self):
        u = self.request.user
        if not u.is_authenticated:
            return False
        if getattr(u, "is_superuser", False):
            return True
        return u.has_perm("factura_compra_captura.editar")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["expediente_id"] = str(kwargs["pk"])
        ctx["csrf_token_value"] = get_token(self.request)
        return ctx
