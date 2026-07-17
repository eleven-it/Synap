from django.db import models


class WebAuthnCredential(models.Model):
    """Credencial WebAuthn (passkey) por usuario y empresa AdministraNET."""

    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveIntegerField(default=0)
    base_empresa = models.CharField(max_length=128, db_index=True)
    id_usuario = models.PositiveIntegerField()
    device_label = models.CharField(max_length=128, default="")
    password_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "login_webauthn_credential"
        indexes = [
            models.Index(fields=["base_empresa", "id_usuario"]),
        ]
        verbose_name = "Credencial WebAuthn"
        verbose_name_plural = "Credenciales WebAuthn"

    def __str__(self):
        return f"{self.base_empresa}:{self.id_usuario} ({self.device_label or 'sin etiqueta'})"

    @property
    def activa(self) -> bool:
        return self.revoked_at is None


class WebAuthnUserPreference(models.Model):
    """Preferencia de autenticación rápida WebAuthn por usuario y empresa."""

    base_empresa = models.CharField(max_length=128, db_index=True)
    id_usuario = models.PositiveIntegerField()
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "login_webauthn_user_preference"
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa", "id_usuario"],
                name="login_webauthn_user_pref_unique",
            ),
        ]
        verbose_name = "Preferencia WebAuthn usuario"
        verbose_name_plural = "Preferencias WebAuthn usuario"

    def __str__(self):
        estado = "activa" if self.enabled else "inactiva"
        return f"{self.base_empresa}:{self.id_usuario} ({estado})"
