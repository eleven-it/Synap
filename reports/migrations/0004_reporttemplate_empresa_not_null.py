from django.db import migrations, models
import core.models.models

class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0003_set_empresa_reporttemplate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reporttemplate',
            name='empresa',
            field=models.ForeignKey(to='core.empresa', on_delete=models.CASCADE, verbose_name='Company'),
        ),
    ] 