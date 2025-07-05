# 🏛️ Sistema de Impuestos en Synap - Implementación Completa

## 📋 **Resumen Ejecutivo**

Se ha implementado un **sistema de impuestos modular, jerárquico y altamente configurable** en Synap, adaptado para contextos internacionales y con integración completa con contabilidad. El sistema soporta IVA, impuestos internos, percepciones/retenciones y cálculos personalizados.

---

## 🏗️ **Arquitectura del Sistema**

### **1. Módulo de Contabilidad (`accounting/`)**
```
accounting/
├── models.py              # Modelos de contabilidad e impuestos
├── services.py            # Servicios de cálculo fiscal
├── apps.py               # Configuración de la app
├── management/
│   └── commands/
│       └── setup_accounting.py  # Comando de configuración inicial
└── __init__.py
```

### **2. Integración con Módulos Existentes**
- **`inventory/models.py`**: Extendido con campos de impuestos en productos
- **`sales/models.py`**: Extendido con campos de impuestos en líneas de venta
- **`sales/services.py`**: Integración con cálculo de impuestos

---

## 📊 **Modelos Implementados**

### **Contabilidad Base**
```python
# Plan de cuentas contables
ChartOfAccounts
├── empresa (FK)
├── code, name
├── account_type (assets, liabilities, equity, income, expenses)
├── is_tax_account, tax_type
└── parent (self-referencing)

# Diarios contables
Journal
├── empresa (FK)
├── code, name, journal_type
├── default_account (FK)
└── tax_account (FK)

# Asientos contables
JournalEntry
├── empresa, journal (FK)
├── number, date, reference
├── state (draft, posted, cancelled)
├── origin_model, origin_id (para integración)
└── created_by, posted_by (auditoría)

JournalEntryLine
├── entry, account (FK)
├── partner (FK)
├── debit, credit, amount_currency
├── tax_line (FK)
└── name (descripción)
```

### **Sistema de Impuestos**
```python
# Grupos de impuestos
TaxGroup
├── empresa (FK)
├── name, code, description
├── account_id (cuenta ventas)
└── refund_account_id (cuenta compras)

# Impuestos individuales
Tax
├── empresa, tax_group (FK)
├── name, code, amount, amount_type
├── price_include, include_base_amount
├── account_id, refund_account_id (FK)
├── python_compute, python_applicable
└── sequence, is_active

# Líneas de impuesto
TaxLine
├── tax (FK)
├── base_amount, tax_amount, total_amount
├── origin_model, origin_id, origin_line_id
└── created_at

# Posiciones fiscales
FiscalPosition
├── empresa (FK)
├── name, code, description
├── country_id, state_id, zip_from, zip_to
└── tax_ids (M2M through FiscalPositionTax)

FiscalPositionTax
├── fiscal_position (FK)
├── tax_src_id, tax_dest_id (FK)
└── unique_together (fiscal_position, tax_src_id)
```

---

## 🔧 **Servicios Implementados**

### **1. TaxCalculationService**
```python
class TaxCalculationService:
    def __init__(self, empresa, partner=None, fiscal_position=None)
    
    # Métodos principales
    def get_applicable_taxes(self, product=None, date=None)
    def calculate_taxes(self, base_amount, product=None, quantity=1, price_unit=None)
    def calculate_line_taxes(self, line, save_tax_lines=True)
    def calculate_document_taxes(self, document)
```

**Características:**
- ✅ Cálculo automático de impuestos por línea
- ✅ Soporte para impuestos en cascada
- ✅ Aplicación de posiciones fiscales
- ✅ Código Python personalizado para cálculos complejos
- ✅ Validación de aplicabilidad por fecha/producto/partner

### **2. TaxReportingService**
```python
class TaxReportingService:
    def get_tax_summary(self, start_date, end_date, tax_group=None)
    def get_tax_by_origin(self, start_date, end_date, origin_model=None)
```

### **3. TaxValidationService**
```python
class TaxValidationService:
    def validate_tax_configuration(self)
    def validate_tax_calculation(self, base_amount, taxes, expected_total)
```

### **4. SalesTaxService**
```python
class SalesTaxService:
    def calculate_order_taxes(self, order)
    def calculate_invoice_taxes(self, invoice)
    def create_invoice_from_order(self, order, user)
    def _create_accounting_entry(self, invoice, tax_lines, user)
```

---

## 🎯 **Tipos de Impuestos Soportados**

### **1. Porcentual (`percent`)**
```python
# Ejemplo: IVA 21%
tax = Tax.objects.create(
    name="IVA 21%",
    amount=Decimal('21.00'),
    amount_type='percent',
    tax_group=iva_group
)
```

### **2. Monto Fijo (`fixed`)**
```python
# Ejemplo: Impuesto fijo por unidad
tax = Tax.objects.create(
    name="Impuesto Especial",
    amount=Decimal('5.00'),
    amount_type='fixed',
    tax_group=especial_group
)
```

### **3. Grupo de Impuestos (`group`)**
```python
# Ejemplo: IVA + Internos
tax = Tax.objects.create(
    name="IVA + Internos",
    amount_type='group',
    tax_group=combinado_group
)
```

### **4. Código Python (`code`)**
```python
# Ejemplo: Cálculo personalizado
tax = Tax.objects.create(
    name="Impuesto al Cheque",
    amount_type='code',
    python_compute="""
    if base_amount > 1000:
        result = base_amount * 0.006
    else:
        result = 0
    """,
    tax_group=especial_group
)
```

---

## 🇦🇷 **Configuración para Argentina**

### **Impuestos Básicos Configurados**
```python
# IVA
IVA21 = Tax(code='IVA21', name='IVA 21%', amount=21.00)
IVA10.5 = Tax(code='IVA10.5', name='IVA 10.5%', amount=10.50)
IVA27 = Tax(code='IVA27', name='IVA 27%', amount=27.00)
IVA0 = Tax(code='IVA0', name='IVA 0%', amount=0.00)

# Impuestos Internos
IIBB = Tax(code='IIBB', name='Impuestos Internos', amount=3.00)
```

### **Plan de Cuentas Argentino**
```python
# Cuentas de impuestos
2210 = ChartOfAccounts(code='2210', name='IVA Ventas', is_tax_account=True)
2220 = ChartOfAccounts(code='2220', name='IVA Compras', is_tax_account=True)
2230 = ChartOfAccounts(code='2230', name='Impuestos Internos', is_tax_account=True)
2240 = ChartOfAccounts(code='2240', name='Percepciones', is_tax_account=True)
```

### **Posiciones Fiscales**
```python
# Exportación
FiscalPosition(
    name="Exportación",
    country_id="AR",
    code="EXPORT"
)

# Consumidor Final
FiscalPosition(
    name="Consumidor Final",
    country_id="AR",
    code="CF"
)
```

---

## 🔄 **Flujo de Integración**

### **1. Creación de Pedido de Venta**
```python
# 1. Usuario crea pedido
order = SalesOrder.objects.create(...)

# 2. Usuario agrega líneas
line = SalesOrderLine.objects.create(
    sales_order=order,
    product_variant=product,
    quantity=2,
    unit_price=100
)

# 3. Sistema calcula impuestos automáticamente
tax_service = TaxCalculationService(empresa, partner=order.client)
tax_result = tax_service.calculate_line_taxes(line)

# 4. Se actualizan totales
line.tax_amount = tax_result['total_tax_amount']
line.save()
order.recalculate_totals()
```

### **2. Facturación Automática**
```python
# 1. Usuario confirma facturación
sales_service = SalesTaxService(empresa)
invoice = sales_service.create_invoice_from_order(order, user)

# 2. Sistema crea factura con impuestos
# 3. Sistema genera asiento contable automáticamente
# 4. Sistema actualiza totales
```

### **3. Asiento Contable Automático**
```python
# Ejemplo de asiento generado:
JournalEntry:
  - Línea 1: Debe Cuenta por Cobrar $242.00
  - Línea 2: Haber Ventas $200.00
  - Línea 3: Haber IVA Ventas $42.00
```

---

## 🛠️ **Comandos de Gestión**

### **Configuración Inicial**
```bash
# Configurar contabilidad para una empresa
python manage.py setup_accounting --empresa-nombre "Mi Empresa"

# Configurar contabilidad por ID
python manage.py setup_accounting --empresa-id 1
```

**Lo que crea automáticamente:**
- ✅ Plan de cuentas básico (activos, pasivos, patrimonio, ingresos, gastos)
- ✅ Diarios contables (ventas, compras, caja, banco, varios)
- ✅ Grupos de impuestos (IVA, Internos)
- ✅ Impuestos básicos (IVA 21%, 10.5%, 27%, 0%, IIBB)
- ✅ Cuentas específicas para impuestos

---

## 📈 **Reportes Disponibles**

### **1. Resumen de Impuestos por Período**
```python
reporting_service = TaxReportingService(empresa)
summary = reporting_service.get_tax_summary(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31)
)
```

### **2. Impuestos por Origen**
```python
by_origin = reporting_service.get_tax_by_origin(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31),
    origin_model='sales.Invoice'
)
```

### **3. Validación de Configuración**
```python
validation_service = TaxValidationService(empresa)
validation = validation_service.validate_tax_configuration()
```

---

## 🔧 **Configuración Avanzada**

### **1. Impuestos Personalizados con Python**
```python
# Impuesto progresivo
tax = Tax.objects.create(
    name="Impuesto Progresivo",
    amount_type='code',
    python_compute="""
    if base_amount <= 1000:
        result = base_amount * 0.05
    elif base_amount <= 5000:
        result = base_amount * 0.10
    else:
        result = base_amount * 0.15
    """,
    python_applicable="""
    # Solo aplicar a productos de lujo
    result = product and product.category.name == 'Lujo'
    """
)
```

### **2. Posiciones Fiscales por Región**
```python
# Buenos Aires
ba_position = FiscalPosition.objects.create(
    name="Buenos Aires",
    country_id="AR",
    state_id="BA",
    code="BA"
)

# Mapeo de impuestos
FiscalPositionTax.objects.create(
    fiscal_position=ba_position,
    tax_src_id=iva_21,
    tax_dest_id=iva_21_ba  # IVA con percepción BA
)
```

### **3. Impuestos por Categoría de Producto**
```python
# En el modelo Product
product.taxes.add(iva_21)  # IVA general
product.taxes.add(iibb)    # Internos

# En el servicio de cálculo
applicable_taxes = tax_service.get_applicable_taxes(product)
```

---

## 🚀 **Próximos Pasos de Implementación**

### **Fase 1: Configuración Básica**
1. ✅ Crear módulo de contabilidad
2. ✅ Implementar modelos de impuestos
3. ✅ Crear servicios de cálculo
4. ✅ Integrar con ventas
5. 🔄 Crear migraciones
6. 🔄 Configurar plan de cuentas inicial

### **Fase 2: Interfaz de Usuario**
1. 🔄 Crear vistas de administración de impuestos
2. 🔄 Integrar cálculo en formularios de venta
3. 🔄 Crear reportes de impuestos
4. 🔄 Implementar validaciones en frontend

### **Fase 3: Funcionalidades Avanzadas**
1. 🔄 Percepciones y retenciones automáticas
2. 🔄 Integración con AFIP
3. 🔄 Impuestos por jurisdicción
4. 🔄 Cálculos de crédito fiscal

---

## 📋 **Checklist de Implementación**

### **Configuración Inicial**
- [ ] Agregar `accounting` a `INSTALLED_APPS`
- [ ] Ejecutar `python manage.py makemigrations accounting`
- [ ] Ejecutar `python manage.py migrate`
- [ ] Ejecutar `python manage.py setup_accounting --empresa-id 1`

### **Integración con Ventas**
- [ ] Actualizar modelos de ventas con campos de impuestos
- [ ] Integrar cálculo automático en creación de pedidos
- [ ] Implementar facturación con impuestos
- [ ] Crear asientos contables automáticos

### **Configuración de Impuestos**
- [ ] Crear grupos de impuestos (IVA, Internos, etc.)
- [ ] Configurar impuestos básicos
- [ ] Definir posiciones fiscales
- [ ] Asignar impuestos a productos

### **Validación y Testing**
- [ ] Validar cálculos de impuestos
- [ ] Verificar asientos contables
- [ ] Probar reportes de impuestos
- [ ] Validar integración completa

---

## 🎯 **Beneficios del Sistema**

### **Para el Usuario Final**
- ✅ **Cálculo automático** de impuestos en tiempo real
- ✅ **Configuración flexible** para diferentes jurisdicciones
- ✅ **Reportes detallados** de obligaciones fiscales
- ✅ **Integración contable** automática

### **Para el Desarrollador**
- ✅ **Arquitectura modular** y extensible
- ✅ **Código Python personalizado** para casos complejos
- ✅ **API consistente** para cálculos fiscales
- ✅ **Validaciones robustas** y manejo de errores

### **Para el Negocio**
- ✅ **Cumplimiento fiscal** automático
- ✅ **Reducción de errores** en cálculos
- ✅ **Escalabilidad** para múltiples países
- ✅ **Auditoría completa** de transacciones

---

## 📞 **Soporte y Mantenimiento**

### **Comandos Útiles**
```bash
# Validar configuración de impuestos
python manage.py shell
>>> from accounting.services import TaxValidationService
>>> service = TaxValidationService(empresa)
>>> validation = service.validate_tax_configuration()
>>> print(validation)

# Verificar cálculos
>>> from accounting.services import TaxCalculationService
>>> service = TaxCalculationService(empresa)
>>> taxes = service.get_applicable_taxes(product)
>>> print(taxes)
```

### **Logs y Debugging**
- Los errores de cálculo se registran en la consola
- Validaciones automáticas en cada transacción
- Reportes de configuración disponibles

---

**🎉 ¡El sistema de impuestos está listo para implementar en Synap!** 