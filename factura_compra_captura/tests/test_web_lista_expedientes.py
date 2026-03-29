"""Vista web listado expedientes captura."""

from django.core.cache import cache
from django.test import Client, TestCase

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_captura.tests.compras_test_permissions import otorgar_permisos_compras


class ListaExpedientesWebTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa Lista Exp",
            razon_social="Empresa Lista Exp SA",
            identificador_fiscal="20112223334",
        )
        self.user = UsuarioExtendido.objects.create_user(
            email="lista-exp@test.local",
            nombre="Lista User",
            password="secret123",
        )
        self.user.uid = "test-uid-lista-exp"
        self.user.save()
        otorgar_permisos_compras(self.user)

    def _login_cliente_web(self, client: Client) -> None:
        """Synap: RequestUserMiddleware usa session['user']; sin eso request.user queda anónimo."""
        client.force_login(self.user)
        s = client.session
        s["user"] = {"uid": self.user.uid}
        s.save()
        cache.delete(f"user_session_{self.user.uid}")

    def test_lista_expedientes_200_muestra_fila(self):
        ExpedienteFacturaCompra.objects.create(
            empresa_id=self.empresa.pk,
            estado=ExpedienteFacturaCompra.Estado.BORRADOR,
        )
        c = Client()
        self._login_cliente_web(c)
        s = c.session
        s["empresa_activa_id"] = self.empresa.pk
        s.save()
        r = c.get("/compras/captura/expedientes/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Expedientes de captura")
        self.assertContains(r, "Borrador")

    def test_lista_sin_empresa_sesion_aviso(self):
        c = Client()
        self._login_cliente_web(c)
        r = c.get("/compras/captura/expedientes/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "No hay empresa activa en sesión")

    def test_revision_sin_uuid_redirige_a_lista(self):
        c = Client()
        self._login_cliente_web(c)
        r = c.get("/compras/captura/revision/", follow=False)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/compras/captura/expedientes/", r.headers.get("Location", ""))

    def test_lista_con_id_empresa_en_session_user_sin_empresa_activa_id(self):
        """Paridad con login administraNET: id_empresa suele ir en session['user']."""
        ExpedienteFacturaCompra.objects.create(
            empresa_id=self.empresa.pk,
            estado=ExpedienteFacturaCompra.Estado.BORRADOR,
        )
        c = Client()
        self._login_cliente_web(c)
        s = c.session
        s["user"] = {"uid": self.user.uid, "id_empresa": self.empresa.pk}
        s.save()
        cache.delete(f"user_session_{self.user.uid}")
        r = c.get("/compras/captura/expedientes/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Borrador")
