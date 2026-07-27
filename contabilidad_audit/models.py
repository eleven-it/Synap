"""Modelos Postgres Synap para políticas y corridas de auditoría contable."""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PREFIJOS_CUENTA_DEFAULT = {
    "resultado": ["4"],
    "activo": ["1"],
    "pasivo": ["2"],
    "pn": ["3"],
}

TRATAMIENTO_ANULADOS_CHOICES = (
    ("excluir", "Excluir anulados"),
    ("incluir_neutralizado", "Incluir neutralizados"),
)

POLITICA_CENTAVO_CHOICES = (
    ("diario_manda", "Diario manda"),
    ("conservar_compensacion", "Conservar compensación VB6"),
)

EJERCICIOS_CERRADOS_CHOICES = (
    ("no_tocar", "No tocar ejercicios cerrados"),
    ("permitir_con_reapertura", "Permitir con reapertura"),
)

ALCANCE_RECOMPUTE_CHOICES = (
    ("ejercicio_activo", "Ejercicio activo"),
    ("ejercicio_seleccionado", "Ejercicio seleccionado"),
    ("historico", "Histórico"),
)

CATEGORIAS_PREFIJOS = ("resultado", "activo", "pasivo", "pn")


class PoliticaAuditoriaContable(models.Model):
    """Política de negocio para checks y recálculo (Postgres Synap)."""

    BASE_DEFAULT = "__default__"

    base_empresa = models.CharField(max_length=64, unique=True)
    tratamiento_anulados = models.CharField(
        max_length=32,
        choices=TRATAMIENTO_ANULADOS_CHOICES,
        default="incluir_neutralizado",
    )
    politica_centavo = models.CharField(
        max_length=32,
        choices=POLITICA_CENTAVO_CHOICES,
        default="diario_manda",
    )
    prefijos_cuenta = models.JSONField(default=dict)
    ejercicios_cerrados = models.CharField(
        max_length=32,
        choices=EJERCICIOS_CERRADOS_CHOICES,
        default="no_tocar",
    )
    alcance_recompute = models.CharField(
        max_length=32,
        choices=ALCANCE_RECOMPUTE_CHOICES,
        default="ejercicio_seleccionado",
    )
    tolerancia_decimal = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.005"),
    )
    actualizado_por = models.CharField(max_length=64, default="sistema")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Política de auditoría contable"
        verbose_name_plural = "Políticas de auditoría contable"

    def __str__(self) -> str:
        return f"Política {self.base_empresa}"

    def clean(self) -> None:
        super().clean()
        errores: dict[str, str] = {}

        if self.tratamiento_anulados not in dict(TRATAMIENTO_ANULADOS_CHOICES):
            errores["tratamiento_anulados"] = "Valor no permitido para tratamiento de anulados."
        if self.politica_centavo not in dict(POLITICA_CENTAVO_CHOICES):
            errores["politica_centavo"] = "Valor no permitido para política de centavo."
        if self.ejercicios_cerrados not in dict(EJERCICIOS_CERRADOS_CHOICES):
            errores["ejercicios_cerrados"] = "Valor no permitido para ejercicios cerrados."
        if self.alcance_recompute not in dict(ALCANCE_RECOMPUTE_CHOICES):
            errores["alcance_recompute"] = "Valor no permitido para alcance de recálculo."

        prefijos = self.prefijos_cuenta or {}
        if not isinstance(prefijos, dict):
            errores["prefijos_cuenta"] = "Debe ser un objeto JSON con categorías de prefijos."
        else:
            for cat in CATEGORIAS_PREFIJOS:
                if cat not in prefijos:
                    errores["prefijos_cuenta"] = (
                        f"Falta la categoría '{cat}' en prefijos_cuenta."
                    )
                    break
                valor = prefijos.get(cat)
                if not isinstance(valor, list):
                    errores["prefijos_cuenta"] = f"La categoría '{cat}' debe ser una lista."
                    break
            if "prefijos_cuenta" not in errores and not prefijos.get("resultado"):
                errores["prefijos_cuenta"] = "La categoría 'resultado' no puede estar vacía."

        if self.tolerancia_decimal is not None and self.tolerancia_decimal < 0:
            errores["tolerancia_decimal"] = "La tolerancia debe ser un valor positivo."

        if errores:
            raise ValidationError(errores)


class CorridaAuditoria(models.Model):
    """Metadatos de una corrida read-only (Fase 1)."""

    corrida_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    base_empresa = models.CharField(max_length=64)
    filtros = models.JSONField(default=dict)
    config_hash = models.CharField(max_length=80)
    resumen = models.JSONField(default=dict)
    ejecutada_por = models.CharField(max_length=64, default="")
    fecha_corrida = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Corrida de auditoría contable"
        verbose_name_plural = "Corridas de auditoría contable"
        ordering = ("-fecha_corrida",)

    def __str__(self) -> str:
        return f"Corrida {self.corrida_id} ({self.base_empresa})"


class PlanCorreccion(models.Model):
    """Stub Fase 2: plan dry-run → apply."""

    dry_run_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    base_empresa = models.CharField(max_length=64)
    alcance = models.JSONField(default=dict)
    config_hash = models.CharField(max_length=80)
    data_fingerprint = models.CharField(max_length=80, default="")
    plan = models.JSONField(default=dict)
    estado = models.CharField(max_length=24, default="propuesto")
    creado_por = models.CharField(max_length=64, default="")
    creado_en = models.DateTimeField(default=timezone.now)
    expira_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Plan de corrección contable"
        verbose_name_plural = "Planes de corrección contable"


class HistorialPoliticaAuditoria(models.Model):
    """Registro append-only de cambios en políticas (POL-10)."""

    base_empresa = models.CharField(max_length=64, db_index=True)
    snapshot_anterior = models.JSONField(null=True, blank=True)
    snapshot_nuevo = models.JSONField()
    config_hash_anterior = models.CharField(max_length=80, null=True, blank=True)
    config_hash_nuevo = models.CharField(max_length=80)
    cambiado_por = models.CharField(max_length=64)
    cambiado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de política de auditoría"
        verbose_name_plural = "Historial de políticas de auditoría"
        ordering = ("-cambiado_en",)

    def __str__(self) -> str:
        return f"Historial {self.base_empresa} ({self.cambiado_en:%d/%m/%Y %H:%M})"


class AprobacionREI(models.Model):
    """Stub Fase 3: aprobación caso a caso de REI."""

    dry_run_id = models.UUIDField()
    id_pc = models.IntegerField()
    id_ejercicio = models.IntegerField()
    rei_teorico = models.DecimalField(max_digits=18, decimal_places=4)
    rei_actual = models.DecimalField(max_digits=18, decimal_places=4)
    estado = models.CharField(max_length=16, default="pendiente")
    aprobado_por = models.CharField(max_length=64, blank=True, default="")
    aprobado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Aprobación REI"
        verbose_name_plural = "Aprobaciones REI"
