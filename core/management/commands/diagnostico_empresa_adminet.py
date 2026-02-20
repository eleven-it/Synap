"""
Diagnóstico: comprueba si en la base MySQL de AdministraNET existe la tabla
DatosEmpresa y si tiene datos. Útil cuando "No hay empresas" sigue apareciendo.

Uso (dentro del contenedor):
  python manage.py diagnostico_empresa_adminet
  python manage.py diagnostico_empresa_adminet --base administranet89
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection
from core.services.administranet_empresas import _nombre_tabla_empresa


class Command(BaseCommand):
    help = "Comprueba tabla DatosEmpresa en la base MySQL AdministraNET (lista tablas, cuenta filas)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base",
            type=str,
            default=None,
            help="Nombre de la base de datos (ej. administranet89). Por defecto usa NAME de DATABASES['mysql'].",
        )

    def handle(self, *args, **options):
        base = (options.get("base") or "").strip()
        if not base:
            base = settings.DATABASES.get("mysql", {}).get("NAME", "administranet")
        self.stdout.write(f"Base: {base}")

        try:
            with get_connection(base) as conn:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                tablas = [row[0] for row in cursor.fetchall() if row and row[0]]
                self.stdout.write(f"Tablas en la base: {len(tablas)}")
                tabla_empresa = _nombre_tabla_empresa(cursor)
                if not tabla_empresa:
                    self.stdout.write(
                        self.style.ERROR(
                            "No existe ninguna tabla cuyo nombre (ignorando mayúsculas) sea 'datosempresa'."
                        )
                    )
                    if tablas:
                        self.stdout.write("Algunas tablas: " + ", ".join(tablas[:15]))
                    return
                self.stdout.write(self.style.SUCCESS(f"Tabla de empresa encontrada: {tabla_empresa}"))
                cursor.execute(f"SELECT COUNT(*) FROM `{tabla_empresa}`")
                total = cursor.fetchone()[0]
                self.stdout.write(f"Filas en {tabla_empresa}: {total}")
                if total > 0:
                    cursor.execute(f"SELECT * FROM `{tabla_empresa}` LIMIT 3")
                    cols = [d[0] for d in cursor.description]
                    for row in cursor.fetchall():
                        d = dict(zip(cols, row))
                        id_e = d.get("id_empresa") or d.get("ID_EMPRESA")
                        nom = d.get("Nombre") or d.get("nombre") or "(sin nombre)"
                        self.stdout.write(f"  id_empresa={id_e}, Nombre={nom!r}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
