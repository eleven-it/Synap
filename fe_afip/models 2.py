"""
Configuración de Factura Electrónica AFIP por empresa (base administraNET).
Credenciales y modo Homologación/Producción; nunca loguear cert/key ni CUIT completo.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class AFIPConfig(models.Model):
    """
    Configuración FE AFIP por base empresa (administraNET).
    Una configuración por base; modo Homologación para pruebas, Producción cuando esté validado.
    """
    name = models.CharField(
        _("Nombre"),
        max_length=64,
        default="Default",
        help_text=_("Identificador de la configuración"),
    )
    # Base de datos administraNET (empresa)
    base_empresa = models.CharField(
        _("Base empresa (DB)"),
        max_length=64,
        db_index=True,
        unique=True,
        help_text=_("Nombre de la base de datos administraNET. Una config por base."),
    )
    # Rutas a archivos en el servidor (no subir clave privada a DB)
    cert_path = models.CharField(
        _("Ruta certificado"),
        max_length=512,
        blank=True,
        help_text=_("Ruta absoluta al archivo .crt o .pem del certificado AFIP"),
    )
    key_path = models.CharField(
        _("Ruta clave privada"),
        max_length=512,
        blank=True,
        help_text=_("Ruta absoluta al archivo .key o .pem de la clave privada"),
    )
    cuit = models.CharField(
        _("CUIT contribuyente"),
        max_length=14,
        blank=True,
        help_text=_("CUIT de 11 dígitos (con o sin guiones)"),
    )
    # Homologación = True → pruebas AFIP (wsaahomo, wswhomo). Producción = False → ambiente real.
    modo_homologacion = models.BooleanField(
        _("Modo homologación"),
        default=True,
        help_text=_("Activado: usa entornos de prueba AFIP (todas las pruebas). Desactivado: producción (solo cuando esté validado)."),
    )
    cache_dir = models.CharField(
        _("Directorio caché"),
        max_length=512,
        blank=True,
        default="/tmp/pyafipws_cache",
        help_text=_("Directorio para caché de tickets WSAA (opcional)"),
    )
    activo = models.BooleanField(_("Activo"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "fe_afip"
        verbose_name = _("Configuración AFIP (FE)")
        verbose_name_plural = _("Configuraciones AFIP (FE)")

    def __str__(self):
        modo = "Homologación" if self.modo_homologacion else "Producción"
        return f"AFIP {self.name} ({self.base_empresa}) [{modo}]"

    def clean(self):
        from django.core.exceptions import ValidationError
        c = (self.cuit or "").replace("-", "").replace(" ", "")
        if c and (len(c) != 11 or not c.isdigit()):
            raise ValidationError({"cuit": _("El CUIT debe tener 11 dígitos.")})


class CAEACode(models.Model):
    """
    CAEA (Código de Autorización Electrónico Anticipado) por período quincenal.
    Período 1 = días 1-15 del mes; período 2 = días 16 al último.
    Se solicita dentro de los 5 días corridos previos al inicio de cada período.
    """
    SOURCE_CONSULTAR = "consultar"
    SOURCE_SOLICITAR = "solicitar"

    base_empresa = models.CharField(
        _("Base empresa (DB)"),
        max_length=64,
        db_index=True,
        help_text=_("Nombre de la base de datos administraNET."),
    )
    periodo = models.CharField(
        _("Período YYYYMM"),
        max_length=6,
        help_text=_("Año y mes, ej. 202601."),
    )
    orden = models.SmallIntegerField(
        _("Orden quincena"),
        help_text=_("1 = días 1-15, 2 = días 16-fin de mes."),
    )
    codigo = models.CharField(
        _("Código CAEA"),
        max_length=24,
        help_text=_("Valor devuelto por AFIP."),
    )
    vencimiento = models.DateField(
        _("Vencimiento"),
        null=True,
        blank=True,
        help_text=_("Fin de vigencia del período (último día de la quincena)."),
    )
    requested_at = models.DateTimeField(_("Solicitado el"), auto_now_add=True)
    source = models.CharField(
        _("Origen"),
        max_length=16,
        choices=[
            (SOURCE_CONSULTAR, _("Consultar")),
            (SOURCE_SOLICITAR, _("Solicitar")),
        ],
        default=SOURCE_SOLICITAR,
    )

    class Meta:
        app_label = "fe_afip"
        verbose_name = _("CAEA por período")
        verbose_name_plural = _("CAEAs por período")
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "periodo", "orden"],
                name="fe_afip_caea_unique_periodo_orden",
            ),
        ]
        indexes = [
            models.Index(fields=["base_empresa", "periodo", "orden"]),
        ]

    def __str__(self):
        return f"CAEA {self.base_empresa} {self.periodo} ord.{self.orden}"
