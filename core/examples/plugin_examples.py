"""
Ejemplos de plugins para el sistema Synap
Demuestra cómo crear plugins modulares para diferentes funcionalidades
"""

from core.plugin_manager import PluginBase
from core.module_events import ModuleEvents, EventDataBuilder


# ============================================================================
# PLUGIN DE INTEGRACIÓN CON EMAIL
# ============================================================================

class EmailIntegrationPlugin(PluginBase):
    """Plugin para integración con servicios de email"""
    
    name = 'email_integration'
    version = '1.0.0'
    description = 'Plugin que agrega funcionalidades de email marketing y notificaciones'
    author = 'Synap Team'
    website = 'https://synap.com'
    license = 'MIT'
    
    requires_modules = ['core']
    optional_modules = ['sales', 'purchases']
    conflicts_with = []
    
    # Hooks que registra
    hooks = {
        'event_user.created': 'on_user_created',
        'event_sale.created': 'on_sale_created',
        'event_invoice.created': 'on_invoice_created',
        'event_payment.received': 'on_payment_received'
    }
    
    # Eventos que escucha
    events = {
        'email.sent': 'on_email_sent',
        'email.failed': 'on_email_failed',
        'campaign.sent': 'on_campaign_sent'
    }
    
    # URLs que agrega
    urls = [
        {'path': 'email/templates/', 'view': 'EmailTemplatesView'},
        {'path': 'email/campaigns/', 'view': 'EmailCampaignsView'},
        {'path': 'email/analytics/', 'view': 'EmailAnalyticsView'}
    ]
    
    # Templates que proporciona
    templates = [
        'email/welcome_template.html',
        'email/sale_confirmation.html',
        'email/invoice_notification.html',
        'email/payment_receipt.html'
    ]
    
    # Configuración por defecto
    default_config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'from_email': 'noreply@synap.com',
        'from_name': 'Synap System',
        'enable_welcome_emails': True,
        'enable_sale_emails': True,
        'enable_invoice_emails': True
    }
    
    def on_user_created(self, event_data):
        """Hook que se ejecuta cuando se crea un usuario"""
        user_id = event_data.get('user_id')
        details = event_data.get('details', {})
        
        # Enviar email de bienvenida
        if self.config.get('enable_welcome_emails'):
            self.send_welcome_email(user_id, details)
        
        return f"Welcome email sent to user {user_id}"
    
    def on_sale_created(self, event_data):
        """Hook que se ejecuta cuando se crea una venta"""
        sale_id = event_data.get('sale_id')
        details = event_data.get('details', {})
        
        # Enviar confirmación de venta
        if self.config.get('enable_sale_emails'):
            self.send_sale_confirmation(sale_id, details)
        
        return f"Sale confirmation sent for sale {sale_id}"
    
    def on_invoice_created(self, event_data):
        """Hook que se ejecuta cuando se crea una factura"""
        invoice_id = event_data.get('sale_id')  # En este contexto, sale_id es invoice_id
        details = event_data.get('details', {})
        
        # Enviar notificación de factura
        if self.config.get('enable_invoice_emails'):
            self.send_invoice_notification(invoice_id, details)
        
        return f"Invoice notification sent for invoice {invoice_id}"
    
    def on_payment_received(self, event_data):
        """Hook que se ejecuta cuando se recibe un pago"""
        payment_data = event_data.get('details', {})
        sale_id = payment_data.get('sale_id')
        amount = payment_data.get('amount', 0)
        
        # Enviar recibo de pago
        self.send_payment_receipt(sale_id, amount, payment_data)
        
        return f"Payment receipt sent for sale {sale_id}"
    
    def on_email_sent(self, event_data):
        """Evento que se ejecuta cuando se envía un email"""
        email_id = event_data.get('email_id')
        recipient = event_data.get('recipient')
        
        # Registrar envío de email
        self.log_email_sent(email_id, recipient)
        
        return f"Email sent logged: {email_id}"
    
    def on_email_failed(self, event_data):
        """Evento que se ejecuta cuando falla un email"""
        email_id = event_data.get('email_id')
        error = event_data.get('error')
        
        # Registrar fallo de email
        self.log_email_failed(email_id, error)
        
        return f"Email failed logged: {email_id}"
    
    def on_campaign_sent(self, event_data):
        """Evento que se ejecuta cuando se envía una campaña"""
        campaign_id = event_data.get('campaign_id')
        recipients_count = event_data.get('recipients_count', 0)
        
        # Registrar envío de campaña
        self.log_campaign_sent(campaign_id, recipients_count)
        
        return f"Campaign sent logged: {campaign_id}"
    
    def on_install(self):
        """Código que se ejecuta al instalar el plugin"""
        # Crear tablas para emails
        self.create_email_tables()
        
        # Crear directorios para templates
        self.create_email_directories()
        
        # Configurar SMTP
        self.setup_smtp_config()
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar el plugin"""
        # Limpiar tablas de emails
        self.cleanup_email_tables()
        
        # Limpiar archivos de emails
        self.cleanup_email_files()
    
    def on_activate(self):
        """Código que se ejecuta al activar el plugin"""
        # Probar conexión SMTP
        self.test_smtp_connection()
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar el plugin"""
        # Limpiar cola de emails
        self.clear_email_queue()
    
    # Funciones auxiliares (simuladas)
    def send_welcome_email(self, user_id, details):
        """Envía email de bienvenida"""
        print(f"Sending welcome email to user {user_id}")
    
    def send_sale_confirmation(self, sale_id, details):
        """Envía confirmación de venta"""
        print(f"Sending sale confirmation for sale {sale_id}")
    
    def send_invoice_notification(self, invoice_id, details):
        """Envía notificación de factura"""
        print(f"Sending invoice notification for invoice {invoice_id}")
    
    def send_payment_receipt(self, sale_id, amount, payment_data):
        """Envía recibo de pago"""
        print(f"Sending payment receipt for sale {sale_id}, amount: ${amount}")
    
    def log_email_sent(self, email_id, recipient):
        """Registra envío de email"""
        print(f"Logging email sent: {email_id} to {recipient}")
    
    def log_email_failed(self, email_id, error):
        """Registra fallo de email"""
        print(f"Logging email failed: {email_id} - {error}")
    
    def log_campaign_sent(self, campaign_id, recipients_count):
        """Registra envío de campaña"""
        print(f"Logging campaign sent: {campaign_id} to {recipients_count} recipients")
    
    def create_email_tables(self):
        """Crea tablas para emails"""
        print("Creating email tables")
    
    def create_email_directories(self):
        """Crea directorios para emails"""
        print("Creating email directories")
    
    def setup_smtp_config(self):
        """Configura SMTP"""
        print("Setting up SMTP configuration")
    
    def cleanup_email_tables(self):
        """Limpia tablas de emails"""
        print("Cleaning up email tables")
    
    def cleanup_email_files(self):
        """Limpia archivos de emails"""
        print("Cleaning up email files")
    
    def test_smtp_connection(self):
        """Prueba conexión SMTP"""
        print("Testing SMTP connection")
    
    def clear_email_queue(self):
        """Limpia cola de emails"""
        print("Clearing email queue")


# ============================================================================
# PLUGIN DE ANÁLISIS DE DATOS
# ============================================================================

class DataAnalyticsPlugin(PluginBase):
    """Plugin para análisis de datos y business intelligence"""
    
    name = 'data_analytics'
    version = '1.0.0'
    description = 'Plugin que agrega capacidades de análisis de datos y BI'
    author = 'Synap Team'
    website = 'https://synap.com'
    license = 'MIT'
    
    requires_modules = ['sales', 'purchases', 'inventory', 'accounting']
    optional_modules = []
    conflicts_with = []
    
    # Hooks que registra
    hooks = {
        'event_sale.completed': 'on_sale_completed',
        'event_purchase.completed': 'on_purchase_completed',
        'event_stock.movement': 'on_stock_movement',
        'event_user.login': 'on_user_login'
    }
    
    # Eventos que escucha
    events = {
        'analytics.data_processed': 'on_data_processed',
        'analytics.insight_generated': 'on_insight_generated'
    }
    
    # URLs que agrega
    urls = [
        {'path': 'analytics/dashboard/', 'view': 'AnalyticsDashboardView'},
        {'path': 'analytics/insights/', 'view': 'InsightsView'},
        {'path': 'analytics/predictions/', 'view': 'PredictionsView'}
    ]
    
    # Templates que proporciona
    templates = [
        'analytics/dashboard.html',
        'analytics/insights_panel.html',
        'analytics/predictions_chart.html'
    ]
    
    # Configuración por defecto
    default_config = {
        'enable_real_time_analytics': True,
        'data_retention_days': 730,
        'prediction_horizon_days': 30,
        'insight_threshold': 0.8,
        'auto_generate_insights': True
    }
    
    def on_sale_completed(self, event_data):
        """Hook que se ejecuta cuando se completa una venta"""
        sale_id = event_data.get('sale_id')
        details = event_data.get('details', {})
        
        # Procesar datos de venta
        self.process_sale_data(sale_id, details)
        
        # Generar insights si está habilitado
        if self.config.get('auto_generate_insights'):
            self.generate_sales_insights(sale_id, details)
        
        return f"Sale data processed for analytics: {sale_id}"
    
    def on_purchase_completed(self, event_data):
        """Hook que se ejecuta cuando se completa una compra"""
        purchase_id = event_data.get('purchase_id')
        details = event_data.get('details', {})
        
        # Procesar datos de compra
        self.process_purchase_data(purchase_id, details)
        
        return f"Purchase data processed for analytics: {purchase_id}"
    
    def on_stock_movement(self, event_data):
        """Hook que se ejecuta cuando hay movimiento de inventario"""
        product_id = event_data.get('product_id')
        quantity = event_data.get('quantity', 0)
        action = event_data.get('action', '')
        
        # Procesar datos de inventario
        self.process_inventory_data(product_id, quantity, action)
        
        return f"Inventory data processed for analytics: {product_id}"
    
    def on_user_login(self, event_data):
        """Hook que se ejecuta cuando un usuario inicia sesión"""
        user_id = event_data.get('user_id')
        
        # Registrar actividad del usuario
        self.track_user_activity(user_id)
        
        return f"User activity tracked: {user_id}"
    
    def on_data_processed(self, event_data):
        """Evento que se ejecuta cuando se procesan datos"""
        data_type = event_data.get('data_type')
        records_count = event_data.get('records_count', 0)
        
        # Registrar procesamiento de datos
        self.log_data_processing(data_type, records_count)
        
        return f"Data processing logged: {data_type}"
    
    def on_insight_generated(self, event_data):
        """Evento que se ejecuta cuando se genera un insight"""
        insight_id = event_data.get('insight_id')
        insight_type = event_data.get('insight_type')
        confidence = event_data.get('confidence', 0)
        
        # Registrar generación de insight
        self.log_insight_generation(insight_id, insight_type, confidence)
        
        return f"Insight generation logged: {insight_type}"
    
    def on_install(self):
        """Código que se ejecuta al instalar el plugin"""
        # Crear tablas para analytics
        self.create_analytics_tables()
        
        # Configurar procesamiento de datos
        self.setup_data_processing()
        
        # Inicializar modelos de ML
        self.initialize_ml_models()
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar el plugin"""
        # Limpiar tablas de analytics
        self.cleanup_analytics_tables()
        
        # Limpiar modelos de ML
        self.cleanup_ml_models()
    
    def on_activate(self):
        """Código que se ejecuta al activar el plugin"""
        # Iniciar procesamiento en tiempo real
        if self.config.get('enable_real_time_analytics'):
            self.start_real_time_processing()
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar el plugin"""
        # Detener procesamiento en tiempo real
        self.stop_real_time_processing()
    
    # Funciones auxiliares (simuladas)
    def process_sale_data(self, sale_id, details):
        """Procesa datos de venta"""
        print(f"Processing sale data for sale {sale_id}")
    
    def generate_sales_insights(self, sale_id, details):
        """Genera insights de ventas"""
        print(f"Generating sales insights for sale {sale_id}")
    
    def process_purchase_data(self, purchase_id, details):
        """Procesa datos de compra"""
        print(f"Processing purchase data for purchase {purchase_id}")
    
    def process_inventory_data(self, product_id, quantity, action):
        """Procesa datos de inventario"""
        print(f"Processing inventory data for product {product_id}")
    
    def track_user_activity(self, user_id):
        """Registra actividad del usuario"""
        print(f"Tracking user activity for user {user_id}")
    
    def log_data_processing(self, data_type, records_count):
        """Registra procesamiento de datos"""
        print(f"Logging data processing: {data_type} - {records_count} records")
    
    def log_insight_generation(self, insight_id, insight_type, confidence):
        """Registra generación de insight"""
        print(f"Logging insight generation: {insight_type} - {confidence}")
    
    def create_analytics_tables(self):
        """Crea tablas para analytics"""
        print("Creating analytics tables")
    
    def setup_data_processing(self):
        """Configura procesamiento de datos"""
        print("Setting up data processing")
    
    def initialize_ml_models(self):
        """Inicializa modelos de ML"""
        print("Initializing ML models")
    
    def cleanup_analytics_tables(self):
        """Limpia tablas de analytics"""
        print("Cleaning up analytics tables")
    
    def cleanup_ml_models(self):
        """Limpia modelos de ML"""
        print("Cleaning up ML models")
    
    def start_real_time_processing(self):
        """Inicia procesamiento en tiempo real"""
        print("Starting real-time processing")
    
    def stop_real_time_processing(self):
        """Detiene procesamiento en tiempo real"""
        print("Stopping real-time processing")


# ============================================================================
# FUNCIÓN PARA REGISTRAR TODOS LOS EJEMPLOS
# ============================================================================

def register_plugin_examples():
    """Registra todos los ejemplos de plugins"""
    from core.plugin_manager import plugin_manager
    
    # Crear instancias de plugins
    email_integration = EmailIntegrationPlugin()
    data_analytics = DataAnalyticsPlugin()
    
    # Registrar plugins
    plugin_manager.register_plugin(email_integration)
    plugin_manager.register_plugin(data_analytics)
    
    print("Plugin examples registered successfully")


def unregister_plugin_examples():
    """Desregistra todos los ejemplos de plugins"""
    from core.plugin_manager import plugin_manager
    
    # Lista de plugins a desregistrar
    plugins_to_remove = ['email_integration', 'data_analytics']
    
    for plugin_name in plugins_to_remove:
        plugin_manager.cleanup_plugin(plugin_name)
    
    print("Plugin examples unregistered successfully")


def test_plugin_system():
    """Prueba el sistema de plugins"""
    from core.plugin_manager import plugin_manager
    
    # Registrar ejemplos
    register_plugin_examples()
    
    # Obtener información de plugins
    plugins_summary = plugin_manager.get_plugins_summary()
    print(f"Total plugins: {plugins_summary['total_plugins']}")
    
    # Probar instalación de un plugin
    if plugin_manager.install_plugin('email_integration'):
        print("Email Integration plugin installed successfully")
        
        # Probar activación
        if plugin_manager.activate_plugin('email_integration'):
            print("Email Integration plugin activated successfully")
            
            # Probar desactivación
            if plugin_manager.deactivate_plugin('email_integration'):
                print("Email Integration plugin deactivated successfully")
            
            # Probar desinstalación
            if plugin_manager.uninstall_plugin('email_integration'):
                print("Email Integration plugin uninstalled successfully")
    
    print("Plugin system test completed")


if __name__ == "__main__":
    # Probar sistema de plugins
    test_plugin_system() 