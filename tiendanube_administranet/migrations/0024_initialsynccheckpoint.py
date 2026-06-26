# Sync inicial por lotes — checkpoint resumible

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0023_customermapping_hardening'),
    ]

    operations = [
        migrations.CreateModel(
            name='InitialSyncCheckpoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_type', models.CharField(
                    choices=[('customer', 'Customer'), ('product', 'Product')],
                    max_length=20,
                    verbose_name='Sync Type',
                )),
                ('last_offset', models.IntegerField(default=0, verbose_name='Last Offset')),
                ('total_items', models.IntegerField(default=0, verbose_name='Total Items')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('in_progress', 'In Progress'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Status',
                )),
                ('last_run_at', models.DateTimeField(blank=True, null=True, verbose_name='Last Run At')),
                ('error_message', models.TextField(blank=True, verbose_name='Error Message')),
                ('adminet_config', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='tiendanube_administranet.administranetconfig',
                    verbose_name='AdministraNET Config',
                )),
                ('tiendanube_config', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='tiendanube_administranet.tiendanubeconfig',
                    verbose_name='Tiendanube Config',
                )),
            ],
            options={
                'verbose_name': 'Initial Sync Checkpoint',
                'verbose_name_plural': 'Initial Sync Checkpoints',
                'ordering': ['-last_run_at', '-id'],
                'unique_together': {('sync_type', 'adminet_config', 'tiendanube_config')},
            },
        ),
    ]
