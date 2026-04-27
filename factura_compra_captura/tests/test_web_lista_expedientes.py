"""Vista web listado expedientes captura."""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import Client, TestCase

from core.models import Empresa, UsuarioExtendido
from factura_compra_captura.models import DocumentoFuente, ExpedienteFacturaCompra
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

    def test_lista_expedientes_403_sin_permiso_modulo(self):
        u = UsuarioExtendido.objects.create_user(
            email="sin-perm-captura@test.local",
            nombre="Sin Perm",
            password="secret123",
        )
        u.uid = "uid-sin-perm-captura"
        u.save()
        c = Client()
        c.force_login(u)
        s = c.session
        s["user"] = {"uid": u.uid}
        s.save()
        cache.delete(f"user_session_{u.uid}")
        r = c.get("/compras/captura/expedientes/")
        self.assertEqual(r.status_code, 403)

    def test_captura_movil_403_sin_permiso_modulo(self):
        u = UsuarioExtendido.objects.create_user(
            email="sin-perm-movil@test.local",
            nombre="Sin Perm Movil",
            password="secret123",
        )
        u.uid = "uid-sin-perm-movil"
        u.save()
        c = Client()
        c.force_login(u)
        s = c.session
        s["user"] = {"uid": u.uid}
        s.save()
        cache.delete(f"user_session_{u.uid}")
        r = c.get("/compras/captura/movil/")
        self.assertEqual(r.status_code, 403)

    def test_revision_403_empresa_sesion_distinta(self):
        emp_a = Empresa.objects.create(
            nombre="Emp A",
            razon_social="Emp A SA",
            identificador_fiscal="20111111112",
        )
        emp_b = Empresa.objects.create(
            nombre="Emp B",
            razon_social="Emp B SA",
            identificador_fiscal="20111111113",
        )
        exp = ExpedienteFacturaCompra.objects.create(
            empresa_id=emp_a.pk,
            estado=ExpedienteFacturaCompra.Estado.BORRADOR,
        )
        u = UsuarioExtendido.objects.create_user(
            email="revision-emp@test.local",
            nombre="Revision Emp",
            password="secret123",
        )
        u.uid = "uid-revision-emp"
        u.save()
        ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
        u.user_permissions.add(Permission.objects.get(content_type=ct, codename="editar"))
        c = Client()
        c.force_login(u)
        s = c.session
        s["user"] = {"uid": u.uid}
        s["empresa_activa_id"] = emp_b.pk
        s.save()
        cache.delete(f"user_session_{u.uid}")
        r = c.get(f"/compras/captura/revision/{exp.pk}/")
        self.assertEqual(r.status_code, 403)

    def _login_cliente_uid(self, client: Client, user: UsuarioExtendido) -> None:
        client.force_login(user)
        s = client.session
        s["user"] = {"uid": user.uid}
        s.save()
        cache.delete(f"user_session_{user.uid}")

    def test_documento_fuente_404_sin_empresa_en_sesion(self):
        exp = ExpedienteFacturaCompra.objects.create(
            empresa_id=self.empresa.pk,
            estado=ExpedienteFacturaCompra.Estado.BORRADOR,
        )
        doc = DocumentoFuente.objects.create(
            expediente=exp,
            archivo=ContentFile(b"%PDF-1.1\n", "x.pdf"),
            tipo_archivo=DocumentoFuente.TipoArchivo.PDF,
            mime_type="application/pdf",
        )
        u = UsuarioExtendido.objects.create_user(
            email="doc-sin-emp@test.local",
            nombre="Doc Sin Emp",
            password="secret123",
        )
        u.uid = "uid-doc-sin-emp"
        u.save()
        ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
        u.user_permissions.add(Permission.objects.get(content_type=ct, codename="editar"))
        c = Client()
        self._login_cliente_uid(c, u)
        s = c.session
        if "empresa_activa_id" in s:
            del s["empresa_activa_id"]
        su = dict(s.get("user") or {})
        su.pop("id_empresa", None)
        s["user"] = su
        s.save()
        cache.delete(f"user_session_{u.uid}")
        r = c.get(
            f"/compras/captura/revision/{exp.pk}/documento/{doc.pk}/",
        )
        self.assertEqual(r.status_code, 404)

    def test_documento_fuente_200_permiso_y_empresa_ok(self):
        exp = ExpedienteFacturaCompra.objects.create(
            empresa_id=self.empresa.pk,
            estado=ExpedienteFacturaCompra.Estado.BORRADOR,
        )
        doc = DocumentoFuente.objects.create(
            expediente=exp,
            archivo=ContentFile(b"%PDF-1.1\n", "y.pdf"),
            tipo_archivo=DocumentoFuente.TipoArchivo.PDF,
            mime_type="application/pdf",
        )
        u = UsuarioExtendido.objects.create_user(
            email="doc-ok@test.local",
            nombre="Doc Ok",
            password="secret123",
        )
        u.uid = "uid-doc-ok"
        u.save()
        ct = ContentType.objects.get_for_model(ExpedienteFacturaCompra)
        u.user_permissions.add(Permission.objects.get(content_type=ct, codename="editar"))
        c = Client()
        self._login_cliente_uid(c, u)
        s = c.session
        s["empresa_activa_id"] = self.empresa.pk
        s.save()
        r = c.get(
            f"/compras/captura/revision/{exp.pk}/documento/{doc.pk}/",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
