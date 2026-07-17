"""Tests procesamiento cola mail e-com con conexión SMTP mockeada."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.models import EcomMailQueue
from ecom.services.comprobante_mail_async import procesar_mail_queue_item


class TestProcesarMailQueueItem(TestCase):
    def setUp(self):
        self.item = EcomMailQueue.objects.create(
            base_empresa="emp1",
            to_email="cliente@test.com",
            subject="Test",
            body_text="Cuerpo",
            body_html="<p>Cuerpo</p>",
            payload_json={
                "comprobante": {
                    "tipocomprobante": "PED",
                    "numerocomprobante": "100",
                    "codigomovimiento": 42,
                }
            },
        )

    @patch("ecom.services.comprobante_mail_async.correo_saliente_configurado", return_value=False)
    def test_sin_smtp_marca_error(self, _mock_cfg):
        ok = procesar_mail_queue_item(self.item.id)
        self.assertFalse(ok)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, EcomMailQueue.STATUS_ERROR)
        self.assertEqual(self.item.last_error, "Correo saliente no configurado")

    @patch("ecom.services.pedido_comprobante_pdf.generar_pedido_pdf", return_value=(False, "skip", None))
    @patch("ecom.services.comprobante_mail_async.get_connection_correo_saliente")
    @patch("ecom.services.comprobante_mail_async.from_email_correo_saliente", return_value="noreply@test.com")
    @patch("ecom.services.comprobante_mail_async.correo_saliente_configurado", return_value=True)
    def test_envio_usa_connection_mockeada(
        self, _mock_cfg, _mock_from, mock_get_conn, _mock_pdf
    ):
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        with patch("ecom.services.comprobante_mail_async.EmailMultiAlternatives") as mock_msg_cls:
            mock_msg = MagicMock()
            mock_msg_cls.return_value = mock_msg
            ok = procesar_mail_queue_item(self.item.id)

        self.assertTrue(ok)
        mock_get_conn.assert_called_once()
        mock_msg_cls.assert_called_once()
        call_kwargs = mock_msg_cls.call_args.kwargs
        self.assertEqual(call_kwargs["connection"], mock_conn)
        self.assertEqual(call_kwargs["from_email"], "noreply@test.com")
        mock_msg.send.assert_called_once_with(fail_silently=False)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, EcomMailQueue.STATUS_SENT)
