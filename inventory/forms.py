from django import forms
from .models import Product, Brand, Category, Subcategory

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'brand', 'subcategory', 'image',
            'handle', 'price', 'price_currency', 'uom', 'tracking',
            'is_published'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'sku': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
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