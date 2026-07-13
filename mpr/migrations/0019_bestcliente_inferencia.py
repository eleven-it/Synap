from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mpr", "0018_best_migration_parity"),
    ]

    operations = [
        migrations.AddField(
            model_name="bestclientemap",
            name="score",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="razon",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="alt1_codigo",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="alt1_nombre",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="bestclientemap",
            name="alt1_score",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="bestclientemap",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("INFERIDO", "Inferido"),
                    ("AMBIGUO", "Ambiguo"),
                    ("SIN_CANDIDATO", "Sin candidato"),
                    ("VALIDADO", "Validado"),
                    ("DESCARTADO", "Descartado"),
                ],
                db_index=True,
                default="PENDIENTE",
                max_length=24,
            ),
        ),
    ]
