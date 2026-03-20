# Visibilidad granular navbar (supervisor): JSON modulos_ocultos + items_menu_ocultos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_navbar_menu_global"),
    ]

    operations = [
        migrations.AddField(
            model_name="navbarmenuglobal",
            name="modulos_ocultos",
            field=models.JSONField(
                default=list,
                help_text="Lista de app_id (APPS_MENU) cuyo módulo no se muestra en la navbar.",
                verbose_name="Módulos ocultos en navbar",
            ),
        ),
        migrations.AddField(
            model_name="navbarmenuglobal",
            name="items_menu_ocultos",
            field=models.JSONField(
                default=dict,
                help_text="Diccionario app_id -> lista de menu_item_id ocultos.",
                verbose_name="Ítems de menú ocultos por módulo",
            ),
        ),
    ]
