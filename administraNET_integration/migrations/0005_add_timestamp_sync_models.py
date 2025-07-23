# Generated manually for timestamp-based sync implementation

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('administraNET_integration', '0004_alter_validationruleconfig_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncTimestampLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('record_type', models.CharField(max_length=50, verbose_name='Record Type')),
                ('record_id', models.CharField(max_length=100, verbose_name='Record ID')),
                ('synap_timestamp', models.DateTimeField(verbose_name='Synap Timestamp')),
                ('adminet_timestamp', models.DateTimeField(verbose_name='administraNET Timestamp')),
                ('winner', models.CharField(choices=[('SYNAP_WINS', 'Synap Wins'), ('ADMINET_WINS', 'administraNET Wins'), ('NO_CHANGE', 'No Change')], max_length=20, verbose_name='Winner')),
                ('fields_updated', models.JSONField(default=list, verbose_name='Fields Updated')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('sync_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timestamp_conflicts', to='administraNET_integration.synclog')),
            ],
            options={
                'verbose_name': 'Sync Timestamp Log',
                'verbose_name_plural': 'Sync Timestamp Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SyncTimestampConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sync_type', models.CharField(choices=[('PRODUCTS', 'Products'), ('CUSTOMERS', 'Customers'), ('STOCK', 'Stock'), ('ORDERS', 'Orders')], max_length=50, verbose_name='Sync Type')),
                ('enable_timestamp_resolution', models.BooleanField(default=True, verbose_name='Enable Timestamp Resolution')),
                ('sync_all_fields', models.BooleanField(default=True, help_text='Always synchronize all editable fields', verbose_name='Sync All Fields')),
                ('log_conflicts', models.BooleanField(default=True, verbose_name='Log Conflicts')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
            ],
            options={
                'verbose_name': 'Sync Timestamp Config',
                'verbose_name_plural': 'Sync Timestamp Configs',
                'ordering': ['sync_type'],
            },
        ),
        migrations.AddIndex(
            model_name='synctimestamplog',
            index=models.Index(fields=['sync_log', 'record_type'], name='administraNE_sync_lo_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='synctimestamplog',
            index=models.Index(fields=['winner'], name='administraNE_winner_123456_idx'),
        ),
        migrations.AddIndex(
            model_name='synctimestamplog',
            index=models.Index(fields=['created_at'], name='administraNE_created_123456_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='synctimestampconfig',
            unique_together={('sync_type',)},
        ),
    ] 