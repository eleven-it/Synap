"""
Tests para la vista SqlChatView del chat de IA SQL.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, Mock
from django.test.utils import override_settings
import json

User = get_user_model()


@override_settings(
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]
)
class SqlChatViewTestCase(TestCase):
    """Tests para la vista SqlChatView."""
    
    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            nombre='Test User',
            password='testpass123'
        )
        self.url = reverse('finance:ai_sql_chat')
    
    def test_get_renders_form(self):
        """Test que GET renderiza el formulario correctamente."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat SQL de IA')
        self.assertContains(response, 'Nueva Consulta')
        self.assertContains(response, 'name="message"')
    
    def test_get_requires_login(self):
        """Test que GET requiere autenticación."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_webhook_not_configured_warning(self):
        """Test que se muestra advertencia cuando el webhook no está configurado."""
        with override_settings(N8N_SQL_CHAT_WEBHOOK=''):
            self.client.login(email='test@example.com', password='testpass123')
            response = self.client.get(self.url)
            
            self.assertContains(response, 'Webhook no configurado')
            self.assertContains(response, 'N8N_SQL_CHAT_WEBHOOK')
    
    def test_webhook_configured_no_warning(self):
        """Test que no se muestra advertencia cuando el webhook está configurado."""
        with override_settings(N8N_SQL_CHAT_WEBHOOK='https://example.com/webhook'):
            self.client.login(email='test@example.com', password='testpass123')
            response = self.client.get(self.url)
            
            self.assertNotContains(response, 'Webhook no configurado')
    
    @patch('finance.services.sql_chat.run_sql_chat')
    def test_post_successful_query(self, mock_run_sql_chat):
        """Test POST con consulta exitosa."""
        # Mock de respuesta exitosa
        mock_response = {
            'ok': True,
            'sql': 'SELECT * FROM cuentacliente LIMIT 10',
            'columns': ['id', 'fecha', 'importe'],
            'rows': [
                {'id': 1, 'fecha': '2024-01-01', 'importe': 1000.00},
                {'id': 2, 'fecha': '2024-01-02', 'importe': 2000.00}
            ],
            'rowcount': 2,
            'meta': {
                'autoLimited': False,
                'risk': 'bajo',
                'explanation': 'Consulta simple de ventas',
                'tables_detected': ['cuentacliente']
            }
        }
        mock_run_sql_chat.return_value = mock_response
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'message': 'Muéstrame las ventas del último mes',
            'year': '2024',
            'currency': 'ARS'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resultados')
        self.assertContains(response, 'SELECT * FROM cuentacliente LIMIT 10')
        self.assertContains(response, 'Consulta simple de ventas')
        self.assertContains(response, 'bajo')
        
        # Verificar que se llamó al servicio con los parámetros correctos
        mock_run_sql_chat.assert_called_once()
        call_args = mock_run_sql_chat.call_args
        self.assertEqual(call_args[1]['message'], 'Muéstrame las ventas del último mes')
        self.assertEqual(call_args[1]['year'], 2024)
        self.assertEqual(call_args[1]['currency'], 'ARS')
        self.assertEqual(call_args[1]['user_id'], str(self.user.pk))
    
    @patch('finance.services.sql_chat.run_sql_chat')
    def test_post_error_response(self, mock_run_sql_chat):
        """Test POST con respuesta de error."""
        # Mock de respuesta de error
        mock_response = {
            'ok': False,
            'reason': 'Error de conexión',
            'details': {'error_type': 'ConnectionError'}
        }
        mock_run_sql_chat.return_value = mock_response
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'message': 'Consulta inválida'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error en la consulta')
        self.assertContains(response, 'Error de conexión')
        self.assertContains(response, 'ConnectionError')
    
    def test_post_invalid_form(self):
        """Test POST con formulario inválido."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'message': '',  # Campo requerido vacío
            'date_from': '2024-12-31',
            'date_to': '2024-01-01'  # Fecha inválida (después de date_from)
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este campo es obligatorio')
        self.assertContains(response, 'La fecha \'Desde\' debe ser anterior')
    
    @patch('finance.services.sql_chat.run_sql_chat')
    def test_post_with_date_filters(self, mock_run_sql_chat):
        """Test POST con filtros de fecha."""
        mock_response = {'ok': True, 'sql': 'SELECT * FROM test', 'columns': [], 'rows': [], 'rowcount': 0, 'meta': {}}
        mock_run_sql_chat.return_value = mock_response
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'message': 'Consulta con fechas',
            'date_from': '2024-01-01',
            'date_to': '2024-12-31'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que se pasaron las fechas correctamente
        call_args = mock_run_sql_chat.call_args
        self.assertEqual(call_args[1]['date_from'], '2024-01-01')
        self.assertEqual(call_args[1]['date_to'], '2024-12-31')
    
    @patch('finance.services.sql_chat.run_sql_chat')
    def test_post_sql_escaping(self, mock_run_sql_chat):
        """Test que el SQL se escapa correctamente en el template."""
        # Mock con SQL que contiene caracteres especiales
        mock_response = {
            'ok': True,
            'sql': '<script>alert("xss")</script>SELECT * FROM test',
            'columns': ['col1'],
            'rows': [{'col1': 'value1'}],
            'rowcount': 1,
            'meta': {'risk': 'bajo'}
        }
        mock_run_sql_chat.return_value = mock_response
        
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.post(self.url, {
            'message': 'Test SQL escaping'
        })
        
        self.assertEqual(response.status_code, 200)
        # Verificar que el script no se ejecuta (se escapa)
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;SELECT')
        self.assertNotContains(response, '<script>alert("xss")</script>')
    
    @patch('finance.services.sql_chat.run_sql_chat')
    def test_post_respects_max_rows(self, mock_run_sql_chat):
        """Test que se respeta el límite de filas configurado."""
        # Mock con muchas filas
        many_rows = [{'col1': f'value{i}'} for i in range(300)]
        mock_response = {
            'ok': True,
            'sql': 'SELECT * FROM test',
            'columns': ['col1'],
            'rows': many_rows,
            'rowcount': 300,
            'meta': {'risk': 'bajo'}
        }
        mock_run_sql_chat.return_value = mock_response
        
        with override_settings(FINANCE_MAX_ROWS=50):
            self.client.login(email='test@example.com', password='testpass123')
            response = self.client.post(self.url, {
                'message': 'Test max rows'
            })
            
            self.assertEqual(response.status_code, 200)
            # Verificar que se limitó a 50 filas
            self.assertContains(response, 'Limitado')
            self.assertContains(response, 'limitado a 50 filas por seguridad')


class SqlChatServiceTestCase(TestCase):
    """Tests para el servicio run_sql_chat."""
    
    @patch('finance.services.sql_chat.requests.post')
    def test_run_sql_chat_success(self, mock_post):
        """Test llamada exitosa al servicio."""
        # Mock de respuesta HTTP exitosa
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'sql': 'SELECT * FROM test',
            'columns': ['col1'],
            'rows': [{'col1': 'value1'}],
            'rowcount': 1,
            'meta': {'risk': 'bajo'}
        }
        mock_post.return_value = mock_response
        
        from finance.services.sql_chat import run_sql_chat
        
        result = run_sql_chat(
            message='Test message',
            user_id='test_user',
            year=2024,
            currency='ARS'
        )
        
        self.assertTrue(result['ok'])
        self.assertEqual(result['sql'], 'SELECT * FROM test')
        
        # Verificar que se hizo la petición correcta
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json']['message'], 'Test message')
        self.assertEqual(call_args[1]['json']['user_id'], 'test_user')
        self.assertEqual(call_args[1]['json']['year'], 2024)
        self.assertEqual(call_args[1]['json']['currency'], 'ARS')
    
    @patch('finance.services.sql_chat.requests.post')
    def test_run_sql_chat_timeout(self, mock_post):
        """Test manejo de timeout."""
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout()
        
        from finance.services.sql_chat import run_sql_chat
        
        result = run_sql_chat(
            message='Test message',
            user_id='test_user'
        )
        
        self.assertFalse(result['ok'])
        self.assertIn('Timeout', result['reason'])
    
    @patch('finance.services.sql_chat.requests.post')
    def test_run_sql_chat_connection_error(self, mock_post):
        """Test manejo de error de conexión."""
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError()
        
        from finance.services.sql_chat import run_sql_chat
        
        result = run_sql_chat(
            message='Test message',
            user_id='test_user'
        )
        
        self.assertFalse(result['ok'])
        self.assertIn('conexión', result['reason'])
    
    def test_run_sql_chat_no_webhook_configured(self):
        """Test cuando no hay webhook configurado."""
        with override_settings(N8N_SQL_CHAT_WEBHOOK=''):
            from finance.services.sql_chat import run_sql_chat
            
            result = run_sql_chat(
                message='Test message',
                user_id='test_user'
            )
            
            self.assertFalse(result['ok'])
            self.assertIn('no configurado', result['reason'])
    
    @patch('finance.services.sql_chat.requests.post')
    def test_run_sql_chat_limits_rows(self, mock_post):
        """Test que se limitan las filas según FINANCE_MAX_ROWS."""
        # Mock con muchas filas
        many_rows = [{'col1': f'value{i}'} for i in range(300)]
        mock_response = Mock()
        mock_response.json.return_value = {
            'ok': True,
            'sql': 'SELECT * FROM test',
            'columns': ['col1'],
            'rows': many_rows,
            'rowcount': 300,
            'meta': {'risk': 'bajo'}
        }
        mock_post.return_value = mock_response
        
        with override_settings(FINANCE_MAX_ROWS=50):
            from finance.services.sql_chat import run_sql_chat
            
            result = run_sql_chat(
                message='Test message',
                user_id='test_user'
            )
            
            self.assertTrue(result['ok'])
            self.assertEqual(len(result['rows']), 50)
            self.assertTrue(result['meta']['autoLimited'])
            self.assertIn('limitado a 50 filas', result['meta']['explanation'])
