from django.db import models

class TiendaNubeCondVentaMap(models.Model):
    payment_method = models.CharField(max_length=100, unique=True, verbose_name="Método de pago Tiendanube")
    adminet_codigo = models.IntegerField(verbose_name="Código condición de venta administraNET")
    adminet_descripcion = models.CharField(max_length=255, blank=True, verbose_name="Descripción administraNET")
    activo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mapeo condición de venta Tiendanube"
        verbose_name_plural = "Mapeos condiciones de venta Tiendanube"
        ordering = ['payment_method']

    def __str__(self):
        return f"{self.payment_method} → {self.adminet_codigo} ({self.adminet_descripcion})"

class TiendaNubeAdminetConfig(models.Model):
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=3306)
    database = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de conexión AdministraNET"
        verbose_name_plural = "Configuraciones de conexión AdministraNET"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.host}:{self.port}/{self.database} ({'Activo' if self.is_active else 'Inactivo'})" 