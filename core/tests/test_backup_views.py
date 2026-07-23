"""Tests vistas /core/backups/ (permiso, lanzamiento)."""

from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase

from core.views.views_backup import backup_launch_view, backup_list_view


class _UserConPermiso:
    is_authenticated = True
    is_superuser = False
    cod_usuario = "operador_dr"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code == "administrar.backup"


class _UserSinPermiso:
    is_authenticated = True
    is_superuser = False
    cod_usuario = "vendedor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return False


def _session_user():
    return {
        "id_usuario": 42,
        "cod_usuario": "operador_dr",
        "base_empresa": "empresa_test",
    }


class BackupViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def test_list_sin_permiso_403(self):
        request = self.factory.get("/core/backups/")
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = _UserSinPermiso()
        with self.assertRaises(PermissionDenied):
            backup_list_view(request)

    @patch("core.views.views_backup.render")
    @patch("core.views.views_backup._list_mysql_bases", return_value=[])
    def test_list_con_permiso_200(self, _bases, mock_render):
        from django.http import HttpResponse

        mock_render.return_value = HttpResponse("ok")
        request = self.factory.get("/core/backups/")
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = _UserConPermiso()
        response = backup_list_view(request)
        self.assertEqual(response.status_code, 200)

    @patch("core.views.views_backup._launch_backup_subprocess")
    @patch("core.views.views_backup._list_mysql_bases", return_value=[])
    def test_post_crea_job_con_triggered_by(self, _bases, mock_subprocess):
        from core.backup.models import BackupJob

        request = self.factory.post(
            "/core/backups/lanzar/",
            data={
                "job_type": "full",
                "base_mysql": "empresa_prod",
                "include_empresas": "1",
            },
            HTTP_ACCEPT="application/json",
        )
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = _UserConPermiso()
        response = backup_launch_view(request)
        self.assertEqual(response.status_code, 200)
        job = BackupJob.objects.get()
        self.assertEqual(job.triggered_by_cod_usuario, "operador_dr")
        self.assertEqual(job.triggered_by_id_usuario, 42)
        self.assertEqual(job.base_mysql, "empresa_prod")
        mock_subprocess.assert_called_once()

    @patch("core.views.views_backup._launch_backup_subprocess")
    def test_post_sin_base_rechaza(self, _sub):
        request = self.factory.post(
            "/core/backups/lanzar/",
            data={"job_type": "full", "base_mysql": ""},
            HTTP_ACCEPT="application/json",
        )
        request.session = self.client.session
        request.session["user"] = _session_user()
        request.session.save()
        request.user = _UserConPermiso()
        response = backup_launch_view(request)
        self.assertEqual(response.status_code, 400)
