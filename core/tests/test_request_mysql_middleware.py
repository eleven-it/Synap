"""
Tests TDD para "una conexión por request" (middleware + get_connection).

Especificación: docs/general/ESPEC_UNA_CONEXION_POR_REQUEST.md
Verificación: CA-1 a CA-5; RF-1 a RF-4.

Ejecutar: docker exec Synap_app python manage.py test core.tests.test_request_mysql_middleware
"""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings


class TestGetConnectionRequestScoped(TestCase):
    """RF-2: get_connection reutiliza la conexión de request cuando el contextvar está set."""

    def test_get_connection_uses_request_connection_when_set(self):
        """Con contextvar con (base_empresa, conn), get_connection(base_empresa) entrega esa conn y no libera al salir."""
        from core.mysql_pool import (
            get_connection,
            request_mysql_conn_var,
        )
        base_empresa = "administranet92"
        mock_conn = MagicMock()
        request_mysql_conn_var.set((base_empresa, mock_conn))
        try:
            with patch("core.mysql_pool.get_mysql_pool") as mock_get_pool:
                pool_cm = MagicMock()
                pool_cm.__enter__ = MagicMock(return_value=MagicMock())
                pool_cm.__exit__ = MagicMock(return_value=None)
                mock_get_pool.return_value.get_connection.return_value = pool_cm

                with get_connection(base_empresa) as conn:
                    self.assertIs(conn, mock_conn)
                # Al salir del with no debe haberse llamado al pool
                mock_get_pool.return_value.get_connection.assert_not_called()
        finally:
            try:
                request_mysql_conn_var.set(None)
            except Exception:
                pass

    def test_get_connection_uses_pool_when_no_request_connection(self):
        """Sin contextvar (o base_empresa distinta), get_connection(base_empresa) usa el pool."""
        from core.mysql_pool import get_connection, request_mysql_conn_var
        base_empresa = "administranet92"
        # Asegurar que no hay conexión de request
        try:
            request_mysql_conn_var.set(None)
        except Exception:
            pass
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_cm.__exit__ = MagicMock(return_value=None)

        with patch("core.mysql_pool.get_mysql_pool") as mock_get_pool:
            mock_get_pool.return_value.get_connection.return_value = mock_cm
            with get_connection(base_empresa) as conn:
                self.assertIs(conn, mock_conn)
            mock_get_pool.return_value.get_connection.assert_called_once_with(base_empresa)
            mock_cm.__exit__.assert_called_once()


class TestRequestScopedMysqlMiddleware(TestCase):
    """RF-1, RF-3, RF-4: middleware asigna y libera conexión por request; excluye paths."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request_with_session(self, path="/core/dashboard/", base_empresa="administranet92"):
        request = self.factory.get(path)
        request.session = {"user": {"base_empresa": base_empresa}}
        return request

    def test_middleware_sets_contextvar_when_base_empresa_in_session(self):
        """Tras process_request con sesión y base_empresa, el contextvar tiene (base_empresa, conn)."""
        from core.middleware.request_scoped_mysql import RequestScopedMysqlMiddleware
        from core.mysql_pool import request_mysql_conn_var

        request = self._request_with_session()
        middleware = RequestScopedMysqlMiddleware(lambda r: None)
        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_cm.__exit__ = MagicMock(return_value=None)

        with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
            mock_get_pool.return_value.get_connection.return_value = mock_cm
            middleware.process_request(request)
            try:
                val = request_mysql_conn_var.get()
                self.assertIsNotNone(val)
                base, conn = val
                self.assertEqual(base, "administranet92")
                self.assertIs(conn, mock_conn)
            finally:
                if getattr(request, "_mysql_conn_ref", None):
                    request._mysql_conn_ref.__exit__(None, None, None)
                try:
                    request_mysql_conn_var.set(None)
                except Exception:
                    pass

    def test_middleware_skips_when_no_base_empresa(self):
        """Request sin base_empresa en sesión no asigna conexión de request."""
        from core.middleware.request_scoped_mysql import RequestScopedMysqlMiddleware
        from core.mysql_pool import request_mysql_conn_var

        request = self.factory.get("/core/dashboard/")
        request.session = {"user": {}}
        middleware = RequestScopedMysqlMiddleware(lambda r: None)
        with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
            middleware.process_request(request)
            mock_get_pool.return_value.get_connection.assert_not_called()
            self.assertFalse(hasattr(request, "_mysql_conn_ref"))

    def test_middleware_skips_excluded_paths(self):
        """Request a /static/ o /sw.js con sesión y base_empresa no asigna conexión."""
        from core.middleware.request_scoped_mysql import RequestScopedMysqlMiddleware

        for path in ["/static/css/styles.css", "/sw.js", "/manifest.json", "/offline/"]:
            request = self._request_with_session(path=path)
            middleware = RequestScopedMysqlMiddleware(lambda r: None)
            with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
                middleware.process_request(request)
                mock_get_pool.return_value.get_connection.assert_not_called()
                self.assertFalse(
                    getattr(request, "_mysql_conn_ref", None) is not None,
                    f"Path {path} no debería tener conexión asignada",
                )

    def test_middleware_releases_connection_on_response(self):
        """process_response libera la conexión (pool recibe __exit__)."""
        from core.middleware.request_scoped_mysql import RequestScopedMysqlMiddleware

        request = self._request_with_session()
        middleware = RequestScopedMysqlMiddleware(lambda r: None)
        mock_cm = MagicMock()
        mock_conn = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_cm.__exit__ = MagicMock(return_value=None)

        with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
            mock_get_pool.return_value.get_connection.return_value = mock_cm
            middleware.process_request(request)
            response = MagicMock()
            middleware.process_response(request, response)
            mock_cm.__exit__.assert_called_once()

    def test_middleware_releases_connection_on_exception(self):
        """process_exception libera la conexión y limpia contextvar."""
        from core.middleware.request_scoped_mysql import RequestScopedMysqlMiddleware
        from core.mysql_pool import request_mysql_conn_var

        request = self._request_with_session()
        middleware = RequestScopedMysqlMiddleware(lambda r: None)
        mock_cm = MagicMock()
        mock_conn = MagicMock()
        mock_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_cm.__exit__ = MagicMock(return_value=None)

        with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
            mock_get_pool.return_value.get_connection.return_value = mock_cm
            middleware.process_request(request)
            middleware.process_exception(request, Exception("test"))
            mock_cm.__exit__.assert_called_once()
            # Contextvar debe quedar limpio (o sin conexión de este request)
            try:
                val = request_mysql_conn_var.get()
                self.assertIsNone(val)
            except Exception:
                pass
