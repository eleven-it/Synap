from django.test import TestCase, override_settings
from unittest.mock import patch, Mock
import json


@override_settings(
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
    N8N_SQL_CHAT_WEBHOOK='https://test-n8n.example.com/webhook/sql-chat'
)
class SqlChatAPITestCase(TestCase):
    """Tests para el endpoint de SQL chat con n8n."""

    def setUp(self):
        """Configuración inicial para los tests."""
        self.client = TestCase.client_class()
        self.url = '/finance/api/ai/sql-chat'
        self.valid_data = {
            'user_id': 'user123',
            'message': '¿Cuáles fueron las ventas del mes pasado?',
            'company_ids': [1, 2],
            'locale': 'es'
        }

    def test_sql_chat_success(self):
        """Test petición exitosa al webhook de n8n."""
        # Mock de la respuesta de n8n
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sql': 'SELECT SUM(net_amount) FROM finance_financialentry WHERE entry_type = "sale"',
            'results': [{'total_sales': 1500.00}],
            'explanation': 'Consulta ejecutada exitosamente'
        }
        mock_response.content = b'{"sql": "SELECT..."}'
        
        with patch('requests.post', return_value=mock_response):
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sql', data)
        self.assertIn('results', data)
        self.assertIn('explanation', data)

    def test_sql_chat_missing_user_id(self):
        """Test error cuando falta user_id."""
        invalid_data = self.valid_data.copy()
        del invalid_data['user_id']
        
        response = self.client.post(
            self.url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('user_id is required', data['detail'])

    def test_sql_chat_missing_message(self):
        """Test error cuando falta message."""
        invalid_data = self.valid_data.copy()
        del invalid_data['message']
        
        response = self.client.post(
            self.url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('message is required', data['detail'])

    def test_sql_chat_invalid_json(self):
        """Test error con JSON inválido."""
        response = self.client.post(
            self.url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('Invalid JSON', data['detail'])

    def test_sql_chat_wrong_method(self):
        """Test error con método HTTP incorrecto."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('method not allowed', data['detail'])

    def test_sql_chat_n8n_timeout(self):
        """Test manejo de timeout de n8n."""
        with patch('requests.post', side_effect=Exception('Request timeout')):
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('Request timeout', data['detail'])

    def test_sql_chat_n8n_connection_error(self):
        """Test manejo de error de conexión con n8n."""
        with patch('requests.post', side_effect=Exception('Connection error')):
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('Connection error', data['detail'])

    def test_sql_chat_n8n_error_response(self):
        """Test manejo de respuesta de error de n8n."""
        # Mock de respuesta de error de n8n
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            'error': 'SQL syntax error',
            'details': 'Invalid query structure'
        }
        mock_response.content = b'{"error": "SQL syntax error"}'
        
        with patch('requests.post', return_value=mock_response):
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)

    def test_sql_chat_minimal_data(self):
        """Test con datos mínimos requeridos."""
        minimal_data = {
            'user_id': 'user123',
            'message': '¿Cuántas ventas hubo?'
        }
        
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sql': 'SELECT COUNT(*) FROM finance_financialentry WHERE entry_type = "sale"',
            'results': [{'count': 5}]
        }
        mock_response.content = b'{"sql": "SELECT..."}'
        
        with patch('requests.post', return_value=mock_response):
            response = self.client.post(
                self.url,
                data=json.dumps(minimal_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('sql', data)
        self.assertIn('results', data)

    def test_sql_chat_with_api_key(self):
        """Test que se incluye API key si está configurada."""
        with override_settings(N8N_API_KEY='test-api-key'):
            with patch('requests.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'success': True}
                mock_response.content = b'{"success": true}'
                mock_post.return_value = mock_response
                
                response = self.client.post(
                    self.url,
                    data=json.dumps(self.valid_data),
                    content_type='application/json'
                )
                
                # Verificar que se llamó con el header de API key
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                headers = call_args[1]['headers']
                self.assertEqual(headers['X-API-KEY'], 'test-api-key')

    def test_sql_chat_headers_included(self):
        """Test que se incluyen los headers correctos."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'success': True}
            mock_response.content = b'{"success": true}'
            mock_post.return_value = mock_response
            
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            
            # Verificar headers
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            self.assertEqual(headers['Content-Type'], 'application/json')
            self.assertEqual(headers['User-Agent'], 'Synap-Finance-Proxy/1.0')

    def test_sql_chat_timeout_configuration(self):
        """Test que se configura el timeout correctamente."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'success': True}
            mock_response.content = b'{"success": true}'
            mock_post.return_value = mock_response
            
            response = self.client.post(
                self.url,
                data=json.dumps(self.valid_data),
                content_type='application/json'
            )
            
            # Verificar timeout
            call_args = mock_post.call_args
            self.assertEqual(call_args[1]['timeout'], 30)


