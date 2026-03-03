# Migración inicial Facturación Electrónica AFIP (config por base empresa).

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AFIPConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Default", max_length=64, verbose_name="Nombre")),
                ("base_empresa", models.CharField(db_index=True, help_text="Nombre de la base de datos administraNET. Una config por base.", max_length=64, unique=True, verbose_name="Base empresa (DB)")),
                ("cert_path", models.CharField(blank=True, help_text="Ruta absoluta al archivo .crt o .pem del certificado AFIP", max_length=512, verbose_name="Ruta certificado")),
                ("key_path", models.CharField(blank=True, help_text="Ruta absoluta al archivo .key o .pem de la clave privada", max_length=512, verbose_name="Ruta clave privada")),
                ("cuit", models.CharField(blank=True, help_text="CUIT de 11 dígitos (con o sin guiones)", max_length=14, verbose_name="CUIT contribuyente")),
                ("modo_homologacion", models.BooleanField(default=True, help_text="Activado: usa entornos de prueba AFIP (todas las pruebas). Desactivado: producción (solo cuando esté validado).", verbose_name="Modo homologación")),
                ("cache_dir", models.CharField(blank=True, default="/tmp/pyafipws_cache", help_text="Directorio para caché de tickets WSAA (opcional)", max_length=512, verbose_name="Directorio caché")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración AFIP (FE)",
                "verbose_name_plural": "Configuraciones AFIP (FE)",
            },
        ),
    ]
