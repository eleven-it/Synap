from django import forms
from .models import Product, Brand, Category, Subcategory, InitialStockDraft, InitialStockDraftItem, Warehouse, Location
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import re

class ProductForm(forms.ModelForm):
    images = forms.FileField(
        label=_('Product Images'),
        widget=forms.ClearableFileInput(attrs={'multiple': True, 'class': 'form-input'}),
        required=False
    )
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'category', 'brand', 'subcategory',
            'handle', 'price', 'sale_price', 'cost_price', 'profit_margin', 'price_currency', 'uom', 'tracking',
            'weight_kg', 'volume_m3', 'width_cm', 'height_cm', 'depth_cm', 'is_dangerous', 'barcode',
            'video_url', 'product_kind', 'is_published'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'sku': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-select'}),
            'handle': forms.TextInput(attrs={'class': 'form-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-input'}),
            'profit_margin': forms.NumberInput(attrs={'class': 'form-input'}),
            'price_currency': forms.Select(attrs={'class': 'form-select'}),
            'uom': forms.Select(attrs={'class': 'form-select'}),
            'tracking': forms.Select(attrs={'class': 'form-select'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-input'}),
            'volume_m3': forms.NumberInput(attrs={'class': 'form-input'}),
            'width_cm': forms.NumberInput(attrs={'class': 'form-input'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-input'}),
            'depth_cm': forms.NumberInput(attrs={'class': 'form-input'}),
            'is_dangerous': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'barcode': forms.TextInput(attrs={'class': 'form-input'}),
            'video_url': forms.URLInput(attrs={'class': 'form-input'}),
            'product_kind': forms.Select(attrs={'class': 'form-select'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subcategory'].queryset = Subcategory.objects.none()

        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.subcategory:
            self.fields['subcategory'].queryset = self.instance.subcategory.category.subcategories.order_by('name')

    def clean(self):
        cleaned = super().clean()
        # Validar margen si hay precio y costo
        price = cleaned.get('price')
        cost = cleaned.get('cost_price')
        margin = cleaned.get('profit_margin')
        if price and cost is not None and margin is not None:
            expected_margin = ((price - cost) / price) * 100 if price else 0
            if abs(expected_margin - margin) > 1:
                raise ValidationError({'profit_margin': _('Profit margin does not match price and cost price.')})
        return cleaned

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError(_('Name is required.'))
        if len(name) > 255:
            raise ValidationError(_('Name must be at most 255 characters.'))
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if not description:
            raise ValidationError(_('Description is required.'))
        return description

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price in [None, '']:
            raise ValidationError(_('Price is required.'))
        if isinstance(price, str) and ',' in price:
            raise ValidationError(_('Solo se permite el punto (.) como separador decimal.'))
        return price

    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku is None:
            return None
        sku = sku.strip()
        if sku and not re.match(r'^[A-Za-z0-9\-_.]+$', sku):
            raise ValidationError(_('SKU can only contain letters, numbers, hyphens, underscores and dots.'))
        if sku and Product.objects.exclude(pk=self.instance.pk).filter(sku=sku).exists():
            raise ValidationError(_('SKU must be unique.'))
        return sku

    def clean_handle(self):
        handle = self.cleaned_data.get('handle')
        if handle is None:
            return None
        handle = handle.strip()
        if handle and not re.match(r'^[a-z0-9\-]+$', handle):
            raise ValidationError(_('Handle can only contain lowercase letters, numbers and hyphens.'))
        if handle and Product.objects.exclude(pk=self.instance.pk).filter(handle=handle).exists():
            raise ValidationError(_('Handle must be unique.'))
        return handle

    def clean_sale_price(self):
        sale_price = self.cleaned_data.get('sale_price')
        if isinstance(sale_price, str) and ',' in sale_price:
            raise ValidationError(_('Solo se permite el punto (.) como separador decimal.'))
        return sale_price

    def clean_cost_price(self):
        cost_price = self.cleaned_data.get('cost_price')
        if cost_price in [None, '']:
            return None
        if isinstance(cost_price, str) and ',' in cost_price:
            raise ValidationError(_('Solo se permite el punto (.) como separador decimal.'))
        return cost_price

    def clean_profit_margin(self):
        margin = self.cleaned_data.get('profit_margin')
        if margin is not None:
            if margin < 0 or margin > 100:
                raise ValidationError(_('Profit margin must be between 0 and 100.'))
        return margin

    def clean_weight_kg(self):
        weight = self.cleaned_data.get('weight_kg')
        kind = self.cleaned_data.get('product_kind')
        if kind == 'physical' and (weight is None or weight <= 0):
            raise ValidationError(_('Weight is required and must be greater than 0 for physical products.'))
        return weight

    def clean_width_cm(self):
        width = self.cleaned_data.get('width_cm')
        kind = self.cleaned_data.get('product_kind')
        if kind == 'physical' and (width is None or width <= 0):
            raise ValidationError(_('Width is required and must be greater than 0 for physical products.'))
        return width

    def clean_height_cm(self):
        height = self.cleaned_data.get('height_cm')
        kind = self.cleaned_data.get('product_kind')
        if kind == 'physical' and (height is None or height <= 0):
            raise ValidationError(_('Height is required and must be greater than 0 for physical products.'))
        return height

    def clean_depth_cm(self):
        depth = self.cleaned_data.get('depth_cm')
        kind = self.cleaned_data.get('product_kind')
        if kind == 'physical' and (depth is None or depth <= 0):
            raise ValidationError(_('Depth is required and must be greater than 0 for physical products.'))
        return depth

    def clean_video_url(self):
        url = self.cleaned_data.get('video_url', '').strip()
        if url:
            if not (url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/') or url.startswith('https://vimeo.com/')):
                raise ValidationError(_('Only YouTube or Vimeo links are allowed.'))
        return url

    def clean_product_kind(self):
        kind = self.cleaned_data.get('product_kind')
        if kind not in ['physical', 'digital']:
            raise ValidationError(_('Invalid product kind.'))
        return kind

class InitialStockDraftForm(forms.ModelForm):
    almacen = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        label="Warehouse",
        help_text="Select the warehouse where the initial stock will be loaded."
    )
    ubicacion = forms.ModelChoiceField(
        queryset=Location.objects.none(),
        label="Location",
        help_text="Select the location within the warehouse."
    )
    documentos_respaldo = forms.FileField(
        label="Supporting documents",
        help_text="Upload one or more files as supporting documentation. Drag & drop is supported.",
        widget=forms.ClearableFileInput(attrs={"multiple": True})
    )
    class Meta:
        model = InitialStockDraft
        fields = ['almacen', 'ubicacion', 'comentario', 'tags', 'referencia_externa', 'documentos_respaldo']
        widgets = {
            'comentario': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Add a comment...'}),
            'tags': forms.TextInput(attrs={'placeholder': 'e.g. Migration, Annual inventory'}),
            'referencia_externa': forms.TextInput(attrs={'placeholder': 'External reference'}),
        }
        help_texts = {
            'comentario': 'Add any notes or explanations about this initial stock load.',
            'tags': 'Use tags to classify or filter this load (e.g. Migration, Adjustment).',
            'referencia_externa': 'Link this load to an external document or system.',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        almacenes = self.fields['almacen'].queryset
        if 'almacen' in self.data:
            try:
                almacen_id = int(self.data.get('almacen'))
                self.fields['ubicacion'].queryset = Location.objects.filter(warehouse_id=almacen_id, is_active=True)
            except (ValueError, TypeError):
                self.fields['ubicacion'].queryset = Location.objects.none()
        elif self.instance.pk and self.instance.ubicacion:
            self.fields['ubicacion'].queryset = Location.objects.filter(warehouse=self.instance.ubicacion.warehouse, is_active=True)
            self.fields['almacen'].initial = self.instance.ubicacion.warehouse.pk
        elif almacenes.count() == 1:
            almacen = almacenes.first()
            self.fields['almacen'].initial = almacen.pk
            self.fields['ubicacion'].queryset = Location.objects.filter(warehouse=almacen, is_active=True)
        else:
            self.fields['ubicacion'].queryset = Location.objects.none()

class InitialStockDraftItemForm(forms.ModelForm):
    class Meta:
        model = InitialStockDraftItem
        fields = ['producto', 'sku', 'cantidad', 'lote', 'fecha_vencimiento', 'observaciones', 'uom', 'precio_unitario', 'ubicacion_detalle']
        widgets = {
            'observaciones': forms.Textarea(attrs={'rows': 1}),
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('cantidad', 0) <= 0:
            self.add_error('cantidad', 'La cantidad debe ser mayor a cero.')
        return cleaned

class InitialStockDraftExcelForm(forms.ModelForm):
    class Meta:
        model = InitialStockDraft
        fields = ['archivo_excel']
    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if archivo:
            if not archivo.name.endswith('.xlsx'):
                raise forms.ValidationError('El archivo debe ser formato Excel (.xlsx)')
            if archivo.size > 2*1024*1024:
                raise forms.ValidationError('El archivo no debe superar los 2MB.')
        return archivo 