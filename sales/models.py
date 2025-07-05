from django.db import models
from django.conf import settings

# --- CLIENTES Y CONTACTOS ---
class Client(models.Model):
    """Cliente: empresa o persona física"""
    name = models.CharField(max_length=255)
    vat = models.CharField(max_length=32, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    type = models.CharField(max_length=16, choices=[('company', 'Company'), ('person', 'Person')])
    origin = models.CharField(max_length=32, blank=True, null=True)
    tiendanube_customer_id = models.CharField(max_length=64, blank=True, null=True)
    from_ecommerce = models.BooleanField(default=False)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Contact(models.Model):
    """Contacto de cliente"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.client.name})"

# --- LISTAS DE PRECIOS ---
class PriceList(models.Model):
    name = models.CharField(max_length=128)
    currency = models.CharField(max_length=8)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    min_qty = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    max_qty = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    promo_code = models.CharField(max_length=32, blank=True, null=True)
    rule_type = models.CharField(max_length=32, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)

# --- CONDICIONES DE PAGO ---
class PaymentTerm(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PaymentTermLine(models.Model):
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.CASCADE, related_name='lines')
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    days = models.IntegerField()
    sequence = models.IntegerField(default=1)

# --- SALES ORDER Y LÍNEAS ---
class SalesOrder(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    order_date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='orders')
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)
    price_list = models.ForeignKey(PriceList, on_delete=models.PROTECT)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    manual_credit_override = models.BooleanField(default=False)
    credit_override_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.number

class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=32)

# --- INVOICES Y LÍNEAS ---
class Invoice(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    invoice_date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    invoice_type = models.CharField(max_length=16)

    def __str__(self):
        return self.number

class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

# --- PAGOS ---
class Payment(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, blank=True, null=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, blank=True, null=True)
    payment_method = models.CharField(max_length=32)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)

# --- DELIVERY ORDERS ---
class DeliveryOrder(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    delivery_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)

class DeliveryOrderLine(models.Model):
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.CharField(max_length=32)

# --- CREDIT NOTES ---
class CreditNote(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    credit_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    reason = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)

# --- APROBACIONES ---
class ApprovalLog(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    reason = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(auto_now_add=True)

# --- DEVOLUCIONES ---
class ReturnDelivery(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    return_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.PROTECT)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    return_type = models.CharField(max_length=32)
    reason = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
