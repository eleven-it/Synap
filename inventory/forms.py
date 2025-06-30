from django import forms
from .models import Product, Brand, Category, Subcategory, InitialStockDraft, InitialStockDraftItem, Warehouse, Location
from django.utils.translation import gettext_lazy as _

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'category', 'brand', 'subcategory', 'image',
            'handle', 'price', 'price_currency', 'uom', 'tracking',
            'is_published'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'sku': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-input'}),
            'handle': forms.TextInput(attrs={'class': 'form-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
            'price_currency': forms.Select(attrs={'class': 'form-select'}),
            'uom': forms.Select(attrs={'class': 'form-select'}),
            'tracking': forms.Select(attrs={'class': 'form-select'}),
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
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')
        if subcategory and category and subcategory.category != category:
            self.add_error('subcategory', _('La subcategoría seleccionada no pertenece al rubro seleccionado.'))
        return cleaned_data

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