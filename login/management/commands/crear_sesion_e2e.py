# Sesión Django para pruebas E2E (solo desarrollo).
# Uso: docker exec Synap_app python manage.py crear_sesion_e2e --cod-usuario=Supervisor --base-empresa=administranet96 --json

import json

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand

from login.administranet_auth import AdministraNETAuth


def _cargar_usuario_sin_password(base_empresa: str, cod_usuario: str):
    """Lee usuario activo sin validar contraseña (solo entornos de desarrollo)."""
    auth = AdministraNETAuth()
    try:
        with auth.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'idioma'
                """,
                [base_empresa],
            )
            tiene_idioma = cursor.fetchone()[0] > 0
            cod_lower = (cod_usuario or "").strip().lower()
            if tiene_idioma:
                cursor.execute(
                    """
                    SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario,
                           id_empresa, id_sucursal, id_puesto, id_punto_venta, id_deposito, id_caja,
                           tipo_busqueda_defecto, baja_usuario, idioma
                    FROM usuarios
                    WHERE (baja_usuario IS NULL OR baja_usuario = 'No') AND LOWER(cod_usuario) = %s
                    LIMIT 1
                    """,
                    [cod_lower],
                )
            else:
                cursor.execute(
                    """
                    SELECT id_usuario, cod_usuario, nombre_usuario, apellido_usuario,
                           id_empresa, id_sucursal, id_puesto, id_punto_venta, id_deposito, id_caja,
                           tipo_busqueda_defecto, baja_usuario
                    FROM usuarios
                    WHERE (baja_usuario IS NULL OR baja_usuario = 'No') AND LOWER(cod_usuario) = %s
                    LIMIT 1
                    """,
                    [cod_lower],
                )
            row = cursor.fetchone()
            if not row:
                return None
            user_dict = {
                "id_usuario": row[0],
                "cod_usuario": row[1],
                "nombre_usuario": row[2] or "",
                "apellido_usuario": row[3] or "",
                "id_empresa": row[4],
                "id_sucursal": row[5],
                "id_puesto": row[6],
                "id_punto_venta": row[7],
                "id_deposito": row[8],
                "id_caja": row[9],
                "tipo_busqueda_defecto": row[10],
                "baja_usuario": row[11],
                "base_empresa": base_empresa,
                "idioma": (row[12] if tiene_idioma else None) or "es",
            }
            if user_dict["id_puesto"]:
                try:
                    cursor.execute(
                        "SELECT puesto FROM puestos WHERE idpuesto = %s AND anulado = 'No'",
                        [user_dict["id_puesto"]],
                    )
                    puesto_row = cursor.fetchone()
                    user_dict["nombre_puesto"] = puesto_row[0] if puesto_row else None
                except Exception:
                    user_dict["nombre_puesto"] = None
            else:
                user_dict["nombre_puesto"] = None
            cursor.close()
            return user_dict
    except Exception:
        return None


class Command(BaseCommand):
    help = "Crea sesión Django para E2E (solo DEBUG/development). Imprime session_key o JSON."

    def add_arguments(self, parser):
        parser.add_argument("--cod-usuario", type=str, default="Supervisor")
        parser.add_argument("--base-empresa", type=str, default="administranet96")
        parser.add_argument("--json", action="store_true", help="Salida JSON para Playwright.")

    def handle(self, *args, **options):
        env = (getattr(settings, "ENVIRONMENT", "") or "").lower()
        if not settings.DEBUG and env not in ("development", "dev", ""):
            self.stderr.write(self.style.ERROR("Solo disponible con DEBUG o ENVIRONMENT=development."))
            return

        base = (options["base_empresa"] or "").strip()
        cod = (options["cod_usuario"] or "").strip()
        user_data = _cargar_usuario_sin_password(base, cod)
        if not user_data:
            self.stderr.write(self.style.ERROR(f"Usuario '{cod}' no encontrado en {base}."))
            return

        store = SessionStore()
        nombre_empresa = ""
        try:
            from login.administranet_auth import AdministraNETAuth
            nombre_empresa = AdministraNETAuth().nombre_empresa_por_base(base) or base
        except Exception:
            nombre_empresa = base
        store["user"] = {
            "id_usuario": user_data["id_usuario"],
            "cod_usuario": user_data["cod_usuario"],
            "nombre_usuario": user_data["nombre_usuario"],
            "apellido_usuario": user_data["apellido_usuario"],
            "nombre_completo": f"{user_data['nombre_usuario']} {user_data['apellido_usuario']}".strip(),
            "id_empresa": user_data["id_empresa"],
            "id_sucursal": user_data["id_sucursal"],
            "id_puesto": user_data["id_puesto"],
            "nombre_puesto": user_data.get("nombre_puesto"),
            "base_empresa": base,
            "nombre_empresa": nombre_empresa,
            "id_sesion": None,
        }
        store.save()

        cookie_name = settings.SESSION_COOKIE_NAME
        payload = {
            "session_key": store.session_key,
            "cookie_name": cookie_name,
            "base_empresa": base,
            "cod_usuario": user_data["cod_usuario"],
        }
        if options.get("json"):
            self.stdout.write(json.dumps(payload))
        else:
            self.stdout.write(f"{cookie_name}={store.session_key}")
