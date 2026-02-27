# MPR - Modelos para agrupar OPT (Pedidos de producción) con múltiples artículos.
# Cada fila en lista_produccion_agrupada (MySQL) tiene su propio id_lista_produccion.
# Opt agrupa varias líneas (OptLinea) para representar una OPT con múltiples artículos.
from django.db import models


class Opt(models.Model):
    """Cabecera de un Pedido de producción (OPT) con uno o más artículos."""

    base_empresa = models.CharField(max_length=64, db_index=True)
    id_lista_principal = models.BigIntegerField(
        help_text="Primer id_lista_produccion de la OPT (para enlaces y detalle)."
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    id_usuario = models.IntegerField(null=True, blank=True)
    codigo_movimiento = models.IntegerField(
        null=True,
        blank=True,
        help_text="CodigoMovimiento del comprobante MSTOCK (OPT) cuando se liberó; para imprimir comprobante.",
    )

    class Meta:
        db_table = "mpr_opt"
        ordering = ["-fecha_creacion"]
        verbose_name = "OPT (Pedido de producción)"
        verbose_name_plural = "OPT (Pedidos de producción)"

    def __str__(self):
        return f"OPT #{self.id_lista_principal} ({self.base_empresa})"


class OptLinea(models.Model):
    """Línea de una OPT: vincula id_lista_produccion (MySQL) a una Opt."""

    opt = models.ForeignKey(Opt, on_delete=models.CASCADE, related_name="lineas")
    id_lista_produccion = models.BigIntegerField()
    id_articulo = models.IntegerField()
    cantidad_pedida = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = "mpr_opt_linea"
        ordering = ["id"]
        verbose_name = "Línea OPT"
        verbose_name_plural = "Líneas OPT"
        unique_together = [["opt", "id_lista_produccion"]]

    def __str__(self):
        return f"OPT {self.opt_id} · lista {self.id_lista_produccion} · art. {self.id_articulo}"


class MprConfig(models.Model):
    """
    Configuración MPR por base de datos (empresa).
    id_deposito_produccion: depósito donde se lleva el stock al liberar OPT (automático, sin selección).
    """
    base_empresa = models.CharField(max_length=64, unique=True, db_index=True)
    id_deposito_produccion = models.IntegerField(
        null=True,
        blank=True,
        help_text="Depósito de producción: donde se registra el stock al liberar la OPT (automático).",
    )

    class Meta:
        db_table = "mpr_config"
        verbose_name = "Configuración MPR"
        verbose_name_plural = "Configuraciones MPR"

    def __str__(self):
        return f"MPR config {self.base_empresa} (dep. prod. {self.id_deposito_produccion})"
