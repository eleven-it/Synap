# MPR - Modelos para agrupar OPT (Pedidos de producción) con múltiples artículos.
# La OPT se representa en MySQL en lista_produccion_agrupada (codigo_movimiento_opt, id_operario_opt; id_opt heredado opcional).
# Opt y OptLinea están en desuso (managed=False); los datos viven en MySQL, no en Django.
import uuid
from django.db import models


# Constantes de modo de armado
MODO_ARMADO_1RA = "1ra"
MODO_ARMADO_2DA = "2da"
MODO_ARMADO_CHOICES = [
    (MODO_ARMADO_1RA, "Armado 1ra"),
    (MODO_ARMADO_2DA, "Armado 2da"),
]

# Constantes de estado de imputación
ESTADO_IMPUTACION_PENDIENTE = "pendiente"
ESTADO_IMPUTACION_PARCIAL = "parcial"
ESTADO_IMPUTACION_COMPLETO = "completo"
ESTADO_IMPUTACION_NA = "na"
ESTADO_IMPUTACION_CHOICES = [
    (ESTADO_IMPUTACION_PENDIENTE, "Pendiente"),
    (ESTADO_IMPUTACION_PARCIAL, "Parcial"),
    (ESTADO_IMPUTACION_COMPLETO, "Completo"),
    (ESTADO_IMPUTACION_NA, "No aplica"),
]

# Constantes de origen de regla de imputación
ORIGEN_REGLA_FIFO = "FIFO"
ORIGEN_REGLA_MANUAL = "MANUAL"
ORIGEN_REGLA_CHOICES = [
    (ORIGEN_REGLA_FIFO, "FIFO"),
    (ORIGEN_REGLA_MANUAL, "Manual"),
]


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


class MprArmadoLote(models.Model):
    """Lote de armado (1ra o 2da) ejecutado en una sesión POS."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_empresa = models.CharField(max_length=64, db_index=True)
    modo = models.CharField(
        max_length=3,
        choices=MODO_ARMADO_CHOICES,
        help_text="Modo de armado: 1ra (Semi → Terminado 1ra) o 2da (2da selección → Terminado 2da)",
    )
    id_operario = models.IntegerField(null=True, blank=True)
    id_usuario = models.IntegerField(
        help_text="Usuario que ejecutó el lote de armado"
    )
    deposito_origen = models.IntegerField()
    deposito_destino = models.IntegerField()
    ejecutado_en = models.DateTimeField(auto_now_add=True)
    cantidad_items = models.IntegerField(
        default=0,
        help_text="Cantidad total de ítems en el lote",
    )
    cantidad_exitosos = models.IntegerField(
        default=0,
        help_text="Cantidad de ítems exitosos",
    )
    cantidad_fallidos = models.IntegerField(
        default=0,
        help_text="Cantidad de ítems fallidos",
    )

    class Meta:
        verbose_name = "Lote de armado"
        verbose_name_plural = "Lotes de armado"
        ordering = ["-ejecutado_en"]
        indexes = [
            models.Index(fields=["base_empresa", "modo"]),
            models.Index(fields=["ejecutado_en"]),
        ]

    def __str__(self):
        return f"Lote {self.modo} {self.id} · {self.cantidad_exitosos}/{self.cantidad_items} exitosos"


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
    modo = models.CharField(
        max_length=3,
        choices=MODO_ARMADO_CHOICES,
        default=MODO_ARMADO_2DA,
        help_text="Modo de armado: 1ra o 2da",
    )
    id_lote_armado = models.ForeignKey(
        MprArmadoLote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
        help_text="Lote de armado al que pertenece este movimiento",
    )
    estado_imputacion = models.CharField(
        max_length=10,
        choices=ESTADO_IMPUTACION_CHOICES,
        default=ESTADO_IMPUTACION_NA,
        help_text="Estado de imputación a pedidos (solo para modo 1ra)",
    )

    class Meta:
        verbose_name = "Movimiento armado surtido"
        verbose_name_plural = "Movimientos armado surtido"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["base_empresa", "codigo_movimiento"]),
            models.Index(fields=["modo", "estado_imputacion"]),
        ]

    def __str__(self):
        return f"Armado {self.modo} {self.codigo_movimiento} · {self.cantidad_packs} packs"


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


class MprImputacionArmado(models.Model):
    """Imputación de un MSTOCK de armado 1ra a un pedido de producción (supervisor)."""

    base_empresa = models.CharField(max_length=64, db_index=True)
    codigo_movimiento = models.IntegerField(
        db_index=True,
        help_text="CodigoMovimiento del MSTOCK de armado 1ra",
    )
    id_articulo_pack = models.IntegerField(
        help_text="IDArt del pack armado"
    )
    cantidad = models.IntegerField(
        help_text="Unidades imputadas en esta línea"
    )
    codigo_movimiento_pedido = models.IntegerField(
        help_text="CodigoMovimiento del comprobante de pedido (comp_ped)",
    )
    id_lista_detalle = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID de lista_produccion_detalle si aplica",
    )
    origen_regla = models.CharField(
        max_length=10,
        choices=ORIGEN_REGLA_CHOICES,
        help_text="Origen de la regla de imputación: FIFO o Manual",
    )
    id_usuario_supervisor = models.IntegerField(
        help_text="Usuario supervisor que confirmó la imputación"
    )
    imputado_en = models.DateTimeField(auto_now_add=True)
    notas = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Notas opcionales de ajuste manual",
    )

    class Meta:
        verbose_name = "Imputación de armado 1ra"
        verbose_name_plural = "Imputaciones de armado 1ra"
        ordering = ["-imputado_en"]
        indexes = [
            models.Index(fields=["base_empresa", "codigo_movimiento"]),
            models.Index(fields=["codigo_movimiento_pedido"]),
            models.Index(fields=["imputado_en"]),
        ]

    def __str__(self):
        return f"Imputación MSTOCK {self.codigo_movimiento} → Pedido {self.codigo_movimiento_pedido} · {self.cantidad} u."


class MprTurno(models.Model):
    """
    Turno de producción global por empresa.
    Ej: Mañana 06:00-14:00, Tarde 14:00-22:00, Noche 22:00-06:00.
    Turnos nocturnos (hora_fin < hora_inicio) cruzan medianoche — se permiten.
    """

    base_empresa = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Scope por empresa (ej. Empresa1).",
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del turno (ej. Mañana, Tarde, Noche).",
    )
    hora_inicio = models.TimeField(
        help_text="Hora de inicio del turno (formato HH:MM).",
    )
    hora_fin = models.TimeField(
        help_text="Hora de finalización del turno. Si < hora_inicio, cruza medianoche.",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Flag de activación. Turnos inactivos no se ofrecen en nuevas asignaciones.",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp de creación.",
    )

    class Meta:
        verbose_name = "Turno de producción"
        verbose_name_plural = "Turnos de producción"
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "nombre"],
                name="mpr_turno_nombre_unico_empresa",
            ),
        ]
        indexes = [
            models.Index(fields=["base_empresa", "activo"], name="mpr_turno_empresa_activo_idx"),
        ]
        ordering = ["base_empresa", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')})"


class MprRosterDia(models.Model):
    """
    Asignación de turno a un operario en una fecha específica.
    Constraint único: un operario solo puede tener un turno por fecha en la misma empresa.
    """

    base_empresa = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Scope por empresa.",
    )
    fecha = models.DateField(
        help_text="Fecha de la asignación (YYYY-MM-DD).",
    )
    id_operario = models.IntegerField(
        help_text="FK lógico a sue_abm_empleado.id_sue_abm_empleado.",
    )
    turno = models.ForeignKey(
        MprTurno,
        on_delete=models.PROTECT,
        related_name="asignaciones_roster",
        help_text="Turno asignado. PROTECT: no permitir eliminar turno si tiene asignaciones.",
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp de creación.",
    )

    class Meta:
        verbose_name = "Asignación de turno (roster)"
        verbose_name_plural = "Asignaciones de turno (roster)"
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "fecha", "id_operario"],
                name="mpr_roster_dia_unico_operario_fecha",
            ),
        ]
        indexes = [
            models.Index(fields=["base_empresa", "fecha"], name="mpr_roster_emp_fecha_idx"),
        ]
        ordering = ["base_empresa", "fecha", "id_operario"]

    def __str__(self):
        return f"Operario {self.id_operario} - {self.fecha.strftime('%d/%m/%Y')} - Turno {self.turno.nombre}"


# ---------------------------------------------------------------------------
# ETAPA 4: Parte de Producción (Ledger OPP-parte)
# ---------------------------------------------------------------------------

class MprParte(models.Model):
    """Parte de producción: cabecera ledger-only por fecha y turno."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_empresa = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Scope por empresa.",
    )
    fecha_produccion = models.DateField(
        help_text="Fecha de producción. Puede ser pasada (registro diferido). UI: dd/MM/yyyy.",
    )
    turno = models.ForeignKey(
        MprTurno,
        on_delete=models.PROTECT,
        related_name="partes",
        help_text="Turno de producción. PROTECT: no eliminar si hay partes.",
    )
    id_usuario = models.IntegerField(
        help_text="Usuario que registró el parte en Synap.",
    )
    registrado_en = models.DateTimeField(auto_now_add=True)
    notas = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Notas opcionales del parte.",
    )
    movimiento_fisico_ok = models.BooleanField(
        default=False,
        help_text="True si el asiento físico MySQL (MSTOCK OPP + stock_deposito) fue confirmado.",
    )
    id_lista_produccion = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID de la OPT activa (lista_produccion_agrupada.id_lista_produccion) al momento de registrar el parte. Capturado best-effort para trazabilidad E6.",
    )

    class Meta:
        verbose_name = "Parte de producción"
        verbose_name_plural = "Partes de producción"
        indexes = [
            models.Index(
                fields=["base_empresa", "fecha_produccion"],
                name="mpr_parte_emp_fecha_idx",
            ),
            models.Index(
                fields=["base_empresa", "turno_id"],
                name="mpr_parte_emp_turno_idx",
            ),
        ]
        ordering = ["-registrado_en"]

    def __str__(self):
        return (
            f"Parte {self.fecha_produccion.strftime('%d/%m/%Y')}"
            f" · {self.turno.nombre} ({self.base_empresa})"
        )


class MprParteLinea(models.Model):
    """Línea de parte de producción: cantidad por (pack, operario)."""

    parte = models.ForeignKey(
        MprParte,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    id_articulo = models.IntegerField(
        help_text="ID artículo nivel COMPONENTE (desde grilla Fabricando, E8).",
    )
    id_operario = models.IntegerField(
        help_text="FK lógico a sue_abm_empleado.id_sue_abm_empleado.",
    )
    operario_nombre = models.CharField(
        max_length=255,
        default="-",
        help_text="Snapshot de nombre_empleado al momento del registro. No se actualiza.",
    )
    cantidad = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        verbose_name = "Línea de parte de producción"
        verbose_name_plural = "Líneas de parte de producción"
        constraints = [
            models.UniqueConstraint(
                fields=["parte", "id_articulo", "id_operario"],
                name="mpr_parte_linea_unico",
            ),
        ]
        ordering = ["id_articulo", "id_operario"]

    def __str__(self):
        return (
            f"Parte {self.parte_id} · art. {self.id_articulo}"
            f" · op. {self.id_operario} = {self.cantidad}"
        )


class MprParteAjuste(models.Model):
    """Ajuste delta append-only sobre una línea de parte de producción."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parte = models.ForeignKey(
        MprParte,
        on_delete=models.PROTECT,
        related_name="ajustes",
        help_text="PROTECT: no eliminar cabecera si existen ajustes.",
    )
    id_articulo = models.IntegerField()
    id_operario = models.IntegerField()
    delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Delta positivo o negativo. Cantidad efectiva = linea.cantidad + Σdeltas.",
    )
    motivo = models.CharField(max_length=255)
    id_usuario = models.IntegerField()
    registrado_en = models.DateTimeField(auto_now_add=True)
    ajuste_fisico_ok = models.BooleanField(
        default=False,
        help_text="True si el delta físico MySQL (stock_deposito) fue confirmado.",
    )

    class Meta:
        verbose_name = "Ajuste de parte de producción"
        verbose_name_plural = "Ajustes de parte de producción"
        indexes = [
            models.Index(
                fields=["parte", "id_articulo", "id_operario"],
                name="mpr_parte_ajuste_linea_idx",
            ),
        ]
        ordering = ["registrado_en"]

    def __str__(self):
        signo = "+" if self.delta >= 0 else ""
        return f"Ajuste {signo}{self.delta} art. {self.id_articulo} op. {self.id_operario}"


class MprTransicionLote(models.Model):
    """Registro de trazabilidad para transferencias de stock entre etapas MPR.

    Cada fila representa una transferencia física entre dos depósitos MPR
    (ej. Producción → Planchado) ejecutada por ``transferir_stock_entre_etapas``.
    """

    base_empresa = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Scope por empresa (base_empresa de AdministraNET).",
    )
    id_articulo = models.IntegerField(
        help_text="ID componente (nivel al que opera la transición, ya explotado).",
    )
    tipo_origen = models.CharField(
        max_length=64,
        help_text="Etapa de origen (constante TIPO_MPR_*, ej. 'Produccion').",
    )
    tipo_destino = models.CharField(
        max_length=64,
        help_text="Etapa de destino (constante TIPO_MPR_*, ej. 'Planchado').",
    )
    cantidad = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Cantidad transferida en unidades del componente.",
    )
    codigo_movimiento = models.IntegerField(
        null=True,
        blank=True,
        help_text="CodigoMovimiento MSTOCK de la transición en MySQL legacy.",
    )
    id_usuario = models.IntegerField(
        help_text="ID usuario de AdministraNET que realizó la transición.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transición de lote MPR"
        verbose_name_plural = "Transiciones de lote MPR"
        indexes = [
            models.Index(
                fields=["base_empresa", "id_articulo"],
                name="mpr_tl_emp_art_idx",
            ),
            models.Index(
                fields=["base_empresa", "creado_en"],
                name="mpr_tl_emp_fecha_idx",
            ),
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return (
            f"Transición {self.tipo_origen}→{self.tipo_destino}"
            f" art.{self.id_articulo} qty={self.cantidad}"
            f" ({self.base_empresa})"
        )


class MprEnvioProduccion(models.Model):
    """Ledger de envíos directos a producción desde el tablero, nivel COMPONENTE.

    Registro append-only. No escribe en tablas MySQL legacy ni en stock_deposito.
    Contribuye a la columna 'Enviado' del tablero via la fórmula E7:
        Enviado_tablero = max(0, SUM(envíos_tablero) − stock_produccion)
    """

    base_empresa = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Scope por empresa (base_empresa de AdministraNET).",
    )
    id_articulo = models.IntegerField(
        help_text="ID artículo nivel COMPONENTE (ya explotado, no PACK).",
    )
    cantidad = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Cantidad enviada en unidades del componente.",
    )
    id_usuario = models.IntegerField(
        help_text="ID usuario AdministraNET que realizó el envío.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    anulado = models.BooleanField(
        default=False,
        help_text="True si el envío fue anulado (solo desde admin Django en E7).",
    )

    class Meta:
        verbose_name = "Envío a producción desde tablero"
        verbose_name_plural = "Envíos a producción desde tablero"
        indexes = [
            models.Index(
                fields=["base_empresa", "id_articulo"],
                name="mpr_ep_emp_art_idx",
            ),
            models.Index(
                fields=["base_empresa", "creado_en"],
                name="mpr_ep_emp_fecha_idx",
            ),
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return (
            f"Envío tablero art.{self.id_articulo} qty={self.cantidad}"
            f" ({self.base_empresa})"
        )
