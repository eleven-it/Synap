# MPR - Modelos para agrupar OPT (Pedidos de producción) con múltiples artículos.
# La OPT se representa en MySQL en lista_produccion_agrupada (codigo_movimiento_opt, id_operario_opt; id_opt heredado opcional).
# Opt y OptLinea están en desuso (managed=False); los datos viven en MySQL, no en Django.
from django.db import models


class Opt(models.Model):
    """Cabecera de un Pedido de producción (OPT). En desuso: datos en lista_produccion_agrupada (MySQL)."""

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
        managed = False
        db_table = "mpr_opt"
        ordering = ["-fecha_creacion"]
        verbose_name = "OPT (Pedido de producción)"
        verbose_name_plural = "OPT (Pedidos de producción)"

    def __str__(self):
        return f"OPT #{self.id_lista_principal} ({self.base_empresa})"


class OptLinea(models.Model):
    """Línea de una OPT. En desuso: datos en lista_produccion_agrupada (MySQL, codigo_movimiento_opt, id_operario_opt)."""

    opt = models.ForeignKey(Opt, on_delete=models.CASCADE, related_name="lineas")
    id_lista_produccion = models.BigIntegerField()
    id_articulo = models.IntegerField()
    cantidad_pedida = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    id_operario_opt = models.IntegerField(
        null=True,
        blank=True,
        help_text="id_sue_abm_empleado del operario que fabrica esta línea.",
    )

    class Meta:
        managed = False
        db_table = "mpr_opt_linea"
        ordering = ["id"]
        verbose_name = "Línea OPT"
        verbose_name_plural = "Líneas OPT"
        unique_together = [["opt", "id_lista_produccion"]]

    def __str__(self):
        return f"OPT {self.opt_id} · lista {self.id_lista_produccion} · art. {self.id_articulo}"
