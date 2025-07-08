"""
Ejemplos de extensiones para el sistema Synap
Demuestra cómo crear extensiones que agregan funcionalidad a módulos existentes
"""

from core.extension_manager import ExtensionBase


# ============================================================================
# EXTENSIÓN PARA VENTAS - CUPONES Y DESCUENTOS
# ============================================================================

class SalesCouponsExtension(ExtensionBase):
    """Extensión que agrega sistema de cupones y descuentos al módulo de ventas"""
    
    name = 'sales_coupons'
    version = '1.0.0'
    description = 'Extensión que agrega sistema de cupones y descuentos a las ventas'
    author = 'Synap Team'
    target_module = 'sales'
    
    # Modelos que extiende
    extends_models = [
        'SaleOrder',
        'SaleOrderLine'
    ]
    
    # Vistas que extiende
    extends_views = [
        'SaleOrderCreateView',
        'SaleOrderDetailView',
        'SaleOrderListView'
    ]
    
    # Templates que extiende
    extends_templates = [
        'sales/orders/order_form.html',
        'sales/orders/order_detail.html',
        'sales/orders/order_list.html'
    ]
    
    # Formularios que extiende
    extends_forms = [
        'SaleOrderForm',
        'SaleOrderLineForm'
    ]
    
    # Admin que extiende
    extends_admin = [
        'SaleOrderAdmin',
        'SaleOrderLineAdmin'
    ]
    
    # Configuración por defecto
    default_config = {
        'enable_coupons': True,
        'enable_discounts': True,
        'max_discount_percent': 50,
        'coupon_expiry_days': 30,
        'auto_apply_coupons': False
    }
    
    def extend_models(self):
        """Extiende modelos del módulo de ventas"""
        # Agregar campos a SaleOrder
        self.add_coupon_fields_to_sale_order()
        
        # Agregar campos a SaleOrderLine
        self.add_discount_fields_to_sale_order_line()
        
        # Crear modelo de cupones
        self.create_coupon_model()
    
    def extend_views(self):
        """Extiende vistas del módulo de ventas"""
        # Agregar funcionalidad de cupones a vistas de ventas
        self.add_coupon_functionality_to_views()
        
        # Agregar vistas de gestión de cupones
        self.add_coupon_management_views()
    
    def extend_templates(self):
        """Extiende templates del módulo de ventas"""
        # Agregar sección de cupones a formularios
        self.add_coupon_section_to_templates()
        
        # Agregar sección de descuentos a detalles
        self.add_discount_section_to_templates()
    
    def extend_forms(self):
        """Extiende formularios del módulo de ventas"""
        # Agregar campos de cupones a formularios
        self.add_coupon_fields_to_forms()
        
        # Agregar validación de cupones
        self.add_coupon_validation()
    
    def extend_admin(self):
        """Extiende admin del módulo de ventas"""
        # Agregar campos de cupones al admin
        self.add_coupon_fields_to_admin()
        
        # Agregar filtros de cupones
        self.add_coupon_filters_to_admin()
    
    def revert_models(self):
        """Revierte extensiones de modelos"""
        # Remover campos agregados
        self.remove_coupon_fields()
        
        # Eliminar modelo de cupones
        self.drop_coupon_model()
    
    def revert_views(self):
        """Revierte extensiones de vistas"""
        # Remover funcionalidad de cupones
        self.remove_coupon_functionality()
    
    def revert_templates(self):
        """Revierte extensiones de templates"""
        # Remover secciones de cupones
        self.remove_coupon_sections()
    
    def revert_forms(self):
        """Revierte extensiones de formularios"""
        # Remover campos de cupones
        self.remove_coupon_form_fields()
    
    def revert_admin(self):
        """Revierte extensiones de admin"""
        # Remover campos del admin
        self.remove_coupon_admin_fields()
    
    def on_install(self):
        """Código que se ejecuta al instalar la extensión"""
        # Crear tablas para cupones
        self.create_coupon_tables()
        
        # Crear cupones por defecto
        self.create_default_coupons()
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar la extensión"""
        # Limpiar datos de cupones
        self.cleanup_coupon_data()
    
    def on_activate(self):
        """Código que se ejecuta al activar la extensión"""
        # Habilitar funcionalidad de cupones
        self.enable_coupon_functionality()
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar la extensión"""
        # Deshabilitar funcionalidad de cupones
        self.disable_coupon_functionality()
    
    # Funciones auxiliares (simuladas)
    def add_coupon_fields_to_sale_order(self):
        """Agrega campos de cupones a SaleOrder"""
        print("Adding coupon fields to SaleOrder model")
    
    def add_discount_fields_to_sale_order_line(self):
        """Agrega campos de descuentos a SaleOrderLine"""
        print("Adding discount fields to SaleOrderLine model")
    
    def create_coupon_model(self):
        """Crea modelo de cupones"""
        print("Creating Coupon model")
    
    def add_coupon_functionality_to_views(self):
        """Agrega funcionalidad de cupones a vistas"""
        print("Adding coupon functionality to sales views")
    
    def add_coupon_management_views(self):
        """Agrega vistas de gestión de cupones"""
        print("Adding coupon management views")
    
    def add_coupon_section_to_templates(self):
        """Agrega sección de cupones a templates"""
        print("Adding coupon section to sales templates")
    
    def add_discount_section_to_templates(self):
        """Agrega sección de descuentos a templates"""
        print("Adding discount section to sales templates")
    
    def add_coupon_fields_to_forms(self):
        """Agrega campos de cupones a formularios"""
        print("Adding coupon fields to sales forms")
    
    def add_coupon_validation(self):
        """Agrega validación de cupones"""
        print("Adding coupon validation to forms")
    
    def add_coupon_fields_to_admin(self):
        """Agrega campos de cupones al admin"""
        print("Adding coupon fields to sales admin")
    
    def add_coupon_filters_to_admin(self):
        """Agrega filtros de cupones al admin"""
        print("Adding coupon filters to sales admin")
    
    def remove_coupon_fields(self):
        """Remueve campos de cupones"""
        print("Removing coupon fields from models")
    
    def drop_coupon_model(self):
        """Elimina modelo de cupones"""
        print("Dropping Coupon model")
    
    def remove_coupon_functionality(self):
        """Remueve funcionalidad de cupones"""
        print("Removing coupon functionality from views")
    
    def remove_coupon_sections(self):
        """Remueve secciones de cupones"""
        print("Removing coupon sections from templates")
    
    def remove_coupon_form_fields(self):
        """Remueve campos de cupones de formularios"""
        print("Removing coupon fields from forms")
    
    def remove_coupon_admin_fields(self):
        """Remueve campos de cupones del admin"""
        print("Removing coupon fields from admin")
    
    def create_coupon_tables(self):
        """Crea tablas para cupones"""
        print("Creating coupon tables")
    
    def create_default_coupons(self):
        """Crea cupones por defecto"""
        print("Creating default coupons")
    
    def cleanup_coupon_data(self):
        """Limpia datos de cupones"""
        print("Cleaning up coupon data")
    
    def enable_coupon_functionality(self):
        """Habilita funcionalidad de cupones"""
        print("Enabling coupon functionality")
    
    def disable_coupon_functionality(self):
        """Deshabilita funcionalidad de cupones"""
        print("Disabling coupon functionality")


# ============================================================================
# EXTENSIÓN PARA INVENTARIO - CÓDIGOS DE BARRAS
# ============================================================================

class InventoryBarcodeExtension(ExtensionBase):
    """Extensión que agrega sistema de códigos de barras al módulo de inventario"""
    
    name = 'inventory_barcode'
    version = '1.0.0'
    description = 'Extensión que agrega sistema de códigos de barras al inventario'
    author = 'Synap Team'
    target_module = 'inventory'
    
    # Modelos que extiende
    extends_models = [
        'Product',
        'ProductVariant',
        'Location'
    ]
    
    # Vistas que extiende
    extends_views = [
        'ProductCreateView',
        'ProductDetailView',
        'ProductListView',
        'LocationCreateView'
    ]
    
    # Templates que extiende
    extends_templates = [
        'inventory/products/product_form.html',
        'inventory/products/product_detail.html',
        'inventory/products/product_list.html',
        'inventory/locations/location_form.html'
    ]
    
    # Formularios que extiende
    extends_forms = [
        'ProductForm',
        'ProductVariantForm',
        'LocationForm'
    ]
    
    # Admin que extiende
    extends_admin = [
        'ProductAdmin',
        'ProductVariantAdmin',
        'LocationAdmin'
    ]
    
    # Configuración por defecto
    default_config = {
        'enable_barcode_generation': True,
        'barcode_format': 'EAN13',
        'auto_generate_barcodes': True,
        'enable_barcode_scanning': True,
        'barcode_prefix': 'SYN'
    }
    
    def extend_models(self):
        """Extiende modelos del módulo de inventario"""
        # Agregar campos de código de barras a Product
        self.add_barcode_fields_to_product()
        
        # Agregar campos de código de barras a ProductVariant
        self.add_barcode_fields_to_product_variant()
        
        # Agregar campos de código de barras a Location
        self.add_barcode_fields_to_location()
        
        # Crear modelo de códigos de barras
        self.create_barcode_model()
    
    def extend_views(self):
        """Extiende vistas del módulo de inventario"""
        # Agregar funcionalidad de códigos de barras a vistas
        self.add_barcode_functionality_to_views()
        
        # Agregar vistas de gestión de códigos de barras
        self.add_barcode_management_views()
    
    def extend_templates(self):
        """Extiende templates del módulo de inventario"""
        # Agregar sección de códigos de barras a formularios
        self.add_barcode_section_to_templates()
        
        # Agregar visualización de códigos de barras
        self.add_barcode_display_to_templates()
    
    def extend_forms(self):
        """Extiende formularios del módulo de inventario"""
        # Agregar campos de códigos de barras a formularios
        self.add_barcode_fields_to_forms()
        
        # Agregar validación de códigos de barras
        self.add_barcode_validation()
    
    def extend_admin(self):
        """Extiende admin del módulo de inventario"""
        # Agregar campos de códigos de barras al admin
        self.add_barcode_fields_to_admin()
        
        # Agregar filtros de códigos de barras
        self.add_barcode_filters_to_admin()
    
    def revert_models(self):
        """Revierte extensiones de modelos"""
        # Remover campos agregados
        self.remove_barcode_fields()
        
        # Eliminar modelo de códigos de barras
        self.drop_barcode_model()
    
    def revert_views(self):
        """Revierte extensiones de vistas"""
        # Remover funcionalidad de códigos de barras
        self.remove_barcode_functionality()
    
    def revert_templates(self):
        """Revierte extensiones de templates"""
        # Remover secciones de códigos de barras
        self.remove_barcode_sections()
    
    def revert_forms(self):
        """Revierte extensiones de formularios"""
        # Remover campos de códigos de barras
        self.remove_barcode_form_fields()
    
    def revert_admin(self):
        """Revierte extensiones de admin"""
        # Remover campos del admin
        self.remove_barcode_admin_fields()
    
    def on_install(self):
        """Código que se ejecuta al instalar la extensión"""
        # Crear tablas para códigos de barras
        self.create_barcode_tables()
        
        # Generar códigos de barras para productos existentes
        self.generate_barcodes_for_existing_products()
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar la extensión"""
        # Limpiar datos de códigos de barras
        self.cleanup_barcode_data()
    
    def on_activate(self):
        """Código que se ejecuta al activar la extensión"""
        # Habilitar funcionalidad de códigos de barras
        self.enable_barcode_functionality()
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar la extensión"""
        # Deshabilitar funcionalidad de códigos de barras
        self.disable_barcode_functionality()
    
    # Funciones auxiliares (simuladas)
    def add_barcode_fields_to_product(self):
        """Agrega campos de código de barras a Product"""
        print("Adding barcode fields to Product model")
    
    def add_barcode_fields_to_product_variant(self):
        """Agrega campos de código de barras a ProductVariant"""
        print("Adding barcode fields to ProductVariant model")
    
    def add_barcode_fields_to_location(self):
        """Agrega campos de código de barras a Location"""
        print("Adding barcode fields to Location model")
    
    def create_barcode_model(self):
        """Crea modelo de códigos de barras"""
        print("Creating Barcode model")
    
    def add_barcode_functionality_to_views(self):
        """Agrega funcionalidad de códigos de barras a vistas"""
        print("Adding barcode functionality to inventory views")
    
    def add_barcode_management_views(self):
        """Agrega vistas de gestión de códigos de barras"""
        print("Adding barcode management views")
    
    def add_barcode_section_to_templates(self):
        """Agrega sección de códigos de barras a templates"""
        print("Adding barcode section to inventory templates")
    
    def add_barcode_display_to_templates(self):
        """Agrega visualización de códigos de barras a templates"""
        print("Adding barcode display to inventory templates")
    
    def add_barcode_fields_to_forms(self):
        """Agrega campos de códigos de barras a formularios"""
        print("Adding barcode fields to inventory forms")
    
    def add_barcode_validation(self):
        """Agrega validación de códigos de barras"""
        print("Adding barcode validation to forms")
    
    def add_barcode_fields_to_admin(self):
        """Agrega campos de códigos de barras al admin"""
        print("Adding barcode fields to inventory admin")
    
    def add_barcode_filters_to_admin(self):
        """Agrega filtros de códigos de barras al admin"""
        print("Adding barcode filters to inventory admin")
    
    def remove_barcode_fields(self):
        """Remueve campos de códigos de barras"""
        print("Removing barcode fields from models")
    
    def drop_barcode_model(self):
        """Elimina modelo de códigos de barras"""
        print("Dropping Barcode model")
    
    def remove_barcode_functionality(self):
        """Remueve funcionalidad de códigos de barras"""
        print("Removing barcode functionality from views")
    
    def remove_barcode_sections(self):
        """Remueve secciones de códigos de barras"""
        print("Removing barcode sections from templates")
    
    def remove_barcode_form_fields(self):
        """Remueve campos de códigos de barras de formularios"""
        print("Removing barcode fields from forms")
    
    def remove_barcode_admin_fields(self):
        """Remueve campos de códigos de barras del admin"""
        print("Removing barcode fields from admin")
    
    def create_barcode_tables(self):
        """Crea tablas para códigos de barras"""
        print("Creating barcode tables")
    
    def generate_barcodes_for_existing_products(self):
        """Genera códigos de barras para productos existentes"""
        print("Generating barcodes for existing products")
    
    def cleanup_barcode_data(self):
        """Limpia datos de códigos de barras"""
        print("Cleaning up barcode data")
    
    def enable_barcode_functionality(self):
        """Habilita funcionalidad de códigos de barras"""
        print("Enabling barcode functionality")
    
    def disable_barcode_functionality(self):
        """Deshabilita funcionalidad de códigos de barras"""
        print("Disabling barcode functionality")


# ============================================================================
# EXTENSIÓN PARA COMPRAS - APROBACIONES MULTINIVEL
# ============================================================================

class PurchasesMultiLevelApprovalExtension(ExtensionBase):
    """Extensión que agrega sistema de aprobaciones multinivel al módulo de compras"""
    
    name = 'purchases_multi_approval'
    version = '1.0.0'
    description = 'Extensión que agrega sistema de aprobaciones multinivel a las compras'
    author = 'Synap Team'
    target_module = 'purchases'
    
    # Modelos que extiende
    extends_models = [
        'PurchaseOrder',
        'PurchaseRequest'
    ]
    
    # Vistas que extiende
    extends_views = [
        'PurchaseOrderCreateView',
        'PurchaseOrderDetailView',
        'PurchaseRequestCreateView',
        'PurchaseRequestDetailView'
    ]
    
    # Templates que extiende
    extends_templates = [
        'purchases/orders/order_form.html',
        'purchases/orders/order_detail.html',
        'purchases/requests/request_form.html',
        'purchases/requests/request_detail.html'
    ]
    
    # Formularios que extiende
    extends_forms = [
        'PurchaseOrderForm',
        'PurchaseRequestForm'
    ]
    
    # Admin que extiende
    extends_admin = [
        'PurchaseOrderAdmin',
        'PurchaseRequestAdmin'
    ]
    
    # Configuración por defecto
    default_config = {
        'enable_multi_level_approval': True,
        'max_approval_levels': 3,
        'auto_assign_approvers': True,
        'require_all_levels': True,
        'enable_escalation': True
    }
    
    def extend_models(self):
        """Extiende modelos del módulo de compras"""
        # Agrega campos de aprobación a PurchaseOrder
        self.add_approval_fields_to_purchase_order()
        
        # Agrega campos de aprobación a PurchaseRequest
        self.add_approval_fields_to_purchase_request()
        
        # Crear modelo de niveles de aprobación
        self.create_approval_level_model()
    
    def extend_views(self):
        """Extiende vistas del módulo de compras"""
        # Agregar funcionalidad de aprobaciones a vistas
        self.add_approval_functionality_to_views()
        
        # Agregar vistas de gestión de aprobaciones
        self.add_approval_management_views()
    
    def extend_templates(self):
        """Extiende templates del módulo de compras"""
        # Agregar sección de aprobaciones a formularios
        self.add_approval_section_to_templates()
        
        # Agregar flujo de aprobación a detalles
        self.add_approval_flow_to_templates()
    
    def extend_forms(self):
        """Extiende formularios del módulo de compras"""
        # Agregar campos de aprobación a formularios
        self.add_approval_fields_to_forms()
        
        # Agregar validación de aprobaciones
        self.add_approval_validation()
    
    def extend_admin(self):
        """Extiende admin del módulo de compras"""
        # Agregar campos de aprobación al admin
        self.add_approval_fields_to_admin()
        
        # Agregar filtros de aprobación
        self.add_approval_filters_to_admin()
    
    def revert_models(self):
        """Revierte extensiones de modelos"""
        # Remover campos agregados
        self.remove_approval_fields()
        
        # Eliminar modelo de niveles de aprobación
        self.drop_approval_level_model()
    
    def revert_views(self):
        """Revierte extensiones de vistas"""
        # Remover funcionalidad de aprobaciones
        self.remove_approval_functionality()
    
    def revert_templates(self):
        """Revierte extensiones de templates"""
        # Remover secciones de aprobaciones
        self.remove_approval_sections()
    
    def revert_forms(self):
        """Revierte extensiones de formularios"""
        # Remover campos de aprobación
        self.remove_approval_form_fields()
    
    def revert_admin(self):
        """Revierte extensiones de admin"""
        # Remover campos del admin
        self.remove_approval_admin_fields()
    
    def on_install(self):
        """Código que se ejecuta al instalar la extensión"""
        # Crear tablas para aprobaciones
        self.create_approval_tables()
        
        # Crear niveles de aprobación por defecto
        self.create_default_approval_levels()
    
    def on_uninstall(self):
        """Código que se ejecuta al desinstalar la extensión"""
        # Limpiar datos de aprobaciones
        self.cleanup_approval_data()
    
    def on_activate(self):
        """Código que se ejecuta al activar la extensión"""
        # Habilitar funcionalidad de aprobaciones
        self.enable_approval_functionality()
    
    def on_deactivate(self):
        """Código que se ejecuta al desactivar la extensión"""
        # Deshabilitar funcionalidad de aprobaciones
        self.disable_approval_functionality()
    
    # Funciones auxiliares (simuladas)
    def add_approval_fields_to_purchase_order(self):
        """Agrega campos de aprobación a PurchaseOrder"""
        print("Adding approval fields to PurchaseOrder model")
    
    def add_approval_fields_to_purchase_request(self):
        """Agrega campos de aprobación a PurchaseRequest"""
        print("Adding approval fields to PurchaseRequest model")
    
    def create_approval_level_model(self):
        """Crea modelo de niveles de aprobación"""
        print("Creating ApprovalLevel model")
    
    def add_approval_functionality_to_views(self):
        """Agrega funcionalidad de aprobaciones a vistas"""
        print("Adding approval functionality to purchase views")
    
    def add_approval_management_views(self):
        """Agrega vistas de gestión de aprobaciones"""
        print("Adding approval management views")
    
    def add_approval_section_to_templates(self):
        """Agrega sección de aprobaciones a templates"""
        print("Adding approval section to purchase templates")
    
    def add_approval_flow_to_templates(self):
        """Agrega flujo de aprobación a templates"""
        print("Adding approval flow to purchase templates")
    
    def add_approval_fields_to_forms(self):
        """Agrega campos de aprobación a formularios"""
        print("Adding approval fields to purchase forms")
    
    def add_approval_validation(self):
        """Agrega validación de aprobaciones"""
        print("Adding approval validation to forms")
    
    def add_approval_fields_to_admin(self):
        """Agrega campos de aprobación al admin"""
        print("Adding approval fields to purchase admin")
    
    def add_approval_filters_to_admin(self):
        """Agrega filtros de aprobación al admin"""
        print("Adding approval filters to purchase admin")
    
    def remove_approval_fields(self):
        """Remueve campos de aprobación"""
        print("Removing approval fields from models")
    
    def drop_approval_level_model(self):
        """Elimina modelo de niveles de aprobación"""
        print("Dropping ApprovalLevel model")
    
    def remove_approval_functionality(self):
        """Remueve funcionalidad de aprobaciones"""
        print("Removing approval functionality from views")
    
    def remove_approval_sections(self):
        """Remueve secciones de aprobaciones"""
        print("Removing approval sections from templates")
    
    def remove_approval_form_fields(self):
        """Remueve campos de aprobación de formularios"""
        print("Removing approval fields from forms")
    
    def remove_approval_admin_fields(self):
        """Remueve campos de aprobación del admin"""
        print("Removing approval fields from admin")
    
    def create_approval_tables(self):
        """Crea tablas para aprobaciones"""
        print("Creating approval tables")
    
    def create_default_approval_levels(self):
        """Crea niveles de aprobación por defecto"""
        print("Creating default approval levels")
    
    def cleanup_approval_data(self):
        """Limpia datos de aprobaciones"""
        print("Cleaning up approval data")
    
    def enable_approval_functionality(self):
        """Habilita funcionalidad de aprobaciones"""
        print("Enabling approval functionality")
    
    def disable_approval_functionality(self):
        """Deshabilita funcionalidad de aprobaciones"""
        print("Disabling approval functionality")


# ============================================================================
# FUNCIÓN PARA REGISTRAR TODOS LOS EJEMPLOS
# ============================================================================

def register_extension_examples():
    """Registra todos los ejemplos de extensiones"""
    from core.extension_manager import extension_manager
    
    # Crear instancias de extensiones
    sales_coupons = SalesCouponsExtension()
    inventory_barcode = InventoryBarcodeExtension()
    purchases_approval = PurchasesMultiLevelApprovalExtension()
    
    # Registrar extensiones
    extension_manager.register_extension(sales_coupons)
    extension_manager.register_extension(inventory_barcode)
    extension_manager.register_extension(purchases_approval)
    
    print("Extension examples registered successfully")


def unregister_extension_examples():
    """Desregistra todos los ejemplos de extensiones"""
    from core.extension_manager import extension_manager
    
    # Lista de extensiones a desregistrar
    extensions_to_remove = ['sales_coupons', 'inventory_barcode', 'purchases_multi_approval']
    
    for extension_name in extensions_to_remove:
        extension_manager.cleanup_extension(extension_name)
    
    print("Extension examples unregistered successfully")


def test_extension_system():
    """Prueba el sistema de extensiones"""
    from core.extension_manager import extension_manager
    
    # Registrar ejemplos
    register_extension_examples()
    
    # Obtener información de extensiones
    extensions_summary = extension_manager.get_extensions_summary()
    print(f"Total extensions: {extensions_summary['total_extensions']}")
    
    # Probar instalación de una extensión
    if extension_manager.install_extension('sales_coupons'):
        print("Sales Coupons extension installed successfully")
        
        # Probar activación
        if extension_manager.activate_extension('sales_coupons'):
            print("Sales Coupons extension activated successfully")
            
            # Probar desactivación
            if extension_manager.deactivate_extension('sales_coupons'):
                print("Sales Coupons extension deactivated successfully")
            
            # Probar desinstalación
            if extension_manager.uninstall_extension('sales_coupons'):
                print("Sales Coupons extension uninstalled successfully")
    
    print("Extension system test completed")


if __name__ == "__main__":
    # Probar sistema de extensiones
    test_extension_system() 