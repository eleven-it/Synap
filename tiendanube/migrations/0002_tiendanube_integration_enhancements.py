# Generated manually for Tiendanube integration enhancements

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('tiendanube', '0001_initial'),
        ('inventory', '0001_initial'),
        ('sales', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        # Add new fields to TiendaNubeConfig
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='sync_orders',
            field=models.BooleanField(default=True, verbose_name='Sync Orders'),
        ),
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='sync_customers',
            field=models.BooleanField(default=True, verbose_name='Sync Customers'),
        ),
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='tiendanube_warehouse',
            field=models.ForeignKey(
                blank=True,
                help_text='Warehouse dedicated to Tiendanube stock management',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='inventory.warehouse',
                verbose_name='Tiendanube Warehouse'
            ),
        ),
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='auto_restock',
            field=models.BooleanField(default=True, verbose_name='Auto Restock'),
        ),
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='restock_threshold',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('5.00'),
                help_text='Minimum stock level to trigger auto restock',
                max_digits=10,
                verbose_name='Restock Threshold'
            ),
        ),
        migrations.AddField(
            model_name='tiendanubeconfig',
            name='restock_quantity',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('20.00'),
                help_text='Quantity to restock when threshold is reached',
                max_digits=10,
                verbose_name='Restock Quantity'
            ),
        ),

        # Add new sync types to TiendaNubeSyncLog
        migrations.AlterField(
            model_name='tiendanubesynclog',
            name='sync_type',
            field=models.CharField(
                choices=[
                    ('product', 'Product'),
                    ('stock', 'Stock'),
                    ('variant', 'Variant'),
                    ('order', 'Order'),
                    ('customer', 'Customer'),
                    ('webhook', 'Webhook'),
                    ('restock', 'Restock'),
                    ('full', 'Full Sync')
                ],
                max_length=20,
                verbose_name='Sync Type'
            ),
        ),

        # Add new fields to TiendaNubeProductMapping
        migrations.AddField(
            model_name='tiendanubeproductmapping',
            name='restock_enabled',
            field=models.BooleanField(default=True, verbose_name='Auto Restock Enabled'),
        ),
        migrations.AddField(
            model_name='tiendanubeproductmapping',
            name='restock_threshold',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Override global threshold for this product',
                max_digits=10,
                null=True,
                verbose_name='Restock Threshold'
            ),
        ),
        migrations.AddField(
            model_name='tiendanubeproductmapping',
            name='restock_quantity',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Override global quantity for this product',
                max_digits=10,
                null=True,
                verbose_name='Restock Quantity'
            ),
        ),

        # Create TiendaNubeCustomerMapping
        migrations.CreateModel(
            name='TiendaNubeCustomerMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tiendanube_id', models.BigIntegerField(unique=True)),
                ('tiendanube_email', models.EmailField(blank=True, max_length=254)),
                ('tiendanube_document', models.CharField(blank=True, max_length=50)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('sync_status', models.CharField(
                    choices=[
                        ('synced', 'Synced'),
                        ('pending', 'Pending'),
                        ('error', 'Error'),
                        ('conflict', 'Conflict')
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Sync Status'
                )),
                ('sync_enabled', models.BooleanField(default=True, verbose_name='Sync Enabled')),
                ('error_message', models.TextField(blank=True)),
                ('client', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sales.client')),
            ],
            options={
                'verbose_name': 'TiendaNube Customer Mapping',
                'verbose_name_plural': 'TiendaNube Customer Mappings',
            },
        ),

        # Create TiendaNubeOrderMapping
        migrations.CreateModel(
            name='TiendaNubeOrderMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tiendanube_order_id', models.BigIntegerField(unique=True)),
                ('tiendanube_order_number', models.CharField(blank=True, max_length=50)),
                ('order_source', models.CharField(default='Tiendanube', max_length=50)),
                ('payment_method', models.CharField(blank=True, max_length=100)),
                ('payment_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('last_synced', models.DateTimeField(auto_now=True)),
                ('sync_status', models.CharField(
                    choices=[
                        ('synced', 'Synced'),
                        ('pending', 'Pending'),
                        ('error', 'Error'),
                        ('conflict', 'Conflict')
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Sync Status'
                )),
                ('error_message', models.TextField(blank=True)),
                ('sales_order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='sales.salesorder')),
            ],
            options={
                'verbose_name': 'TiendaNube Order Mapping',
                'verbose_name_plural': 'TiendaNube Order Mappings',
            },
        ),

        # Create TiendaNubeRestockRule
        migrations.CreateModel(
            name='TiendaNubeRestockRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Rule Name')),
                ('rule_type', models.CharField(
                    choices=[
                        ('product', 'Product'),
                        ('category', 'Category'),
                        ('global', 'Global')
                    ],
                    max_length=20,
                    verbose_name='Rule Type'
                )),
                ('action_type', models.CharField(
                    choices=[
                        ('transfer', 'Internal Transfer'),
                        ('purchase', 'Purchase Order'),
                        ('notification', 'Notification Only')
                    ],
                    max_length=20,
                    verbose_name='Action Type'
                )),
                ('threshold', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Threshold')),
                ('restock_quantity', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Restock Quantity')),
                ('notify_email', models.EmailField(blank=True, max_length=254)),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.category')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.product')),
                ('source_warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='restock_source_rules', to='inventory.warehouse')),
                ('destination_warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='restock_destination_rules', to='inventory.warehouse')),
                ('notify_users', models.ManyToManyField(blank=True, to='core.usuarioextendido')),
            ],
            options={
                'verbose_name': 'TiendaNube Restock Rule',
                'verbose_name_plural': 'TiendaNube Restock Rules',
            },
        ),

        # Create TiendaNubeRestockLog
        migrations.CreateModel(
            name='TiendaNubeRestockLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(
                    choices=[
                        ('transfer', 'Internal Transfer'),
                        ('purchase', 'Purchase Order'),
                        ('notification', 'Notification')
                    ],
                    max_length=20,
                    verbose_name='Action Type'
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed')
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Status'
                )),
                ('quantity_requested', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Quantity Requested')),
                ('quantity_processed', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Quantity Processed')),
                ('message', models.TextField(blank=True)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.product')),
                ('rule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tiendanube.tiendanuberestockrule')),
                ('stock_move', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventory.stockmove')),
                ('purchase_order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='purchases.purchaseorder')),
            ],
            options={
                'verbose_name': 'TiendaNube Restock Log',
                'verbose_name_plural': 'TiendaNube Restock Logs',
                'ordering': ['-created_at'],
            },
        ),
    ] 