"""
Formularios para Remito de compra (paridad PRemito.frm VB6).
Solo cabecera; renglones se gestionan vía cuerpostockp (temporales) y servicios.
"""
from django import forms


class RemitoCompraCabeceraForm(forms.Form):
    DEPOSITO_SELECCION_CHOICES = [
        ("defecto_usuario", "Defecto usuario"),
        ("comp_original", "Comp. original"),
        ("seleccionado", "Seleccionado"),
        ("por_articulo", "Por artículo"),
    ]
    TIPO_COMP_CHOICES = [
        ("ord_compra", "Ord. Compra"),
        ("factura", "Factura"),
    ]

    """Cabecera del remito de compra (paridad FrameEncabezado + FramePie)."""

    tipo_comp = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=TIPO_COMP_CHOICES,
        initial="ord_compra",
        widget=forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    nro = forms.CharField(
        label="Nro. Comprobante",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "placeholder": "Número"}),
    )
    nro_suc = forms.CharField(
        label="Nro. Suc.",
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "placeholder": "Suc."}),
    )
    fecha = forms.DateField(
        label="Fecha Comprobante",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    fecha_registro = forms.DateField(
        label="Fecha Registro",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    detalle = forms.CharField(
        label="Detalle",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    codigo_proveedor = forms.IntegerField(
        label="Proveedor",
        required=True,
        widget=forms.HiddenInput(),
    )
    nombre_proveedor = forms.CharField(
        label="Proveedor",
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "readonly": "readonly"}),
    )
    id_deposito = forms.TypedChoiceField(
        label="Depósito",
        required=True,
        coerce=int,
        empty_value=0,
        widget=forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    deposito_seleccion = forms.ChoiceField(
        label="Modo depósito",
        required=False,
        choices=DEPOSITO_SELECCION_CHOICES,
        initial="defecto_usuario",
        widget=forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    # Pie (totales)
    importe_total = forms.DecimalField(
        label="Total General",
        required=False,
        decimal_places=2,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-right", "readonly": "readonly"}),
    )
    exento = forms.DecimalField(
        label="Exento",
        required=False,
        decimal_places=2,
        initial=0,
        widget=forms.HiddenInput(),
    )
    subtotal1 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    subtotal2 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    imp_desc1_1 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    sub_total_desc1 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    sub_total_desc2 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    iva1 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    iva2 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    iva3 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    alic1 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    alic2 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    alic3 = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    percep_ib = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    percep_ib_prov = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    percep_gan = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    percep_iva = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    otros_imp = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    impuesto_interno = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    id_condcompra = forms.IntegerField(required=False, widget=forms.HiddenInput())
    cond_compra = forms.CharField(required=False, widget=forms.HiddenInput())
    coti_dolar = forms.DecimalField(required=False, initial=0, widget=forms.HiddenInput())
    nro_cai = forms.CharField(required=False, widget=forms.HiddenInput())
    fecha_cai = forms.DateField(required=False, widget=forms.HiddenInput())

    def __init__(self, depositos_choices=None, tipo_comp_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if depositos_choices is not None:
            self.fields["id_deposito"].choices = depositos_choices
        if tipo_comp_choices is not None:
            self.fields["tipo_comp"].choices = tipo_comp_choices
        self.fields["id_deposito"].widget.attrs["x-model"] = "depositoGlobal"
        self.fields["deposito_seleccion"].widget.attrs["x-model"] = "depositoMode"
        self.fields["tipo_comp"].widget.attrs["x-model"] = "tipoComp"


class AltaRenglonRemitoForm(forms.Form):
    """Alta de un renglón temporal en cuerpostockp (paridad AceptarStock / agregar línea)."""

    codigo_articulo = forms.CharField(
        label="Código artículo",
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "placeholder": "Código"}),
    )
    descripcion = forms.CharField(
        label="Descripción",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "placeholder": "Descripción"}),
    )
    cantidad = forms.DecimalField(
        label="Cantidad",
        required=True,
        min_value=0,
        decimal_places=4,
        widget=forms.NumberInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "step": "0.0001"}),
    )
    id_deposito = forms.TypedChoiceField(
        label="Depósito",
        required=False,
        coerce=int,
        empty_value=None,
        widget=forms.Select(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2"}),
    )
    precio_costo_u = forms.DecimalField(
        label="Precio costo x unidad",
        required=True,
        decimal_places=4,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2", "step": "0.0001"}),
    )

    def __init__(self, depositos_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if depositos_choices is not None:
            self.fields["id_deposito"].choices = depositos_choices
