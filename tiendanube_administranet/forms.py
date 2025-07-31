"""
Formularios para la integración Tiendanube-AdministraNET.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping,
    ProductMapping, ProductVariantMapping, ProductCategoryMapping,
    OrderMapping, WebhookConfig
)


class TiendanubeConfigForm(forms.ModelForm):
    """
    Formulario para configuración de Tiendanube.
    """
    
    class Meta:
        model = TiendanubeConfig
        fields = ['name', 'store_id', 'access_token', 'api_url', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nombre de la configuración')
            }),
            'store_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('ID de la tienda')
            }),
            'access_token': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': _('Token de acceso')
            }),
            'api_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://api.tiendanube.com/v1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': _('Nombre'),
            'store_id': _('ID de Tienda'),
            'access_token': _('Token de Acceso'),
            'api_url': _('URL de la API'),
            'is_active': _('Activo')
        }
        help_texts = {
            'store_id': _('ID único de tu tienda en Tiendanube'),
            'access_token': _('Token de acceso para la API de Tiendanube'),
            'api_url': _('URL base de la API de Tiendanube'),
            'is_active': _('Activar esta configuración')
        }
    
    def clean_store_id(self):
        """Validar que el store_id sea único si está activo."""
        store_id = self.cleaned_data['store_id']
        is_active = self.cleaned_data.get('is_active', False)
        
        if is_active:
            existing = TiendanubeConfig.objects.filter(
                store_id=store_id,
                is_active=True
            )
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise ValidationError(_('Ya existe una configuración activa con este ID de tienda.'))
        
        return store_id


class AdministraNETConfigForm(forms.ModelForm):
    """
    Formulario para configuración de AdministraNET.
    """
    
    class Meta:
        model = AdministraNETConfig
        fields = ['name', 'host', 'port', 'database', 'user', 'password', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'placeholder': _('Nombre de la configuración')
            }),
            'host': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'placeholder': 'localhost'
            }),
            'port': forms.NumberInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'min': 1,
                'max': 65535
            }),
            'database': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'placeholder': _('Nombre de la base de datos')
            }),
            'user': forms.TextInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'placeholder': _('Usuario de la base de datos')
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'block w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400',
                'placeholder': _('Contraseña de la base de datos')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            })
        }
        labels = {
            'name': _('Nombre'),
            'host': _('Host'),
            'port': _('Puerto'),
            'database': _('Base de Datos'),
            'user': _('Usuario'),
            'password': _('Contraseña'),
            'is_active': _('Activo')
        }
        help_texts = {
            'host': _('Dirección del servidor MySQL'),
            'port': _('Puerto del servidor MySQL (por defecto: 3306)'),
            'database': _('Nombre de la base de datos de AdministraNET'),
            'user': _('Usuario con permisos de lectura/escritura'),
            'password': _('Contraseña del usuario'),
            'is_active': _('Activar esta configuración')
        }
    
    def clean(self):
        """Validar que solo haya una configuración activa."""
        cleaned_data = super().clean()
        is_active = cleaned_data.get('is_active', False)
        
        if is_active:
            existing = AdministraNETConfig.objects.filter(is_active=True)
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise ValidationError(_('Ya existe una configuración activa de AdministraNET.'))
        
        return cleaned_data


class CustomerMappingForm(forms.ModelForm):
    """
    Formulario para mapeo de clientes entre Tiendanube y AdministraNET.
    """
    
    class Meta:
        model = CustomerMapping
        fields = [
            # Campos de Tiendanube
            'tiendanube_id', 'tiendanube_email', 'tiendanube_name',
            'tiendanube_first_name', 'tiendanube_last_name', 'tiendanube_document',
            'tiendanube_phone', 'tiendanube_address', 'tiendanube_city',
            'tiendanube_state', 'tiendanube_country', 'tiendanube_postal_code',
            'tiendanube_notes', 'tiendanube_tags', 'tiendanube_accepts_marketing',
            'tiendanube_total_spent', 'tiendanube_orders_count',
            'tiendanube_last_order_id', 'tiendanube_verified_email',
            'tiendanube_multipass_identifier', 'tiendanube_tax_exempt',
            'tiendanube_tax_exemptions', 'tiendanube_created_at', 'tiendanube_updated_at',
            
            # Campos de AdministraNET
            'adminet_codigo', 'adminet_nombre', 'adminet_email', 'adminet_documento',
            'adminet_telefono', 'adminet_calle', 'adminet_nro_calle', 'adminet_dpto', 'adminet_direccion',
            'adminet_id_distrito', 'adminet_cod_provincia', 'adminet_id_departamento',
            'adminet_tipo_cliente', 'adminet_cod_viajante', 'adminet_id_pais', 'adminet_estado',
            'adminet_tipo_doc', 'adminet_lista_precio', 'adminet_fecha_alta', 'adminet_fecha_ultima_compra',
            'adminet_cuit', 'adminet_credito', 'adminet_descuento', 'adminet_observaciones',
            'adminet_saldo', 'adminet_id_manual_cli', 'adminet_nombre_fantasia', 'adminet_cliente_ecommerce',
            
            # Configuración de sincronización
            'sync_direction', 'sync_status', 'sync_enabled'
        ]
        widgets = {
            'tiendanube_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@email.com'
            }),
            'tiendanube_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del cliente'
            }),
            'tiendanube_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'tiendanube_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'tiendanube_document': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DNI, CUIT, etc.'
            }),
            'tiendanube_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+54 11 1234-5678'
            }),
            'tiendanube_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'adminet_calle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la calle'
            }),
            'adminet_nro_calle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de calle'
            }),
            'adminet_dpto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Departamento/Piso'
            }),
            'adminet_id_distrito': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Distrito'
            }),
            'adminet_cod_provincia': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Provincia'
            }),
            'adminet_id_departamento': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Departamento'
            }),
            'adminet_tipo_cliente': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tipo Cliente'
            }),
            'adminet_cod_viajante': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Viajante'
            }),
            'adminet_id_pais': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID País'
            }),
            'adminet_tipo_doc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tipo Documento'
            }),
            'adminet_lista_precio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lista Precio'
            }),
            'adminet_fecha_ultima_compra': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'adminet_cuit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CUIT'
            }),
            'adminet_credito': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Crédito'
            }),
            'adminet_descuento': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Descuento'
            }),
            'adminet_observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones'
            }),
            'adminet_saldo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Saldo'
            }),
            'adminet_id_manual_cli': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Manual Cliente'
            }),
            'adminet_nombre_fantasia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre Fantasía'
            }),
            'adminet_cliente_ecommerce': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cliente Ecommerce'
            }),
            'tiendanube_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'tiendanube_state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Provincia/Estado'
            }),
            'tiendanube_country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'País'
            }),
            'tiendanube_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código postal'
            }),
            'tiendanube_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
            'tiendanube_tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'tag1, tag2, tag3'
            }),
            'tiendanube_total_spent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'tiendanube_orders_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'tiendanube_last_order_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'tiendanube_multipass_identifier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Identificador Multipass'
            }),
            'tiendanube_tax_exemptions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemption1, exemption2'
            }),
            'tiendanube_created_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'tiendanube_updated_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            
            # Campos de AdministraNET
            'adminet_codigo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'adminet_nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre en AdministraNET'
            }),
            'adminet_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Documento en AdministraNET'
            }),
            'adminet_telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono en AdministraNET'
            }),
            'adminet_direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección en AdministraNET'
            }),
            'adminet_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email en AdministraNET'
            }),
            'adminet_estado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estado en AdministraNET'
            }),
            'adminet_id_departamento': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID Departamento'
            }),
            'adminet_cod_provincia': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código Provincia'
            }),
            'adminet_fecha_alta': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer algunos campos de solo lectura
        readonly_fields = [
            'tiendanube_id', 'tiendanube_created_at', 'tiendanube_updated_at',
            'tiendanube_total_spent', 'tiendanube_orders_count', 'tiendanube_last_order_id',
            'tiendanube_verified_email', 'tiendanube_multipass_identifier'
        ]
        
        for field_name in readonly_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['readonly'] = True
                self.fields[field_name].widget.attrs['class'] = 'form-control bg-light'
    
    def clean_tiendanube_email(self):
        """Validar email único."""
        email = self.cleaned_data.get('tiendanube_email')
        if not email:
            return email
        
        # Verificar si ya existe un mapeo con este email
        existing = CustomerMapping.objects.filter(tiendanube_email=email)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        
        if existing.exists():
            raise forms.ValidationError("Ya existe un mapeo con este email.")
        
        return email
    
    def clean_tiendanube_tags(self):
        """Convertir tags de string a lista."""
        tags = self.cleaned_data.get('tiendanube_tags')
        if isinstance(tags, str):
            # Convertir string "tag1, tag2" a lista
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        return tags
    
    def clean_tiendanube_tax_exemptions(self):
        """Convertir exenciones de string a lista."""
        exemptions = self.cleaned_data.get('tiendanube_tax_exemptions')
        if isinstance(exemptions, str):
            # Convertir string "exemption1, exemption2" a lista
            exemptions = [exemption.strip() for exemption in exemptions.split(',') if exemption.strip()]
        return exemptions
    
    def clean(self):
        """Validación cruzada de campos."""
        cleaned_data = super().clean()
        
        # Validar que al menos uno de name o first_name+last_name esté presente
        name = cleaned_data.get('tiendanube_name')
        first_name = cleaned_data.get('tiendanube_first_name')
        last_name = cleaned_data.get('tiendanube_last_name')
        
        if not name and not (first_name or last_name):
            raise forms.ValidationError(
                "Debe proporcionar un nombre completo (name) o nombre y apellido (first_name + last_name)."
            )
        
        return cleaned_data


class CustomerMappingFilterForm(forms.Form):
    """
    Formulario para filtrar mapeos de clientes.
    """
    
    # Filtros básicos
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por email, nombre o documento...'
        })
    )
    
    sync_status = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('synced', 'Sincronizado'),
            ('pending', 'Pendiente'),
            ('error', 'Error'),
            ('conflict', 'Conflicto'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sync_direction = forms.ChoiceField(
        choices=[
            ('', 'Todas las direcciones'),
            ('bidirectional', 'Bidireccional'),
            ('tiendanube_to_adminet', 'Tiendanube → AdministraNET'),
            ('adminet_to_tiendanube', 'AdministraNET → Tiendanube'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sync_enabled = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('true', 'Habilitado'),
            ('false', 'Deshabilitado'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Filtros de Tiendanube
    tiendanube_verified_email = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('true', 'Email verificado'),
            ('false', 'Email no verificado'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tiendanube_accepts_marketing = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('true', 'Acepta marketing'),
            ('false', 'No acepta marketing'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tiendanube_has_orders = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('true', 'Con órdenes'),
            ('false', 'Sin órdenes'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tiendanube_country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'País'
        })
    )
    
    tiendanube_city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ciudad'
        })
    )
    
    # Filtros de fecha
    created_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    created_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    last_synced_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    last_synced_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    # Filtros de rango
    total_spent_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo',
            'step': '0.01',
            'min': '0'
        })
    )
    
    total_spent_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Máximo',
            'step': '0.01',
            'min': '0'
        })
    )
    
    orders_count_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo',
            'min': '0'
        })
    )
    
    orders_count_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Máximo',
            'min': '0'
        })
    )
    
    def clean(self):
        """Validar rangos de fechas y valores."""
        cleaned_data = super().clean()
        
        # Validar rangos de fechas
        created_from = cleaned_data.get('created_date_from')
        created_to = cleaned_data.get('created_date_to')
        if created_from and created_to and created_from > created_to:
            raise forms.ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        
        synced_from = cleaned_data.get('last_synced_from')
        synced_to = cleaned_data.get('last_synced_to')
        if synced_from and synced_to and synced_from > synced_to:
            raise forms.ValidationError("La fecha de sincronización inicial debe ser anterior a la final.")
        
        # Validar rangos de valores
        spent_min = cleaned_data.get('total_spent_min')
        spent_max = cleaned_data.get('total_spent_max')
        if spent_min and spent_max and spent_min > spent_max:
            raise forms.ValidationError("El gasto mínimo debe ser menor al máximo.")
        
        orders_min = cleaned_data.get('orders_count_min')
        orders_max = cleaned_data.get('orders_count_max')
        if orders_min and orders_max and orders_min > orders_max:
            raise forms.ValidationError("El número mínimo de órdenes debe ser menor al máximo.")
        
        return cleaned_data


class ProductMappingForm(forms.ModelForm):
    """
    Formulario para mapeo de productos.
    """
    class Meta:
        model = ProductMapping
        fields = [
            'tiendanube_name', 'tiendanube_handle', 'tiendanube_description', 'tiendanube_sku',
            'tiendanube_price', 'tiendanube_compare_at_price', 'tiendanube_cost', 'tiendanube_stock',
            'tiendanube_weight', 'tiendanube_width', 'tiendanube_height', 'tiendanube_depth',
            'tiendanube_free_shipping', 'tiendanube_published', 'tiendanube_featured',
            'tiendanube_product_type', 'tiendanube_seo_title', 'tiendanube_seo_description',
            'tiendanube_brand', 'tiendanube_categories', 'tiendanube_tags', 'tiendanube_images',
            'tiendanube_videos', 'tiendanube_created_at', 'tiendanube_updated_at',
            'adminet_id', 'adminet_id_manual', 'adminet_codigo_articulo', 'adminet_nombre', 'adminet_detalle',
            'adminet_precio_costo', 'adminet_precio_1v', 'adminet_precio_2v', 'adminet_precio_3v', 'adminet_precio_4v', 'adminet_precio_5v',
            'adminet_stock', 'adminet_stock_max', 'adminet_stock_min', 'adminet_codigo_barra', 'adminet_codigo_barra_f',
            'adminet_codigo_proveedor', 'adminet_codigo_marca', 'adminet_codigo_modelo', 'adminet_codigo_rubro', 'adminet_codigo_subrubro',
            'adminet_alicuota', 'adminet_alicuota_ib', 'adminet_moneda', 'adminet_tipo_iva', 'adminet_tipo_ib',
            'adminet_discontinuo', 'adminet_ecommerce', 'adminet_detalle_web', 'adminet_disponible_venta', 'adminet_disponible_compra',
            'adminet_promo_destacado', 'adminet_fecha_alta', 'adminet_fecha_mod',
            'sync_enabled', 'sync_price', 'sync_stock', 'sync_description', 'sync_images'
        ]
        widgets = {
            'tiendanube_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_handle': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tiendanube_sku': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_compare_at_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'tiendanube_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'tiendanube_width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_depth': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_free_shipping': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiendanube_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiendanube_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiendanube_product_type': forms.Select(attrs={'class': 'form-select'}),
            'tiendanube_seo_title': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_seo_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tiendanube_brand': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_categories': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'category1, category2'}),
            'tiendanube_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'tag1, tag2, tag3'}),
            'tiendanube_images': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'url1, url2'}),
            'tiendanube_videos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'url1, url2'}),
            'tiendanube_created_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'tiendanube_updated_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'adminet_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_id_manual': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_codigo_articulo': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_detalle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'adminet_precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_precio_1v': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_precio_2v': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_precio_3v': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_precio_4v': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_precio_5v': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'adminet_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_stock_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adminet_stock_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adminet_codigo_barra': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_codigo_barra_f': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_codigo_proveedor': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_codigo_marca': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_codigo_modelo': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_codigo_rubro': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_codigo_subrubro': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_alicuota': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_alicuota_ib': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_moneda': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_tipo_iva': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_tipo_ib': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_discontinuo': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_ecommerce': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_detalle_web': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'adminet_disponible_venta': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_disponible_compra': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_promo_destacado': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_fecha_alta': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'adminet_fecha_mod': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_price': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_description': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_images': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer algunos campos opcionales
        self.fields['tiendanube_compare_at_price'].required = False
        self.fields['tiendanube_cost'].required = False
        self.fields['tiendanube_weight'].required = False
        self.fields['tiendanube_width'].required = False
        self.fields['tiendanube_height'].required = False
        self.fields['tiendanube_depth'].required = False
        self.fields['tiendanube_seo_title'].required = False
        self.fields['tiendanube_seo_description'].required = False
        self.fields['adminet_detalle'].required = False


class ProductVariantMappingForm(forms.ModelForm):
    """
    Formulario para mapeo de variantes de productos.
    """
    class Meta:
        model = ProductVariantMapping
        fields = [
            'tiendanube_name', 'tiendanube_sku', 'tiendanube_price', 'tiendanube_compare_at_price',
            'tiendanube_cost', 'tiendanube_stock', 'tiendanube_weight', 'tiendanube_width',
            'tiendanube_height', 'tiendanube_depth', 'tiendanube_free_shipping', 'tiendanube_published',
            'tiendanube_values', 'tiendanube_images', 'tiendanube_product_id', 'tiendanube_options',
            'tiendanube_created_at', 'tiendanube_updated_at',
            'adminet_id', 'adminet_id_manual', 'adminet_codigo_articulo', 'adminet_nombre', 'adminet_detalle',
            'adminet_precio_costo', 'adminet_precio_1v', 'adminet_stock', 'adminet_codigo_barra',
            'adminet_codigo_proveedor', 'adminet_codigo_marca', 'adminet_codigo_modelo',
            'adminet_alicuota', 'adminet_alicuota_ib', 'adminet_moneda', 'adminet_tipo_iva', 'adminet_tipo_ib',
            'adminet_discontinuo', 'adminet_ecommerce', 'adminet_detalle_web', 'adminet_disponible_venta', 'adminet_disponible_compra',
            'adminet_fecha_alta', 'adminet_fecha_mod',
            'sync_enabled', 'sync_price', 'sync_stock'
        ]
        widgets = {
            'tiendanube_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_sku': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_compare_at_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'tiendanube_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'tiendanube_width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_depth': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiendanube_free_shipping': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiendanube_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'adminet_codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adminet_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'adminet_peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'adminet_ancho': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adminet_alto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'adminet_profundo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_price': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer algunos campos opcionales
        self.fields['tiendanube_compare_at_price'].required = False
        self.fields['tiendanube_cost'].required = False
        self.fields['tiendanube_weight'].required = False
        self.fields['tiendanube_width'].required = False
        self.fields['tiendanube_height'].required = False
        self.fields['tiendanube_depth'].required = False
        self.fields['adminet_peso'].required = False
        self.fields['adminet_ancho'].required = False
        self.fields['adminet_alto'].required = False
        self.fields['adminet_profundo'].required = False


class ProductCategoryMappingForm(forms.ModelForm):
    """
    Formulario para mapeo de categorías de productos.
    """
    class Meta:
        model = ProductCategoryMapping
        fields = [
            'tiendanube_name', 'tiendanube_handle', 'tiendanube_description',
            'adminet_codigo', 'adminet_nombre', 'adminet_descripcion',
            'sync_enabled'
        ]
        widgets = {
            'tiendanube_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_handle': forms.TextInput(attrs={'class': 'form-control'}),
            'tiendanube_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'adminet_codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'adminet_descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tiendanube_description'].required = False
        self.fields['adminet_descripcion'].required = False


class OrderMappingForm(forms.ModelForm):
    """
    Formulario para mapeo de órdenes.
    """
    
    class Meta:
        model = OrderMapping
        fields = [
            'tiendanube_number', 'tiendanube_total', 'tiendanube_currency', 'tiendanube_status',
            'tiendanube_payment_status', 'tiendanube_notes', 'tiendanube_customer_id',
            'tiendanube_customer_email', 'tiendanube_customer_name', 'tiendanube_shipping_address',
            'tiendanube_billing_address', 'tiendanube_payment_method', 'tiendanube_shipping_method',
            'tiendanube_created_at', 'tiendanube_updated_at',
            'adminet_codigo', 'adminet_numero', 'adminet_estado', 'adminet_total',
            'sync_enabled'
        ]
        widgets = {
            'tiendanube_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Número de orden en Tiendanube')
            }),
            'tiendanube_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': _('Total de la orden')
            }),
            'tiendanube_currency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Moneda (USD, ARS, etc.)')
            }),
            'tiendanube_status': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estado de la orden')
            }),
            'tiendanube_payment_status': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estado del pago')
            }),
            'tiendanube_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Notas de la orden')
            }),
            'tiendanube_customer_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('ID del cliente')
            }),
            'tiendanube_customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Email del cliente de la orden')
            }),
            'tiendanube_customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Nombre del cliente')
            }),
            'tiendanube_shipping_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Dirección de envío (JSON)')
            }),
            'tiendanube_billing_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Dirección de facturación (JSON)')
            }),
            'tiendanube_payment_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Método de pago')
            }),
            'tiendanube_shipping_method': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Método de envío')
            }),
            'tiendanube_created_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'tiendanube_updated_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'adminet_codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Código de la orden en AdministraNET')
            }),
            'adminet_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Número de orden en AdministraNET')
            }),
            'adminet_estado': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estado en AdministraNET')
            }),
            'adminet_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': _('Total en AdministraNET')
            }),
            'sync_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'tiendanube_number': _('Número Tiendanube'),
            'tiendanube_customer_email': _('Email Cliente Tiendanube'),
            'adminet_codigo': _('Código AdministraNET'),
            'adminet_numero': _('Número AdministraNET'),
            'sync_enabled': _('Sincronización Habilitada')
        }
        help_texts = {
            'sync_enabled': _('Habilitar sincronización automática')
        }


class SyncConfigurationForm(forms.Form):
    """
    Formulario para configuración de sincronización.
    """
    
    sync_interval = forms.ChoiceField(
        choices=[
            ('5', _('5 minutos')),
            ('15', _('15 minutos')),
            ('30', _('30 minutos')),
            ('60', _('1 hora')),
            ('360', _('6 horas')),
            ('720', _('12 horas')),
            ('1440', _('1 día'))
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Intervalo de Sincronización'),
        help_text=_('Frecuencia de sincronización automática')
    )
    
    batch_size = forms.IntegerField(
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label=_('Tamaño de Lote'),
        help_text=_('Número de registros a procesar por lote'),
        initial=100
    )
    
    auto_sync_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Sincronización Automática Habilitada'),
        help_text=_('Habilitar sincronización automática programada')
    )
    
    error_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Notificaciones de Error'),
        help_text=_('Enviar notificaciones cuando ocurran errores'),
        initial=True
    ) 


class WebhookConfigForm(forms.ModelForm):
    """
    Formulario para configuración de webhooks.
    """
    
    class Meta:
        model = WebhookConfig
        fields = [
            'tiendanube_config', 'webhook_url', 'webhook_secret', 
            'events', 'description', 'is_active', 'max_retries', 'retry_delay'
        ]
        widgets = {
            'webhook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://your-domain.com/webhooks/tiendanube/'
            }),
            'webhook_secret': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional secret for webhook verification'
            }),
            'events': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of this webhook configuration'
            }),
            'max_retries': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 10
            }),
            'retry_delay': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 60,
                'max': 3600
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar configuraciones activas de Tiendanube
        self.fields['tiendanube_config'].queryset = TiendanubeConfig.objects.filter(is_active=True)
        
        # Agrupar eventos por categoría
        event_choices = []
        event_groups = {
            'Products': [
                ('product/created', 'Product Created'),
                ('product/updated', 'Product Updated'),
                ('product/deleted', 'Product Deleted'),
            ],
            'Orders': [
                ('order/created', 'Order Created'),
                ('order/updated', 'Order Updated'),
                ('order/cancelled', 'Order Cancelled'),
                ('order/paid', 'Order Paid'),
                ('order/fulfilled', 'Order Fulfilled'),
            ],
            'Customers': [
                ('customer/created', 'Customer Created'),
                ('customer/updated', 'Customer Updated'),
                ('customer/deleted', 'Customer Deleted'),
            ],
            'Inventory': [
                ('inventory/updated', 'Inventory Updated'),
            ],
            'Categories': [
                ('category/created', 'Category Created'),
                ('category/updated', 'Category Updated'),
                ('category/deleted', 'Category Deleted'),
            ]
        }
        
        for group_name, events in event_groups.items():
            event_choices.append((group_name, events))
        
        self.fields['events'].choices = event_choices
    
    def clean_webhook_url(self):
        """Validar URL del webhook."""
        url = self.cleaned_data['webhook_url']
        
        # Verificar que sea HTTPS en producción
        if settings.DEBUG is False and not url.startswith('https://'):
            raise forms.ValidationError(
                'Webhook URL must use HTTPS in production environment.'
            )
        
        return url
    
    def clean_events(self):
        """Validar eventos seleccionados."""
        events = self.cleaned_data['events']
        
        if not events:
            raise forms.ValidationError(
                'At least one event must be selected.'
            )
        
        return events


class WebhookEventFilterForm(forms.Form):
    """
    Formulario para filtrar eventos de webhook.
    """
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('', 'All Event Types'),
        ('product', 'Product Events'),
        ('order', 'Order Events'),
        ('customer', 'Customer Events'),
        ('inventory', 'Inventory Events'),
        ('category', 'Category Events'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    event_type = forms.ChoiceField(
        choices=EVENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    resource_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Resource ID'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    webhook_config = forms.ModelChoiceField(
        queryset=WebhookConfig.objects.all(),
        required=False,
        empty_label="All Webhooks",
        widget=forms.Select(attrs={'class': 'form-select'})
    ) 