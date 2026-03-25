import django.db.models.deletion
from django.db import migrations, models

import factura_compra_captura.models.documento_fuente


class Migration(migrations.Migration):

    dependencies = [
        ("factura_compra_captura", "0001_initial_expediente_factura_compra"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentoFuente",
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
                (
                    "archivo",
                    models.FileField(
                        max_length=512,
                        upload_to=factura_compra_captura.models.documento_fuente.documento_fuente_upload_to,
                    ),
                ),
                ("nombre_original", models.CharField(blank=True, max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=128)),
                ("tamano_bytes", models.PositiveBigIntegerField(default=0)),
                ("sha256_hex", models.CharField(blank=True, db_index=True, max_length=64)),
                (
                    "tipo_archivo",
                    models.CharField(
                        choices=[("imagen", "Imagen"), ("pdf", "PDF")],
                        default="imagen",
                        max_length=16,
                    ),
                ),
                (
                    "estado_procesamiento",
                    models.CharField(
                        choices=[
                            ("pendiente", "OCR pendiente"),
                            ("procesando", "OCR en curso"),
                            ("completado", "OCR completado"),
                            ("fallido", "OCR fallido"),
                        ],
                        db_index=True,
                        default="pendiente",
                        max_length=20,
                    ),
                ),
                ("ocr_intento", models.PositiveIntegerField(default=0)),
                ("ocr_error_codigo", models.CharField(blank=True, max_length=64)),
                ("ocr_error_detalle", models.TextField(blank=True)),
                ("resultado_ocr", models.JSONField(blank=True, default=dict)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("modificado_en", models.DateTimeField(auto_now=True)),
                (
                    "expediente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documentos_fuente",
                        to="factura_compra_captura.expedientefacturacompra",
                    ),
                ),
            ],
            options={
                "verbose_name": "Documento fuente (factura compra)",
                "verbose_name_plural": "Documentos fuente (factura compra)",
                "ordering": ["creado_en"],
            },
        ),
        migrations.AddIndex(
            model_name="documentofuente",
            index=models.Index(
                fields=["expediente", "estado_procesamiento"],
                name="factura_com_expedie_9a1b2c_idx",
            ),
        ),
    ]
