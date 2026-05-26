"""
Copia certificados AFIP desde rutas antiguas (p. ej. bajo bind mount /app) al
almacén definido por SYNAP_AFIP_STORAGE / FE_AFIP_CERT_STORAGE_DIR y actualiza fe_afip.AFIPConfig.
"""
import os

from django.core.management.base import BaseCommand, CommandError

from fe_afip.models import AFIPConfig
from fe_afip.services.cert_arca import ingest_external_cert_pair, validate_cert_cuit


class Command(BaseCommand):
    help = (
        "Migra cert_path/key_path de AFIPConfig al volumen interno (SYNAP_AFIP_STORAGE). "
        "Útil tras habilitar el volumen synap_afip_secrets en Docker. "
        "Si la lectura desde BD falla (Errno 35), usá --certificado y --clave con rutas dentro del "
        "contenedor (p. ej. /tmp/... tras docker cp desde el host)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué registros se migrarían, sin escribir archivos ni BD.",
        )
        parser.add_argument(
            "--base-empresa",
            dest="base_empresa",
            default="",
            help="Con --certificado/--clave: base administraNET a actualizar. Obligatorio en ese modo.",
        )
        parser.add_argument(
            "--certificado",
            dest="certificado",
            default="",
            help="Ruta absoluta DENTRO del contenedor al .crt/.pem (copiá antes con docker cp a /tmp).",
        )
        parser.add_argument(
            "--clave",
            dest="clave",
            default="",
            help="Ruta absoluta DENTRO del contenedor a la clave privada (.key).",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        cert_imp = (options.get("certificado") or "").strip()
        key_imp = (options.get("clave") or "").strip()
        base_imp = (options.get("base_empresa") or "").strip()

        if cert_imp or key_imp:
            if dry:
                raise CommandError("No uses --dry-run junto con --certificado/--clave.")
            if not cert_imp or not key_imp:
                raise CommandError("Indicá ambos: --certificado y --clave.")
            if not base_imp:
                raise CommandError("Con importación manual hace falta --base-empresa.")
            if not os.path.isfile(cert_imp):
                raise CommandError(f"No existe el certificado en el contenedor: {cert_imp}")
            if not os.path.isfile(key_imp):
                raise CommandError(f"No existe la clave en el contenedor: {key_imp}")
            cfg = AFIPConfig.objects.filter(base_empresa=base_imp, activo=True).first()
            if not cfg:
                raise CommandError(f"No hay AFIPConfig activa para base_empresa={base_imp!r}.")
            cuit_cfg = (cfg.cuit or "").replace("-", "").replace(" ", "").strip()
            if len(cuit_cfg) == 11 and cuit_cfg.isdigit():
                ok, err = validate_cert_cuit(cert_imp, cuit_cfg)
                if not ok:
                    raise CommandError(err or "El certificado no coincide con el CUIT de la configuración AFIP.")
            try:
                new_c, new_k = ingest_external_cert_pair(base_imp, cert_imp, key_imp)
            except ValueError as e:
                raise CommandError(str(e)) from e
            cfg.cert_path = new_c
            cfg.key_path = new_k
            cfg.save(update_fields=["cert_path", "key_path"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"{base_imp}: certificados copiados al almacén seguro y rutas actualizadas en BD."
                )
            )
            self.stdout.write(
                "Podés borrar los archivos temporales en /tmp del contenedor si los copiaste solo para importar."
            )
            return

        qs = AFIPConfig.objects.filter(activo=True).exclude(cert_path="").exclude(key_path="")
        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No hay configuraciones AFIP con cert_path y key_path."))
            return
        if dry:
            for cfg in qs:
                self.stdout.write(
                    f"[dry-run] base_empresa={cfg.base_empresa} (se migraría al almacén SYNAP_AFIP_STORAGE si aplica)."
                )
            self.stdout.write(self.style.NOTICE(f"Total {total} (sin cambios en disco ni BD)."))
            return
        migrated = 0
        unchanged = 0
        errors = 0
        for cfg in qs:
            old_c = (cfg.cert_path or "").strip()
            old_k = (cfg.key_path or "").strip()
            if not old_c or not old_k:
                continue
            try:
                new_c, new_k = ingest_external_cert_pair(cfg.base_empresa, old_c, old_k)
            except ValueError as e:
                self.stderr.write(self.style.ERROR(f"{cfg.base_empresa}: {e}"))
                errors += 1
                continue
            if new_c != old_c or new_k != old_k:
                cfg.cert_path = new_c
                cfg.key_path = new_k
                cfg.save(update_fields=["cert_path", "key_path"])
                self.stdout.write(self.style.SUCCESS(f"{cfg.base_empresa}: rutas actualizadas en almacén seguro."))
                migrated += 1
            else:
                self.stdout.write(f"{cfg.base_empresa}: ya estaba en almacén canónico (sin cambios).")
                unchanged += 1
        self.stdout.write(
            self.style.NOTICE(
                f"Listo. Procesadas={total}, migradas={migrated}, sin cambios={unchanged}, errores={errors}."
            )
        )
