"""
Tests para DeviceDetectionMiddleware (detección móvil en dos capas).

Cookie device_hint (mobile|desktop), PHONE_PATTERNS, TABLET_PATTERNS,
compatibilidad synap_prefer_mobile. Ver docs/general/DETECCION_TABLET_IPAD_ANDROID.md.
"""
from django.test import RequestFactory, TestCase

from core.middleware.base_middleware import DeviceDetectionMiddleware


class DeviceDetectionMiddlewareTests(TestCase):
    def _process_request(self, path='/core/dashboard/', user_agent='', cookies=None):
        request = RequestFactory().get(path)
        request.META['HTTP_USER_AGENT'] = user_agent
        if cookies:
            request.COOKIES = cookies
        middleware = DeviceDetectionMiddleware(lambda r: None)
        middleware.process_request(request)
        return request

    def test_cookie_device_hint_mobile_sets_is_mobile(self):
        request = self._process_request(cookies={'device_hint': 'mobile'})
        self.assertTrue(request.is_mobile)
        self.assertFalse(request.is_desktop)

    def test_cookie_device_hint_desktop_sets_is_desktop(self):
        request = self._process_request(
            cookies={'device_hint': 'desktop'},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        )
        self.assertFalse(request.is_mobile)
        self.assertTrue(request.is_desktop)

    def test_no_cookie_ua_iphone_sets_is_mobile(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        self.assertTrue(request.is_mobile)

    def test_no_cookie_ua_macintosh_sets_is_desktop(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Safari/605.1.15'
        )
        self.assertFalse(request.is_mobile)

    def test_no_cookie_ua_android_with_mobile_sets_is_mobile(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (Linux; Android 12; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Mobile Safari/537.36'
        )
        self.assertTrue(request.is_mobile)

    def test_no_cookie_ua_android_without_mobile_sets_is_mobile(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (Linux; Android 12; SM-T870) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Safari/537.36'
        )
        self.assertTrue(request.is_mobile)

    def test_compat_synap_prefer_mobile_1_sets_is_mobile(self):
        request = self._process_request(cookies={'synap_prefer_mobile': '1'})
        self.assertTrue(request.is_mobile)

    def test_compat_synap_prefer_mobile_0_sets_is_desktop(self):
        request = self._process_request(
            cookies={'synap_prefer_mobile': '0'},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        )
        self.assertFalse(request.is_mobile)

    def test_device_hint_overrides_synap_prefer_mobile(self):
        request = self._process_request(cookies={'device_hint': 'desktop', 'synap_prefer_mobile': '1'})
        self.assertFalse(request.is_mobile)

    def test_device_type_android_from_ua(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (Linux; Android 12; SM-T870) AppleWebKit/537.36'
        )
        self.assertEqual(request.device_type, 'android')

    def test_device_type_iphone_from_ua(self):
        request = self._process_request(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        )
        self.assertEqual(request.device_type, 'iphone')
