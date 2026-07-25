"""Descifra bootstrap/env.enc con la frase de cifrado (offline / restore)."""

from __future__ import annotations

from pathlib import Path

from cryptography.fernet import InvalidToken
from django.core.management.base import BaseCommand, CommandError

from core.backup.services.bootstrap import decrypt_env_bytes


class Command(BaseCommand):
    help = (
        "Descifra un archivo bootstrap/env.enc usando la frase de cifrado "
        "(la misma configurada en Copias de seguridad → Configuración). "
        "Útil en restore: no requiere Synap levantado con Postgres."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            required=True,
            help="Ruta a env.enc (p. ej. .../bootstrap/env.enc)",
        )
        parser.add_argument(
            "--output",
            default="",
            help="Ruta de salida (default: .env en el directorio actual)",
        )
        parser.add_argument(
            "--passphrase",
            default="",
            help="Frase de cifrado. Si se omite, se pide por stdin (recomendado).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sobrescribir el archivo de salida si ya existe",
        )

    def handle(self, *args, **options):
        enc_path = Path(options["input"]).expanduser().resolve()
        if not enc_path.is_file():
            raise CommandError(f"No existe el archivo: {enc_path}")

        out_path = Path(options["output"] or ".env").expanduser().resolve()
        if out_path.exists() and not options["force"]:
            raise CommandError(
                f"Ya existe {out_path}. Use --force para sobrescribir o indique otro --output."
            )

        phrase = (options.get("passphrase") or "").strip()
        if not phrase:
            phrase = input("Frase de cifrado bootstrap: ").strip()
        if not phrase:
            raise CommandError("La frase de cifrado es obligatoria.")

        ciphertext = enc_path.read_bytes()
        try:
            plaintext = decrypt_env_bytes(ciphertext, phrase)
        except InvalidToken as exc:
            raise CommandError(
                "Frase incorrecta o archivo corrupto (InvalidToken)."
            ) from exc
        except Exception as exc:
            raise CommandError(f"No se pudo descifrar: {exc}") from exc

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(plaintext)
        try:
            out_path.chmod(0o600)
        except OSError:
            pass

        self.stdout.write(self.style.SUCCESS(f"Escrito: {out_path} ({len(plaintext)} bytes)"))
        self.stdout.write(
            "Revise el .env (hosts/puertos) antes de levantar Docker. "
            "Ver docs/general/RESTORE_RUNBOOK_SYNAP.md"
        )
