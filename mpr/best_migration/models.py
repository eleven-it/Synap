"""Modelos PostgreSQL (Synap) para paridad BEST → MPR. No tocan MySQL/Azure."""

from __future__ import annotations

from django.db import models
from django.utils import timezone


class BestArticuloMap(models.Model):
    """Mapeo 1:1 best_id_articulo → articulo.IDArt por base_empresa."""

    class OrigenRequerimiento(models.TextChoices):
        PEDIDO_ABIERTO = "PEDIDO_ABIERTO", "Pedido abierto"
        STOCK_DEPOSITO = "STOCK_DEPOSITO", "Saldo en depósito"
        BOM_FABRICADO = "BOM_FABRICADO", "BOM fabricado"
        HISTORICO = "HISTORICO", "Histórico / fuera de alcance"

    class Estado(models.TextChoices):
        INFERIDO_ALTO = "INFERIDO_ALTO", "Inferido alto"
        INFERIDO_MEDIO = "INFERIDO_MEDIO", "Inferido medio"
        INFERIDO_BAJO = "INFERIDO_BAJO", "Inferido bajo"
        AMBIGUO = "AMBIGUO", "Ambiguo"
        SIN_CANDIDATO = "SIN_CANDIDATO", "Sin candidato"
        SIN_MATCH = "SIN_MATCH", "Sin match confiable"
        CONFLICTO_1_A_N = "CONFLICTO_1_A_N", "Conflicto 1→N"
        VALIDADO = "VALIDADO", "Validado"
        DESCARTADO = "DESCARTADO", "Descartado (fuera de alcance)"

    base_empresa = models.CharField(max_length=64, db_index=True)
    best_id_articulo = models.CharField(max_length=32, db_index=True)
    best_codigo = models.CharField(max_length=64, blank=True, default="")
    best_articulo = models.CharField(max_length=255, blank=True, default="")
    best_marca = models.CharField(max_length=64, blank=True, default="")
    best_modelos = models.CharField(max_length=128, blank=True, default="")
    best_colores = models.CharField(max_length=64, blank=True, default="")
    best_color_mode = models.CharField(max_length=16, blank=True, default="")
    best_talle = models.CharField(max_length=8, blank=True, default="")
    best_pack = models.CharField(max_length=8, blank=True, default="")
    best_variant_codes = models.CharField(max_length=128, blank=True, default="")

    admin_idart = models.IntegerField(null=True, blank=True, db_index=True)
    admin_id_manual = models.CharField(max_length=64, blank=True, default="")
    admin_nombre = models.CharField(max_length=255, blank=True, default="")
    admin_cod_art_prov = models.CharField(max_length=128, blank=True, default="")
    admin_pack = models.CharField(max_length=8, blank=True, default="")
    admin_talle = models.CharField(max_length=8, blank=True, default="")
    admin_color_mode = models.CharField(max_length=16, blank=True, default="")

    estado = models.CharField(max_length=24, choices=Estado.choices, db_index=True)
    score = models.IntegerField(null=True, blank=True)
    razon = models.CharField(max_length=512, blank=True, default="")
    candidatos_n = models.PositiveIntegerField(default=0)
    alt1_idart = models.IntegerField(null=True, blank=True)
    alt1_nombre = models.CharField(max_length=255, blank=True, default="")
    alt1_score = models.IntegerField(null=True, blank=True)
    alt2_idart = models.IntegerField(null=True, blank=True)
    alt2_nombre = models.CharField(max_length=255, blank=True, default="")
    alt2_score = models.IntegerField(null=True, blank=True)
    dict_version = models.CharField(max_length=32, blank=True, default="")

    validado = models.BooleanField(default=False)
    validado_por = models.CharField(max_length=64, blank=True, default="")
    validado_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, default="")

    requerido_migracion = models.BooleanField(default=True, db_index=True)
    en_snapshot_abierto = models.BooleanField(default=True, db_index=True)
    origen_requerimiento = models.CharField(
        max_length=24,
        choices=OrigenRequerimiento.choices,
        default=OrigenRequerimiento.PEDIDO_ABIERTO,
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_articulo_map"
        verbose_name = "Mapeo artículo BEST"
        verbose_name_plural = "Mapeos artículos BEST"
        unique_together = [("base_empresa", "best_id_articulo")]
        indexes = [
            models.Index(fields=["base_empresa", "estado"]),
            models.Index(fields=["base_empresa", "validado"]),
        ]

    def __str__(self) -> str:
        return f"{self.best_id_articulo} → {self.admin_idart} ({self.estado})"

    @property
    def resuelto_para_migracion(self) -> bool:
        """VALIDADO con IDArt, o DESCARTADO (no migra esa línea)."""
        if self.estado == self.Estado.DESCARTADO:
            return True
        return self.validado and self.estado == self.Estado.VALIDADO and self.admin_idart is not None

    @property
    def categoria_migracion(self) -> str:
        """CUMPLE | NECESARIO_PENDIENTE | CUMPLE_STOCK | NECESARIO_STOCK | NO_NECESARIO | EXCLUIDO."""
        if self.estado == self.Estado.DESCARTADO:
            return "EXCLUIDO"
        if not self.requerido_migracion:
            return "NO_NECESARIO"
        es_stock = self.origen_requerimiento == self.OrigenRequerimiento.STOCK_DEPOSITO
        if self.resuelto_para_migracion:
            return "CUMPLE_STOCK" if es_stock else "CUMPLE"
        return "NECESARIO_STOCK" if es_stock else "NECESARIO_PENDIENTE"


class BestClienteMap(models.Model):
    """Mapeo cliente BEST → cliente.Codigo."""

    class OrigenRequerimiento(models.TextChoices):
        PEDIDO_ABIERTO = "PEDIDO_ABIERTO", "Pedido abierto"
        STOCK_DEPOSITO = "STOCK_DEPOSITO", "Saldo en depósito"
        HISTORICO = "HISTORICO", "Histórico / fuera de alcance"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        INFERIDO = "INFERIDO", "Inferido"
        AMBIGUO = "AMBIGUO", "Ambiguo"
        SIN_CANDIDATO = "SIN_CANDIDATO", "Sin candidato"
        VALIDADO = "VALIDADO", "Validado"
        DESCARTADO = "DESCARTADO", "Descartado"

    base_empresa = models.CharField(max_length=64, db_index=True)
    best_cliente = models.CharField(max_length=255)
    best_cuit = models.CharField(max_length=32, blank=True, default="")
    admin_codigo = models.IntegerField(null=True, blank=True)
    admin_nombre = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    score = models.IntegerField(null=True, blank=True)
    razon = models.CharField(max_length=255, blank=True, default="")
    alt1_codigo = models.IntegerField(null=True, blank=True)
    alt1_nombre = models.CharField(max_length=255, blank=True, default="")
    alt1_score = models.IntegerField(null=True, blank=True)
    ordenes_abiertas = models.PositiveIntegerField(default=0)
    validado = models.BooleanField(default=False)
    validado_por = models.CharField(max_length=64, blank=True, default="")
    validado_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, default="")

    requerido_migracion = models.BooleanField(default=True, db_index=True)
    en_snapshot_abierto = models.BooleanField(default=True, db_index=True)
    origen_requerimiento = models.CharField(
        max_length=24,
        choices=OrigenRequerimiento.choices,
        default=OrigenRequerimiento.PEDIDO_ABIERTO,
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_cliente_map"
        verbose_name = "Mapeo cliente BEST"
        verbose_name_plural = "Mapeos clientes BEST"
        unique_together = [("base_empresa", "best_cliente", "best_cuit")]

    def __str__(self) -> str:
        return f"{self.best_cliente} → {self.admin_codigo} ({self.estado})"

    @property
    def resuelto_para_migracion(self) -> bool:
        if self.estado == self.Estado.DESCARTADO:
            return True
        return self.validado and self.estado == self.Estado.VALIDADO and self.admin_codigo is not None

    @property
    def categoria_migracion(self) -> str:
        """CUMPLE | NECESARIO_PENDIENTE | NO_NECESARIO | EXCLUIDO."""
        if self.estado == self.Estado.DESCARTADO:
            return "EXCLUIDO"
        if not self.requerido_migracion:
            return "NO_NECESARIO"
        if self.resuelto_para_migracion:
            return "CUMPLE"
        return "NECESARIO_PENDIENTE"


class BestDepositoMap(models.Model):
    """Mapeo depósito BEST (Id Deposito / CC) → deposito.CodDeposito con tipo_mpr."""

    class OrigenRequerimiento(models.TextChoices):
        PEDIDO_ABIERTO = "PEDIDO_ABIERTO", "Pedido abierto"
        STOCK_DEPOSITO = "STOCK_DEPOSITO", "Saldo en depósito"
        HISTORICO = "HISTORICO", "Histórico / fuera de alcance"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        INFERIDO = "INFERIDO", "Inferido"
        VALIDADO = "VALIDADO", "Validado"
        DESCARTADO = "DESCARTADO", "Descartado"
        SIN_CANDIDATO = "SIN_CANDIDATO", "Sin candidato"

    base_empresa = models.CharField(max_length=64, db_index=True)
    best_id_deposito = models.IntegerField(db_index=True)
    best_nombre = models.CharField(max_length=255, blank=True, default="")
    tipo_mpr_esperado = models.CharField(max_length=32, blank=True, default="")
    admin_cod_deposito = models.IntegerField(null=True, blank=True, db_index=True)
    admin_nombre = models.CharField(max_length=255, blank=True, default="")
    admin_tipo_mpr = models.CharField(max_length=32, blank=True, default="")
    estado = models.CharField(
        max_length=24, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    score = models.IntegerField(null=True, blank=True)
    razon = models.CharField(max_length=512, blank=True, default="")
    requerido_migracion = models.BooleanField(default=True, db_index=True)
    en_snapshot_abierto = models.BooleanField(default=True, db_index=True)
    origen_requerimiento = models.CharField(
        max_length=24,
        choices=OrigenRequerimiento.choices,
        default=OrigenRequerimiento.STOCK_DEPOSITO,
    )
    validado = models.BooleanField(default=False)
    validado_por = models.CharField(max_length=64, blank=True, default="")
    validado_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_deposito_map"
        verbose_name = "Mapeo depósito BEST"
        verbose_name_plural = "Mapeos depósitos BEST"
        unique_together = [("base_empresa", "best_id_deposito")]
        indexes = [
            models.Index(fields=["base_empresa", "estado"]),
            models.Index(fields=["base_empresa", "validado"]),
        ]

    def __str__(self) -> str:
        return f"{self.best_id_deposito} → {self.admin_cod_deposito} ({self.estado})"

    @property
    def resuelto_para_migracion(self) -> bool:
        if self.estado == self.Estado.DESCARTADO:
            return True
        return (
            self.validado
            and self.estado == self.Estado.VALIDADO
            and self.admin_cod_deposito is not None
        )

    @property
    def categoria_migracion(self) -> str:
        if self.estado == self.Estado.DESCARTADO:
            return "EXCLUIDO"
        if not self.requerido_migracion:
            return "NO_NECESARIO"
        if self.resuelto_para_migracion:
            return "CUMPLE"
        return "NECESARIO_PENDIENTE"


class BestStockInicialMap(models.Model):
    """Línea de stock inicial BEST (artículo × depósito) → stock_deposito."""

    class OrigenRequerimiento(models.TextChoices):
        STOCK_DEPOSITO = "STOCK_DEPOSITO", "Saldo en depósito"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        LISTO = "LISTO", "Listo"
        SIN_MAPEO_ARTICULO = "SIN_MAPEO_ARTICULO", "Sin mapeo artículo"
        SIN_MAPEO_DEPOSITO = "SIN_MAPEO_DEPOSITO", "Sin mapeo depósito"
        CONCILIADO = "CONCILIADO", "Conciliado"
        CARGADO = "CARGADO", "Cargado"
        DESCARTADO = "DESCARTADO", "Descartado"

    base_empresa = models.CharField(max_length=64, db_index=True)
    best_id_articulo = models.CharField(max_length=32, db_index=True)
    best_articulo = models.CharField(max_length=255, blank=True, default="")
    best_id_deposito = models.IntegerField(db_index=True)
    best_deposito_nombre = models.CharField(max_length=255, blank=True, default="")
    best_stock_pares = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    best_docenas = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    admin_idart = models.IntegerField(null=True, blank=True, db_index=True)
    admin_nombre = models.CharField(max_length=255, blank=True, default="")
    admin_cod_deposito = models.IntegerField(null=True, blank=True, db_index=True)
    admin_deposito_nombre = models.CharField(max_length=255, blank=True, default="")
    admin_saldo_actual = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    delta_pares = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    estado = models.CharField(
        max_length=24, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    requerido_migracion = models.BooleanField(default=True, db_index=True)
    origen_requerimiento = models.CharField(
        max_length=24,
        choices=OrigenRequerimiento.choices,
        default=OrigenRequerimiento.STOCK_DEPOSITO,
    )
    validado = models.BooleanField(default=False)
    validado_por = models.CharField(max_length=64, blank=True, default="")
    validado_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_stock_inicial_map"
        verbose_name = "Stock inicial BEST"
        verbose_name_plural = "Stock inicial BEST"
        unique_together = [("base_empresa", "best_id_articulo", "best_id_deposito")]
        indexes = [
            models.Index(fields=["base_empresa", "estado"]),
            models.Index(fields=["base_empresa", "requerido_migracion"]),
        ]

    def __str__(self) -> str:
        return f"{self.best_id_articulo}@{self.best_id_deposito} ({self.estado})"

    @property
    def resuelto_para_migracion(self) -> bool:
        if self.estado in {
            self.Estado.DESCARTADO,
            self.Estado.CONCILIADO,
            self.Estado.CARGADO,
        }:
            return True
        return False

    @property
    def categoria_migracion(self) -> str:
        if self.estado == self.Estado.DESCARTADO:
            return "EXCLUIDO"
        if not self.requerido_migracion:
            return "NO_NECESARIO"
        if self.resuelto_para_migracion:
            return "CUMPLE"
        return "NECESARIO_PENDIENTE"


class BestOperarioMap(models.Model):
    """Diccionario letra/código tejedor BEST (TTNOTE) ↔ sue_abm_empleado."""

    class OrigenRequerimiento(models.TextChoices):
        REPORTE = "REPORTE", "Reportes / histórico"
        CATALOGO = "CATALOGO", "Catálogo BEST"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        INFERIDO = "INFERIDO", "Inferido"
        AMBIGUO = "AMBIGUO", "Ambiguo"
        VALIDADO = "VALIDADO", "Validado"
        DESCARTADO = "DESCARTADO", "Descartado"
        SIN_CANDIDATO = "SIN_CANDIDATO", "Sin candidato"

    base_empresa = models.CharField(max_length=64, db_index=True)
    best_codigo = models.CharField(max_length=16, db_index=True, help_text="Letra/código TTNOTE")
    best_nombre = models.CharField(max_length=255, blank=True, default="")
    movimientos_n = models.PositiveIntegerField(default=0)
    admin_id_operario = models.IntegerField(null=True, blank=True, db_index=True)
    admin_nombre = models.CharField(max_length=255, blank=True, default="")
    estado = models.CharField(
        max_length=24, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True
    )
    score = models.IntegerField(null=True, blank=True)
    razon = models.CharField(max_length=512, blank=True, default="")
    alt1_id_operario = models.IntegerField(null=True, blank=True)
    alt1_nombre = models.CharField(max_length=255, blank=True, default="")
    requerido_migracion = models.BooleanField(default=True, db_index=True)
    en_snapshot_abierto = models.BooleanField(default=True, db_index=True)
    origen_requerimiento = models.CharField(
        max_length=24,
        choices=OrigenRequerimiento.choices,
        default=OrigenRequerimiento.REPORTE,
    )
    validado = models.BooleanField(default=False)
    validado_por = models.CharField(max_length=64, blank=True, default="")
    validado_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_operario_map"
        verbose_name = "Mapeo operario/tejedor BEST"
        verbose_name_plural = "Mapeos operarios/tejedores BEST"
        unique_together = [("base_empresa", "best_codigo")]
        indexes = [
            models.Index(fields=["base_empresa", "estado"]),
            models.Index(fields=["base_empresa", "validado"]),
        ]

    def __str__(self) -> str:
        return f"{self.best_codigo} → {self.admin_id_operario} ({self.estado})"

    @property
    def resuelto_para_migracion(self) -> bool:
        if self.estado == self.Estado.DESCARTADO:
            return True
        return (
            self.validado
            and self.estado == self.Estado.VALIDADO
            and self.admin_id_operario is not None
        )

    @property
    def categoria_migracion(self) -> str:
        if self.estado == self.Estado.DESCARTADO:
            return "EXCLUIDO"
        if not self.requerido_migracion:
            return "NO_NECESARIO"
        if self.resuelto_para_migracion:
            return "CUMPLE"
        return "NECESARIO_PENDIENTE"


class BestMigrationParity(models.Model):
    """Estado de paridad por dominio y gate de migración de pedidos."""

    base_empresa = models.CharField(max_length=64, unique=True, db_index=True)
    # Contadores de gate: solo filas con requerido_migracion=True
    articulos_total = models.PositiveIntegerField(default=0)
    articulos_resueltos = models.PositiveIntegerField(default=0)
    articulos_ok = models.BooleanField(default=False)
    clientes_total = models.PositiveIntegerField(default=0)
    clientes_resueltos = models.PositiveIntegerField(default=0)
    clientes_ok = models.BooleanField(default=False)
    depositos_total = models.PositiveIntegerField(default=0)
    depositos_resueltos = models.PositiveIntegerField(default=0)
    stock_inicial_total = models.PositiveIntegerField(default=0)
    stock_inicial_resueltos = models.PositiveIntegerField(default=0)
    unidades_ok = models.BooleanField(
        default=False,
        help_text="Confirmación manual: cantidades en pares.",
    )
    depositos_ok = models.BooleanField(default=False)
    stock_inicial_ok = models.BooleanField(default=False)
    operarios_ok = models.BooleanField(default=False)
    migracion_habilitada = models.BooleanField(default=False)
    ultimo_recalculo_articulos = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.CharField(max_length=500, blank=True, default="")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mpr_best_migration_parity"
        verbose_name = "Paridad migración BEST"
        verbose_name_plural = "Paridades migración BEST"

    def __str__(self) -> str:
        gate = "habilitada" if self.migracion_habilitada else "bloqueada"
        return f"Paridad BEST {self.base_empresa} ({gate})"

    def refresh_gate(self) -> None:
        """Habilita migración solo si dominios obligatorios están OK."""
        self.articulos_ok = (
            self.articulos_total > 0 and self.articulos_resueltos >= self.articulos_total
        )
        self.clientes_ok = (
            self.clientes_total > 0 and self.clientes_resueltos >= self.clientes_total
        )
        self.depositos_ok = (
            self.depositos_total > 0 and self.depositos_resueltos >= self.depositos_total
        )
        self.stock_inicial_ok = (
            self.stock_inicial_total > 0
            and self.stock_inicial_resueltos >= self.stock_inicial_total
        )
        # unidades_ok es checklist manual hasta automatizar
        # depositos/stock_inicial son opcionales para el gate de pedidos
        self.migracion_habilitada = bool(
            self.articulos_ok and self.clientes_ok and self.unidades_ok
        )
        self.actualizado_en = timezone.now()
