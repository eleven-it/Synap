# Generated manually for tiendanube-administranet-reflote phase 5

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube_administranet', '0026_tiendanubeconfig_location_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='TiendanubeOutboxEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('stock_push', 'Stock Push'), ('catch_up_orders', 'Catch Up Orders')], max_length=50, verbose_name='Event Type')),
                ('payload', models.JSONField(default=dict, verbose_name='Payload')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('retry', 'Retry')], default='pending', max_length=20, verbose_name='Status')),
                ('retry_count', models.IntegerField(default=0, verbose_name='Retry Count')),
                ('max_retries', models.IntegerField(default=3, verbose_name='Max Retries')),
                ('retry_delay_seconds', models.IntegerField(default=300, verbose_name='Retry Delay (seconds)')),
                ('error_message', models.TextField(blank=True, verbose_name='Error Message')),
                ('processing_result', models.JSONField(blank=True, default=dict, verbose_name='Processing Result')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Processed At')),
                ('next_retry_at', models.DateTimeField(blank=True, null=True, verbose_name='Next Retry At')),
                ('adminet_config', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='outbox_events', to='tiendanube_administranet.administranetconfig', verbose_name='AdministraNET Configuration')),
                ('tiendanube_config', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outbox_events', to='tiendanube_administranet.tiendanubeconfig', verbose_name='Tiendanube Configuration')),
            ],
            options={
                'verbose_name': 'Tiendanube Outbox Event',
                'verbose_name_plural': 'Tiendanube Outbox Events',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='tiendanubeoutboxevent',
            index=models.Index(fields=['status', 'next_retry_at'], name='tiendanube__status_8a1f2d_idx'),
        ),
    ]
