from decimal import Decimal

from django.db import models


class EcomMigrationCheckpoint(models.Model):
    """Marca de avance por submódulo migrado desde PHP (PostgreSQL)."""

    module_slug = models.SlugField("módulo", max_length=64, unique=True, db_index=True)
    notes = models.TextField("notas", blank=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "checkpoint de migración e-com"
        verbose_name_plural = "checkpoints de migración e-com"

    def __str__(self) -> str:
        return self.module_slug


class EcomMailQueue(models.Model):
    """Cola async de envío de mails para relays e-com."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_PENDING, "pendiente"),
        (STATUS_SENT, "enviado"),
        (STATUS_ERROR, "error"),
    )

    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)
    status = models.CharField("estado", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField("intentos", default=0)
    last_error = models.TextField("último error", blank=True)

    base_empresa = models.CharField("base empresa", max_length=64, db_index=True)
    to_email = models.EmailField("destinatario")
    subject = models.CharField("asunto", max_length=255)
    body_text = models.TextField("cuerpo texto")
    body_html = models.TextField("cuerpo html", blank=True)
    payload_json = models.JSONField("payload", default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "cola mail e-com"
        verbose_name_plural = "cola mails e-com"

    def __str__(self) -> str:
        return f"{self.to_email} [{self.status}]"


class EcomCart(models.Model):
    """
    Carrito mayorista (borrador) persistido en Postgres `synap`.

    Fase P1: sin escritura a MySQL legacy. El precio del renglón se calcula con el
    motor único (`price_rules_engine`) y el stock se valida contra MySQL vía
    `self_checkout.StockService`. El checkout (P2) recalcula precios como autoridad final.
    """

    ESTADO_BORRADOR = "borrador"
    ESTADO_CONFIRMADO = "confirmado"
    ESTADO_CHOICES = (
        (ESTADO_BORRADOR, "borrador"),
        (ESTADO_CONFIRMADO, "confirmado"),
    )

    TIPO_PEDIDO = "PED"
    TIPO_PRESUPUESTO = "PRE"
    TIPO_DEVOLUCION = "DEV"
    TIPO_CHOICES = (
        (TIPO_PEDIDO, "Pedido"),
        (TIPO_PRESUPUESTO, "Presupuesto"),
        (TIPO_DEVOLUCION, "Devolución"),
    )

    base_empresa = models.CharField("base empresa", max_length=64, db_index=True)
    id_usuario = models.IntegerField("usuario (vendedor)", db_index=True)
    idcliente = models.IntegerField("cliente", null=True, blank=True)
    lista_id = models.IntegerField("lista de precio", default=1)
    id_deposito = models.IntegerField("depósito", default=1)
    iva_incluido = models.BooleanField("IVA incluido", default=True)
    tipo_comprobante = models.CharField(
        "tipo comprobante", max_length=3, choices=TIPO_CHOICES, default=TIPO_PEDIDO
    )
    estado = models.CharField(
        "estado", max_length=16, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR, db_index=True
    )
    descuento_pie_pct = models.DecimalField("descuento al pie %", max_digits=6, decimal_places=2, default=Decimal("0"))

    # Resultado del checkout (P2): comprobante legacy generado (idempotencia)
    codigo_movimiento = models.BigIntegerField("CodigoMovimiento", null=True, blank=True)
    nro_comprobante = models.CharField("nro comprobante", max_length=32, blank=True, default="")
    autorizacion = models.CharField("autorización", max_length=16, blank=True, default="")
    confirmed_at = models.DateTimeField("confirmado el", null=True, blank=True)

    # Totales denormalizados (recalculados en cada operación)
    neto_gravado_21 = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    neto_gravado_105 = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    iva_21 = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    iva_105 = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    exento = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    impuesto_interno_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    subtotal_neto = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "carrito mayorista"
        verbose_name_plural = "carritos mayorista"
        indexes = [
            models.Index(fields=["base_empresa", "id_usuario", "estado"]),
        ]

    def __str__(self) -> str:
        return f"Carrito #{self.pk} ({self.base_empresa}/{self.id_usuario})"


class EcomCartItem(models.Model):
    """Renglón de un carrito mayorista. Un renglón por artículo (se consolida cantidad)."""

    cart = models.ForeignKey(EcomCart, related_name="items", on_delete=models.CASCADE)
    id_articulo = models.IntegerField("artículo", db_index=True)
    codigo = models.CharField("código", max_length=64, blank=True, default="")
    id_manual = models.CharField("código manual", max_length=64, blank=True, default="")
    descripcion = models.CharField("descripción", max_length=255, blank=True, default="")

    cantidad = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0"))
    precio_unitario_neto = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    alicuota_iva = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("21"))
    impuesto_interno_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    porcentaje_descuento = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    lista_id = models.IntegerField(default=1)

    promocion = models.CharField(max_length=8, blank=True, default="")
    promocion_tipo = models.CharField(max_length=64, blank=True, default="")
    promocion_por = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    promocion_cant = models.IntegerField(default=0)

    orden = models.IntegerField(default=0)

    tipo_unidad = models.CharField("tipo unidad", max_length=16, blank=True, default="Unidad")
    cantidad_dividir = models.DecimalField(
        "cantidad dividir", max_digits=14, decimal_places=3, default=Decimal("1")
    )

    # Totales del renglón
    neto = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    iva = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "renglón carrito mayorista"
        verbose_name_plural = "renglones carrito mayorista"
        constraints = [
            models.UniqueConstraint(fields=["cart", "id_articulo"], name="uniq_ecomcartitem_cart_articulo"),
        ]

    def __str__(self) -> str:
        return f"{self.descripcion} x{self.cantidad}"


class EcomCatalogoRestriccionPV(models.Model):
    """
    Restricción de catálogo por punto de venta (config en BD, Postgres synap).

    Reemplaza el baneo legacy hardcodeado (listas `lista_baneo_productos_fiscal/no_fiscal`
    en sesión, aplicadas según `punto_venta.cont`). Genérico: por PV concreto se puede
    excluir por artículo/rubro/subrubro/categoría. Se aplica al listado y export del catálogo.
    """

    TIPO_ARTICULO = "articulo"
    TIPO_RUBRO = "rubro"
    TIPO_SUBRUBRO = "subrubro"
    TIPO_CATEGORIA = "categoria"
    TIPO_CHOICES = (
        (TIPO_ARTICULO, "Artículo"),
        (TIPO_RUBRO, "Rubro"),
        (TIPO_SUBRUBRO, "Sub rubro"),
        (TIPO_CATEGORIA, "Categoría"),
    )

    base_empresa = models.CharField("base empresa", max_length=64, db_index=True)
    id_punto_venta = models.IntegerField("punto de venta", db_index=True)
    tipo = models.CharField("tipo", max_length=16, choices=TIPO_CHOICES, default=TIPO_ARTICULO)
    valor_id = models.IntegerField("id excluido")
    activo = models.BooleanField("activo", default=True)
    nota = models.CharField("nota", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "restricción de catálogo por PV"
        verbose_name_plural = "restricciones de catálogo por PV"
        indexes = [
            models.Index(fields=["base_empresa", "id_punto_venta", "activo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "id_punto_venta", "tipo", "valor_id"],
                name="uniq_ecom_restriccion_pv",
            ),
        ]

    def __str__(self) -> str:
        return f"PV {self.id_punto_venta} excluye {self.tipo}={self.valor_id}"


class EcomPedidoMasivoDraft(models.Model):
    """
    Borrador de pedido masivo por sucursales (matriz packs × cliente_domicilio).

    Persistido en Postgres `synap`. El checkout batch (Phase 5) genera 1 PED MySQL
    por sucursal; ante fallo el draft vuelve a BORRADOR con ``ultimo_error``.
    """

    ESTADO_BORRADOR = "borrador"
    ESTADO_CONFIRMANDO = "confirmando"
    ESTADO_CONFIRMADO = "confirmado"
    ESTADO_ARCHIVADO = "archivado"
    ESTADO_ANULADO = "anulado"
    ESTADO_CHOICES = (
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_CONFIRMANDO, "Confirmando"),
        (ESTADO_CONFIRMADO, "Confirmado"),
        (ESTADO_ARCHIVADO, "Archivado"),
        (ESTADO_ANULADO, "Anulado"),
    )

    ESTADO_APROBACION_LOTE_NEUTRO = "-"
    ESTADO_APROBACION_LOTE_PENDIENTE = "pendiente"
    ESTADO_APROBACION_LOTE_APROBADO = "aprobado"
    ESTADO_APROBACION_LOTE_RECHAZADO = "rechazado"
    ESTADO_APROBACION_LOTE_ERROR = "error"
    ESTADO_APROBACION_LOTE_CHOICES = (
        (ESTADO_APROBACION_LOTE_NEUTRO, "Sin aprobación comercial"),
        (ESTADO_APROBACION_LOTE_PENDIENTE, "Pendiente"),
        (ESTADO_APROBACION_LOTE_APROBADO, "Aprobado"),
        (ESTADO_APROBACION_LOTE_RECHAZADO, "Rechazado"),
        (ESTADO_APROBACION_LOTE_ERROR, "Error"),
    )

    MODO_MASIVO = "masivo"
    MODO_SIMPLE = "simple"
    MODO_CHOICES = (
        (MODO_MASIVO, "Masivo"),
        (MODO_SIMPLE, "Simple"),
    )

    base_empresa = models.CharField("base empresa", max_length=64, db_index=True)
    id_usuario = models.IntegerField("usuario", db_index=True)
    cod_viajante = models.IntegerField("CodViajante", null=True, blank=True)
    id_cliente = models.IntegerField("cliente", db_index=True)
    estado = models.CharField(
        "estado",
        max_length=16,
        choices=ESTADO_CHOICES,
        default=ESTADO_BORRADOR,
        db_index=True,
    )
    ultimo_error = models.JSONField("último error por sucursal", default=dict, blank=True)
    codigos_movimiento = models.JSONField(
        "CodigoMovimiento del lote",
        default=list,
        blank=True,
        help_text="Lista de CodigoMovimiento PED creados al confirmar.",
    )
    estado_aprobacion_lote = models.CharField(
        "estado aprobación comercial del lote",
        max_length=16,
        choices=ESTADO_APROBACION_LOTE_CHOICES,
        default=ESTADO_APROBACION_LOTE_NEUTRO,
        db_index=True,
    )
    descuento_pie_pct = models.DecimalField(
        "descuento pie lote %",
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
    )
    descuentos_fila = models.JSONField(
        "descuentos % por artículo (id_articulo → pct)",
        default=dict,
        blank=True,
    )
    precios_fila = models.JSONField(
        "precios unitarios netos por artículo (id_articulo → decimal)",
        default=dict,
        blank=True,
    )
    cod_mov_origen = models.IntegerField(
        "CodigoMovimiento PED origen",
        null=True,
        blank=True,
        help_text="PED pendiente cargado para edición anula+crea (modo simple).",
    )
    modo = models.CharField(
        "modo captura",
        max_length=16,
        choices=MODO_CHOICES,
        default=MODO_MASIVO,
        db_index=True,
    )
    id_domicilio_fijo = models.IntegerField(
        "cliente_domicilio fijo",
        null=True,
        blank=True,
        help_text="Única columna en modo simple (id_cliente_domicilio).",
    )
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "borrador pedido masivo"
        verbose_name_plural = "borradores pedido masivo"
        indexes = [
            models.Index(fields=["base_empresa", "id_usuario", "estado"]),
            models.Index(fields=["base_empresa", "id_cliente", "estado"]),
        ]

    def __str__(self) -> str:
        return f"MasivoDraft #{self.pk} cliente={self.id_cliente} [{self.estado}]"


class EcomPedidoMasivoDraftCelda(models.Model):
    """Celda de la matriz: artículo × sucursal (cliente_domicilio) → cantidad en packs."""

    draft = models.ForeignKey(
        EcomPedidoMasivoDraft,
        related_name="celdas",
        on_delete=models.CASCADE,
    )
    id_articulo = models.IntegerField("artículo", db_index=True)
    id_cliente_domicilio = models.IntegerField("cliente_domicilio", db_index=True)
    cantidad_packs = models.DecimalField(
        "cantidad packs",
        max_digits=14,
        decimal_places=3,
        default=Decimal("0"),
    )
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "celda pedido masivo"
        verbose_name_plural = "celdas pedido masivo"
        constraints = [
            models.UniqueConstraint(
                fields=["draft", "id_articulo", "id_cliente_domicilio"],
                name="uniq_ecom_masivo_celda_draft_art_dom",
            ),
        ]

    def __str__(self) -> str:
        return f"art={self.id_articulo} dom={self.id_cliente_domicilio} x{self.cantidad_packs}"
