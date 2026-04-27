import os

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, TemplateView

from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
from factura_compra_captura.permisos_modulo import usuario_puede_acceder_modulo_captura
from factura_compra_captura.session_empresa import empresa_synap_id_desde_sesion

# Alias usado en esta app (misma función que API)
empresa_id_desde_sesion = empresa_synap_id_desde_sesion


class CapturaMovilView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Shell móvil mínimo (Fase 2): cámara/archivo + subida a la API.
    Mismo criterio de acceso que el listado de expedientes (``compras.ver`` o ``factura_compra_captura.ver``).
    """

    template_name = "factura_compra_captura/captura_movil.html"

    def test_func(self):
        return usuario_puede_acceder_modulo_captura(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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
        if not u.has_perm("factura_compra_captura.editar"):
            return False
        expediente = ExpedienteFacturaCompra.objects.filter(pk=self.kwargs.get("pk")).first()
        if expediente is None:
            return True
        eid = empresa_id_desde_sesion(self.request)
        if eid is None:
            return False
        return int(expediente.empresa_id) == int(eid)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        expediente = (
            ExpedienteFacturaCompra.objects.prefetch_related("documentos_fuente")
            .filter(pk=kwargs["pk"])
            .first()
        )
        if not expediente:
            ctx["expediente_id"] = str(kwargs["pk"])
            ctx["documento_url"] = None
            ctx["documento_es_pdf"] = False
        else:
            doc = (
                expediente.documentos_fuente.filter(
                    tipo_archivo=DocumentoFuente.TipoArchivo.PDF
                )
                .order_by("-creado_en")
                .first()
                or expediente.documentos_fuente.order_by("-creado_en").first()
            )
            ctx["expediente_id"] = str(expediente.pk)
            if doc and doc.archivo:
                rel = reverse(
                    "factura_compra_captura_web:documento-fuente",
                    kwargs={"pk": expediente.pk, "doc_pk": doc.pk},
                )
                ctx["documento_url"] = self.request.build_absolute_uri(rel)
            else:
                ctx["documento_url"] = None
            ctx["documento_es_pdf"] = bool(
                doc and doc.tipo_archivo == DocumentoFuente.TipoArchivo.PDF
            )
        ctx["csrf_token_value"] = get_token(self.request)
        return ctx


class DocumentoFuenteServeView(View):
    """
    Sirve PDF/imagen para el iframe de revisión.
    Requiere usuario autenticado (middleware Synap), permiso de edición del expediente
    y empresa activa en sesión coincidente con el expediente.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise Http404()
        if not (
            getattr(request.user, "is_superuser", False)
            or request.user.has_perm("factura_compra_captura.editar")
        ):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, doc_pk):
        expediente = get_object_or_404(ExpedienteFacturaCompra, pk=pk)
        sess_emp = empresa_id_desde_sesion(request)
        if sess_emp is None:
            raise Http404()
        if int(expediente.empresa_id) != int(sess_emp):
            raise Http404()
        doc = get_object_or_404(
            DocumentoFuente, pk=doc_pk, expediente_id=expediente.pk
        )
        if not doc.archivo:
            raise Http404()
        try:
            fh = doc.archivo.open("rb")
        except OSError:
            raise Http404() from None
        ct = (doc.mime_type or "").strip() or "application/octet-stream"
        if doc.tipo_archivo == DocumentoFuente.TipoArchivo.PDF:
            ct = "application/pdf"
        elif "jpeg" in ct.lower() or "jpg" in ct.lower():
            ct = "image/jpeg"
        elif "png" in ct.lower():
            ct = "image/png"
        resp = FileResponse(fh, content_type=ct)
        name = os.path.basename(doc.archivo.name)
        resp["Content-Disposition"] = f'inline; filename="{name}"'
        return resp


class ListaExpedientesCompraView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Listado web de expedientes de captura (Synap) filtrados por empresa de sesión.
    """

    model = ExpedienteFacturaCompra
    template_name = "factura_compra_captura/lista_expedientes.html"
    context_object_name = "expedientes"
    paginate_by = 25

    def test_func(self):
        return usuario_puede_acceder_modulo_captura(self.request.user)

    def get_queryset(self):
        eid = empresa_id_desde_sesion(self.request)
        qs = (
            ExpedienteFacturaCompra.objects.select_related("empresa")
            .order_by("-creado_en")
        )
        if eid is None:
            return qs.none()
        return qs.filter(empresa_id=eid)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        eid = empresa_id_desde_sesion(self.request)
        ctx["empresa_sesion_id"] = eid
        ctx["empresa_sesion_nombre"] = None
        if eid is not None:
            from core.models import Empresa

            emp = Empresa.objects.filter(pk=eid).only("nombre").first()
            if emp:
                ctx["empresa_sesion_nombre"] = emp.nombre
        u = self.request.user
        ctx["puede_revisar"] = (
            getattr(u, "is_superuser", False)
            or u.has_perm("factura_compra_captura.editar")
        )
        return ctx
