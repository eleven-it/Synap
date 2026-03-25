import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0010_alter_navbarmenuglobal_items_menu_ocultos_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpedienteFacturaCompra",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "sucursal_codigo_legacy",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Código sucursal legacy (opcional)",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("borrador", "Borrador"),
                            ("ocr_completado", "OCR completado"),
                            ("en_revision", "En revisión"),
                            ("listo_para_aprobar", "Listo para aprobar"),
                            ("aprobacion_solicitada", "Aprobación solicitada"),
                            ("aprobado", "Aprobado"),
                            ("rechazado", "Rechazado"),
                            ("error_posting", "Error en posting"),
                        ],
                        db_index=True,
                        default="borrador",
                        max_length=32,
                    ),
                ),
                (
                    "origen_datos",
                    models.CharField(
                        choices=[
                            ("MANUAL", "Manual"),
                            ("REMITO", "Remito"),
                            ("OC", "Orden de compra"),
                            ("VALE", "Vale"),
                        ],
                        default="MANUAL",
                        max_length=16,
                    ),
                ),
                (
                    "codigo_proveedor_legacy",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Código proveedor AdministraNET",
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "posting_status",
                    models.CharField(
                        choices=[
                            ("not_attempted", "No intentado"),
                            ("in_progress", "En curso"),
                            ("posted", "Posteado"),
                            ("failed", "Fallido"),
                        ],
                        default="not_attempted",
                        max_length=24,
                    ),
                ),
                ("posting_attempt", models.PositiveIntegerField(default=0)),
                ("idempotency_key_last", models.CharField(blank=True, max_length=128)),
                (
                    "legacy_codigo_movimiento",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("legacy_nro_comprobante", models.CharField(blank=True, max_length=64)),
                ("rechazo_motivo", models.TextField(blank=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("modificado_en", models.DateTimeField(auto_now=True)),
                (
                    "creado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expedientes_factura_compra_creados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expedientes_factura_compra",
                        to="core.empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Expediente factura de compra",
                "verbose_name_plural": "Expedientes factura de compra",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.CreateModel(
            name="LineaExpedienteCompra",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("orden", models.PositiveIntegerField()),
                (
                    "id_art_legacy",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="ID artículo legacy",
                    ),
                ),
                ("codgasto_legacy", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "cantidad",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        max_digits=18,
                    ),
                ),
                (
                    "precio_unitario",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        max_digits=18,
                    ),
                ),
                (
                    "codigo_movimiento_oc",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "codigo_movimiento_remito",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "expediente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="factura_compra_captura.expedientefacturacompra",
                    ),
                ),
            ],
            options={
                "verbose_name": "Línea expediente compra",
                "verbose_name_plural": "Líneas expediente compra",
                "ordering": ["expediente", "orden"],
            },
        ),
        migrations.CreateModel(
            name="EventoAuditoriaInterno",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tipo_evento", models.CharField(db_index=True, max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="eventos_auditoria_expediente_compra",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "expediente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="eventos_auditoria",
                        to="factura_compra_captura.expedientefacturacompra",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento auditoría interno (expediente compra)",
                "verbose_name_plural": "Eventos auditoría interno (expediente compra)",
                "ordering": ["creado_en"],
            },
        ),
        migrations.AddConstraint(
            model_name="lineaexpedientecompra",
            constraint=models.UniqueConstraint(
                fields=("expediente", "orden"),
                name="uniq_linea_expediente_orden",
            ),
        ),
        migrations.AddIndex(
            model_name="expedientefacturacompra",
            index=models.Index(
                fields=["estado", "empresa"],
                name="factura_com_estado_3e6fbd_idx",
            ),
        ),
    ]
