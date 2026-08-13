"""Tests UX/config: wizard persist, no dummy auto-sync, validaciones first-run."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import UsuarioExtendido
from tiendanube_administranet.forms import AdministraNETConfigForm, TiendanubeConfigForm
from tiendanube_administranet.models import AdministraNETConfig, TiendanubeConfig
from tiendanube_administranet.views import AutoSyncConfigView
from tiendanube_administranet.views.config_views import TiendanubeConfigWizardView


def _tn_perms(user, *codenames):
    ct = ContentType.objects.get_for_model(TiendanubeConfig)
    for codename in codenames:
        perm = Permission.objects.get(codename=codename, content_type=ct)
        user.user_permissions.add(perm)


def _prepare_request(request, user, session_extra=None):
    request.user = user
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session['user'] = {
        'base_empresa': 'test_empresa',
        'id_usuario': 1,
        'cod_usuario': 'admin',
    }
    if session_extra:
        request.session.update(session_extra)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))
    return request


class WizardSaveStorePersistTests(TestCase):
    """Wizard save_store MUST persist auto_sync y prefs de sincronización."""

    def setUp(self):
        self.user = UsuarioExtendido.objects.create_user(
            email='wiz@test.com', nombre='Wizard', password='pass',
        )
        _tn_perms(self.user, 'add_tiendanubeconfig')
        self.factory = RequestFactory()

    @patch('tiendanube_administranet.views.config_views.requests.get')
    def test_save_store_persiste_auto_sync_y_prefs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'name': 'Mi Tienda Test'}
        mock_get.return_value = mock_resp

        url = reverse('tiendanube_administranet:tiendanube_config_wizard') + '?step=6'
        request = _prepare_request(
            self.factory.post(url, {'save_store': '1'}),
            self.user,
            {
                'wizard_access_token': 'token-wizard-abc',
                'wizard_user_id': 'store-wiz-99',
                'wizard_auto_sync': True,
                'wizard_sync_interval': 60,
                'wizard_sync_products': True,
                'wizard_sync_stock': False,
                'wizard_webhook_secret': 'hmac-test-secret',
            },
        )
        view = TiendanubeConfigWizardView.as_view()
        response = view(request)

        self.assertEqual(response.status_code, 302)
        config = TiendanubeConfig.objects.get(store_id='store-wiz-99')
        self.assertTrue(config.is_active)
        self.assertTrue(config.auto_sync)
        self.assertEqual(config.sync_interval, 60)
        self.assertTrue(config.sync_products)
        self.assertFalse(config.sync_stock)
        self.assertEqual(config.webhook_secret, 'hmac-test-secret')


class AutoSyncNoDummyConfigTests(TestCase):
    """AutoSyncConfigView MUST NOT crear config dummy store_id=default."""

    def setUp(self):
        self.user = UsuarioExtendido.objects.create_user(
            email='autosync@test.com', nombre='AutoSync', password='pass',
        )
        _tn_perms(self.user, 'change_tiendanubeconfig')
        self.factory = RequestFactory()

    def test_sin_config_redirige_a_wizard_sin_dummy(self):
        url = reverse('tiendanube_administranet:auto_sync_config')
        request = _prepare_request(self.factory.get(url), self.user)
        response = AutoSyncConfigView.as_view()(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn('wizard', response.url)
        self.assertFalse(TiendanubeConfig.objects.filter(store_id='default').exists())


class TiendanubeConfigFormUxTests(TestCase):
    """Form TN: is_active vs auto_sync, token en edición, HMAC prod, depósito stock."""

    def setUp(self):
        self.config = TiendanubeConfig.objects.create(
            name='Tienda form',
            store_id='form-store-1',
            access_token='token-original',
            is_active=True,
            auto_sync=False,
            sync_stock=True,
            webhook_secret='existing-hmac',
        )
        AdministraNETConfig.objects.create(
            name='Adminet form',
            database='test_empresa',
            deposito_tiendanube_id=5,
            punto_venta_tiendanube_id=1,
            is_active=True,
        )

    def _base_data(self, **overrides):
        data = {
            'name': 'Tienda form',
            'store_id': 'form-store-1',
            'access_token': '',
            'is_active': 'on',
            'auto_sync': 'on',
            'sync_interval': 30,
            'sync_products': 'on',
            'sync_customers': 'on',
            'sync_orders': 'on',
            'sync_stock': 'on',
            'webhook_secret': '',
        }
        data.update(overrides)
        return data

    def test_edicion_token_vacio_no_cambia_token(self):
        form = TiendanubeConfigForm(data=self._base_data(access_token=''), instance=self.config)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.access_token, 'token-original')

    def test_is_active_y_auto_sync_independientes(self):
        form = TiendanubeConfigForm(
            data=self._base_data(is_active='on', auto_sync=''),
            instance=self.config,
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertTrue(saved.is_active)
        self.assertFalse(saved.auto_sync)

    @override_settings(ENVIRONMENT='production')
    def test_webhook_secret_obligatorio_en_produccion_alta(self):
        form = TiendanubeConfigForm(data={
            'name': 'Nueva',
            'store_id': 'new-store',
            'access_token': 'tok',
            'is_active': 'on',
            'auto_sync': '',
            'sync_interval': 30,
            'sync_products': 'on',
            'sync_customers': '',
            'sync_orders': '',
            'sync_stock': '',
            'webhook_secret': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('webhook_secret', form.errors)

    def test_sync_stock_requiere_deposito_adminet(self):
        AdministraNETConfig.objects.filter(is_active=True).update(deposito_tiendanube_id=None)
        form = TiendanubeConfigForm(data=self._base_data(sync_stock='on'), instance=self.config)
        self.assertFalse(form.is_valid())
        self.assertIn('sync_stock', form.errors)

    def test_sync_stock_ok_con_deposito_adminet(self):
        form = TiendanubeConfigForm(data=self._base_data(sync_stock='on'), instance=self.config)
        self.assertTrue(form.is_valid(), form.errors)


class AdminetConfigRequiredFieldsTests(TestCase):
    """AdministraNET: depósito y punto de venta obligatorios con tienda activa."""

    def setUp(self):
        TiendanubeConfig.objects.create(
            name='TN activa',
            store_id='tn-req-1',
            access_token='tok',
            is_active=True,
            sync_stock=True,
        )

    def test_deposito_obligatorio_si_sync_stock(self):
        form = AdministraNETConfigForm(data={
            'name': 'Cfg',
            'deposito_tiendanube_choice': '',
            'punto_venta_tiendanube_choice': '',
            'viajante_tiendanube_choice': '',
            'is_active': 'on',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('deposito_tiendanube_choice', form.errors)
        self.assertIn('punto_venta_tiendanube_choice', form.errors)
