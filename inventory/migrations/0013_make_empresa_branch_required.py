from django.db import migrations, models

def set_not_null(apps, schema_editor):
    # No se requiere lógica Python, solo el alter field
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0012_fill_empresa_branch_not_null'),
    ]
    operations = [
        migrations.AlterField(
            model_name='warehouse',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='warehouses', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='warehouse',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='warehouses', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='location',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='locations', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='location',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='locations', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='product',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='products', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='product',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='products', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='stocklot',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='stocklots', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='stocklot',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='stocklots', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='stockquant',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='stockquants', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='stockquant',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='stockquants', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='stockmove',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='stockmoves', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='stockmove',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='stockmoves', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='inventoryadjustment',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='inventoryadjustments', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='inventoryadjustment',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='inventoryadjustments', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='stockreservation',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='stockreservations', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='stockreservation',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='stockreservations', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='replenishmentrule',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='replenishmentrules', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='replenishmentrule',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='replenishmentrules', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='initialstockdraft',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='initialstockdrafts', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='initialstockdraft',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='initialstockdrafts', verbose_name='Branch'),
        ),
        migrations.AlterField(
            model_name='initialstockdraftitem',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, related_name='initialstockdraftitems', verbose_name='Company'),
        ),
        migrations.AlterField(
            model_name='initialstockdraftitem',
            name='branch',
            field=models.ForeignKey(to='core.branch', on_delete=models.CASCADE, related_name='initialstockdraftitems', verbose_name='Branch'),
        ),
    ] 