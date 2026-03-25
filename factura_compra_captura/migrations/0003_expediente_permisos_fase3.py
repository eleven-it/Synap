from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("factura_compra_captura", "0002_documento_fuente"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="expedientefacturacompra",
            options={
                "ordering": ["-creado_en"],
                "permissions": [
                    ("crear", "Puede crear expedientes de factura de compra"),
                    ("ver", "Puede ver expedientes de factura de compra"),
                    ("editar", "Puede editar expedientes de factura de compra"),
                    (
                        "revisar",
                        "Puede enviar a revisión y marcar listo para aprobar",
                    ),
                    ("aprobar", "Puede aprobar expedientes (posting stub o real)"),
                    ("rechazar", "Puede rechazar expedientes"),
                    ("reintentar_posting", "Puede reintentar posting tras error"),
                ],
                "verbose_name": "Expediente factura de compra",
                "verbose_name_plural": "Expedientes factura de compra",
            },
        ),
    ]
