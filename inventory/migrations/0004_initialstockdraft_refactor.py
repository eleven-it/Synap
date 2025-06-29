from django.db import migrations, models
import django.db.models.deletion
import django.contrib.auth

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0003_initialstockdraft_alter_product_uom_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='initialstockdraft',
            name='motivo',
        ),
        migrations.AddField(
            model_name='initialstockdraft',
            name='almacen',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='inventory.warehouse', verbose_name='Warehouse'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='initialstockdraft',
            name='adjuntos',
        ),
        migrations.CreateModel(
            name='InitialStockDraftDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('archivo', models.FileField(upload_to='stock_initial_attachments/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('borrador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documentos_respaldo', to='inventory.initialstockdraft')),
            ],
        ),
    ] 