"""Modelos PostgreSQL del módulo de migración AdministraNET → Odoo."""

from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from odoo_migracion.services.crypto import decrypt_secret, encrypt_secret, mask_secret


class OdooConnection(models.Model):
    """Conexión destino Odoo 19 (JSON-2) asociada a una base MySQL origen."""

    class ApiMode(models.TextChoices):
        JSON2 = "json2", _("JSON-2")
        XMLRPC = "xmlrpc", _("XML-RPC (legacy)")

    nombre = models.CharField(_("Nombre"), max_length=120)
    base_empresa = models.CharField(
        _("Base empresa AdministraNET"),
        max_length=64,
        db_index=True,
        help_text=_("Nombre de la base MySQL de origen (base_empresa)."),
    )
    base_url = models.URLField(_("URL Odoo"), max_length=512)
    database = models.CharField(
        _("Base de datos Odoo"),
        max_length=128,
        blank=True,
        help_text=_("Header X-Odoo-Database cuando el host sirve varias bases."),
    )
    api_key_encrypted = models.TextField(_("API key (cifrada)"), blank=True)
    api_key_label = models.CharField(_("Etiqueta API key"), max_length=200, blank=True)
    api_key_expires_at = models.DateField(_("Vencimiento API key"), null=True, blank=True)
    api_mode = models.CharField(
        _("Modo API"),
        max_length=16,
        choices=ApiMode.choices,
        default=ApiMode.JSON2,
    )
    timeout_seconds = models.PositiveIntegerField(_("Timeout (segundos)"), default=60)
    activo = models.BooleanField(_("Activo"), default=True)
    last_test_ok_at = models.DateTimeField(_("Última prueba OK"), null=True, blank=True)
    last_test_message = models.CharField(_("Último mensaje de prueba"), max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Conexión Odoo")
        verbose_name_plural = _("Conexiones Odoo")
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.base_empresa})"

    def set_api_key(self, plain: str) -> None:
        self.api_key_encrypted = encrypt_secret((plain or "").strip())

    def get_api_key(self) -> str:
        return decrypt_secret(self.api_key_encrypted or "")

    @property
    def api_key_masked(self) -> str:
        return mask_secret(self.get_api_key())

    def dias_hasta_vencimiento_api_key(self) -> int | None:
        if not self.api_key_expires_at:
            return None
        return (self.api_key_expires_at - timezone.localdate()).days

    def api_key_proxima_a_vencer(self, umbral_dias: int = 7) -> bool:
        dias = self.dias_hasta_vencimiento_api_key()
        return dias is not None and dias <= umbral_dias


class MigrationJob(models.Model):
    """Job de migración/sincronización por dominio."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", _("Pendiente")
        EN_CURSO = "en_curso", _("En curso")
        OK = "ok", _("Completado")
        ERROR = "error", _("Error")
        CANCELADO = "cancelado", _("Cancelado")

    conexion = models.ForeignKey(
        OdooConnection,
        on_delete=models.CASCADE,
        related_name="jobs",
        verbose_name=_("Conexión"),
    )
    dominio = models.CharField(_("Dominio"), max_length=64, db_index=True)
    estado = models.CharField(
        _("Estado"),
        max_length=16,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    offset = models.PositiveIntegerField(_("Offset"), default=0)
    total_procesados = models.PositiveIntegerField(_("Procesados"), default=0)
    total_errores = models.PositiveIntegerField(_("Errores"), default=0)
    mensaje = models.TextField(_("Mensaje"), blank=True)
    iniciado_at = models.DateTimeField(_("Iniciado"), null=True, blank=True)
    finalizado_at = models.DateTimeField(_("Finalizado"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Job de migración")
        verbose_name_plural = _("Jobs de migración")
        ordering = ["-created_at"]


class MigrationEntityMapping(models.Model):
    """Correlación AdministraNET ↔ Odoo (idempotencia)."""

    class SyncState(models.TextChoices):
        PENDIENTE = "pendiente", _("Pendiente")
        OK = "ok", _("OK")
        ERROR = "error", _("Error")

    conexion = models.ForeignKey(
        OdooConnection,
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    entity_type = models.CharField(_("Tipo entidad"), max_length=64, db_index=True)
    adminet_id = models.CharField(_("ID AdministraNET"), max_length=64, db_index=True)
    external_id = models.CharField(_("External ID Odoo"), max_length=128, db_index=True)
    odoo_model = models.CharField(_("Modelo Odoo"), max_length=64)
    odoo_id = models.BigIntegerField(_("ID Odoo"), null=True, blank=True)
    last_hash = models.CharField(_("Hash último payload"), max_length=64, blank=True)
    sync_state = models.CharField(
        _("Estado sync"),
        max_length=16,
        choices=SyncState.choices,
        default=SyncState.PENDIENTE,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Mapeo de entidad")
        verbose_name_plural = _("Mapeos de entidades")
        constraints = [
            models.UniqueConstraint(
                fields=["conexion", "entity_type", "adminet_id"],
                name="odoo_mig_unique_adminet_entity",
            ),
            models.UniqueConstraint(
                fields=["conexion", "external_id"],
                name="odoo_mig_unique_external_id",
            ),
        ]
