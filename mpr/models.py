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


class MprArticuloArmadoSurtido(models.Model):
    """Artículos pack habilitados para armado surtido (config MPR en Synap)."""

    base_empresa = models.CharField(max_length=64, db_index=True)
    id_articulo = models.IntegerField()
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pack habilitado armado surtido"
        verbose_name_plural = "Packs habilitados armado surtido"
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "id_articulo"],
                name="mpr_art_armado_surtido_empresa_art",
            ),
        ]
        ordering = ["base_empresa", "id_articulo"]

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return f"{self.base_empresa} · art. {self.id_articulo} ({estado})"


class MprArmadoSurtidoMovimiento(models.Model):
    """Cabecera de trazabilidad Synap por armado surtido (vínculo con movimiento_stock legacy)."""

    base_empresa = models.CharField(max_length=64, db_index=True)
    codigo_movimiento = models.IntegerField(db_index=True)
    id_articulo_pack = models.IntegerField()
    cantidad_packs = models.IntegerField()
    deposito_origen = models.IntegerField()
    deposito_destino = models.IntegerField()
    id_lista_produccion = models.IntegerField(null=True, blank=True)
    id_operario = models.IntegerField(null=True, blank=True)
    id_usuario = models.IntegerField()
    detalle = models.CharField(max_length=500, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento armado surtido"
        verbose_name_plural = "Movimientos armado surtido"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["base_empresa", "codigo_movimiento"]),
        ]

    def __str__(self):
        return f"Armado surtido {self.codigo_movimiento} · {self.cantidad_packs} packs"


class MprArmadoSurtidoLinea(models.Model):
    """Línea de composición por movimiento de armado surtido."""

    movimiento = models.ForeignKey(
        MprArmadoSurtidoMovimiento,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    id_articulo_componente = models.IntegerField()
    codigo_articulo = models.CharField(max_length=64, blank=True, default="-")
    descripcion_articulo = models.CharField(max_length=255, blank=True, default="-")
    cantidad_por_pack = models.IntegerField()
    cantidad_total = models.IntegerField()

    class Meta:
        verbose_name = "Línea composición armado surtido"
        verbose_name_plural = "Líneas composición armado surtido"
        ordering = ["id"]

    def __str__(self):
        return f"Comp. {self.id_articulo_componente} × {self.cantidad_por_pack}/pack"
