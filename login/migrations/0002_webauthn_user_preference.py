# Generated manually for WebAuthn user preference (Postgres)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("login", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebAuthnUserPreference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("base_empresa", models.CharField(db_index=True, max_length=128)),
                ("id_usuario", models.PositiveIntegerField()),
                ("enabled", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Preferencia WebAuthn usuario",
                "verbose_name_plural": "Preferencias WebAuthn usuario",
                "db_table": "login_webauthn_user_preference",
            },
        ),
        migrations.AddConstraint(
            model_name="webauthnuserpreference",
            constraint=models.UniqueConstraint(
                fields=("base_empresa", "id_usuario"),
                name="login_webauthn_user_pref_unique",
            ),
        ),
    ]
