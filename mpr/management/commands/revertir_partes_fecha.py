# MPR — Inventario / apply para reset total de partes de una o más fechas.
# Cutover: eliminar TODOS los mpr_parte de la(s) fecha(s) + anular OPP/stock.
# Uso dry-run:
#   docker exec Synap_app python manage.py revertir_partes_fecha \
#     --base-empresa=administranet1 --fecha=22/07/2026 \
#     --host=192.168.0.2 --port=30804
# Uso apply (pruebas):
#   docker exec Synap_app python manage.py revertir_partes_fecha \
#     --base-empresa=administranet1 \
#     --fecha=22/07/2026 --fecha=23/07/2026 --fecha=24/07/2026 --fecha=27/07/2026 \
#     --host=192.168.0.2 --port=30804 \
#     --apply --confirmar=RESET
# Apply sobre 'administranet' (prod) requiere además --forzar-produccion.

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none
from mpr.services import _nombre_tabla

MSG_CONFIRMAR_REQUERIDO = (
    "Para --apply indique --confirmar=RESET (cutover: eliminar TODOS los partes "
    "de la(s) fecha(s) + anular OPP y ajustar stock_deposito)."
)
MSG_PRODUCCION_BLOQUEADA = (
    "Apply bloqueado sobre base 'administranet' (producción). "
    "Use una base de prueba (ej. administranet1) o --forzar-produccion."
)
CONFIRMAR_RESET = "RESET"

# Fechas de cutover Best Sox (referencia; se pueden pasar otras con --fecha).
FECHAS_CUTOVER_REF = (
    "22/07/2026",
    "23/07/2026",
    "24/07/2026",
    "27/07/2026",
)


def parse_fecha_arg(valor: str) -> str:
    """
    Acepta YYYY-MM-DD o dd/MM/yyyy. Devuelve 'YYYY-MM-DD' para MySQL.
    """
    texto = (valor or "").strip()
    if not texto:
        raise CommandError("Indique --fecha (YYYY-MM-DD o dd/MM/yyyy).")
    iso = to_date_or_none(texto)
    if iso:
        try:
            datetime.strptime(iso, "%Y-%m-%d")
            return iso
        except ValueError:
            pass
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise CommandError(
        f"Fecha inválida: {valor!r}. Use YYYY-MM-DD o dd/MM/yyyy (ej. 22/07/2026)."
    )


def parse_fechas_args(valores: List[str]) -> List[str]:
    """Parsea una o más --fecha (también admite CSV en un mismo valor). Sin duplicados, orden de aparición."""
    if not valores:
        raise CommandError(
            "Indique al menos --fecha (ej. --fecha=22/07/2026). "
            f"Cutover ref.: {', '.join(FECHAS_CUTOVER_REF)}."
        )
    out: List[str] = []
    seen: set[str] = set()
    for raw in valores:
        for piece in str(raw or "").split(","):
            piece = piece.strip()
            if not piece:
                continue
            iso = parse_fecha_arg(piece)
            if iso not in seen:
                seen.add(iso)
                out.append(iso)
    if not out:
        raise CommandError("Indique al menos --fecha válida.")
    return out


def _row_val(row: Any, *keys: str):
    if not row:
        return None
    if isinstance(row, dict):
        lower = {str(k).lower(): v for k, v in row.items()}
        for key in keys:
            if key.lower() in lower:
                return lower[key.lower()]
    elif isinstance(row, (list, tuple)) and len(row) == 1 and not keys:
        return row[0]
    return None


def _fmt_decimal(val: Any) -> str:
    d = to_decimal_or_none(val)
    if d is None:
        return "0"
    if d == d.to_integral_value():
        return str(int(d))
    return str(d.normalize())


def _fmt_fecha_es(fecha_iso: str) -> str:
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return fecha_iso


class Command(BaseCommand):
    help = (
        "Reset total de partes MPR (dry-run o --apply --confirmar=RESET): "
        "inventario, anular OPP-parte, ajustar stock_deposito y borrar mpr_parte."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            default="administranet",
            help="Base MySQL de la empresa (default: administranet).",
        )
        parser.add_argument(
            "--fecha",
            action="append",
            dest="fechas",
            default=None,
            help=(
                "Fecha de producción (YYYY-MM-DD o dd/MM/yyyy). "
                "Repetible o CSV. Cutover ref.: "
                + ", ".join(FECHAS_CUTOVER_REF)
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Ejecutar reset (requiere --confirmar=RESET).",
        )
        parser.add_argument(
            "--confirmar",
            type=str,
            default="",
            help=f"Debe ser '{CONFIRMAR_RESET}' junto con --apply.",
        )
        parser.add_argument(
            "--forzar-produccion",
            action="store_true",
            help="Permite --apply sobre base administranet (producción). Por defecto bloqueado.",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="",
            help="Host MySQL opcional (p. ej. LAN planta). Si se indica, no usa el pool Synap.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=0,
            help="Puerto MySQL opcional (junto con --host).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "administranet").strip()
        if not base:
            raise CommandError("Indique --base-empresa.")

        aplicar = bool(options.get("apply"))
        if aplicar:
            confirmar = str(options.get("confirmar") or "").strip()
            if confirmar != CONFIRMAR_RESET:
                raise CommandError(MSG_CONFIRMAR_REQUERIDO)
            if base.lower() == "administranet" and not options.get("forzar_produccion"):
                raise CommandError(MSG_PRODUCCION_BLOQUEADA)

        fechas_iso = parse_fechas_args(options.get("fechas") or [])
        host = (options.get("host") or "").strip()
        port = int(options.get("port") or 0)
        fechas_es = ", ".join(_fmt_fecha_es(f) for f in fechas_iso)
        modo = "APPLY" if aplicar else "DRY-RUN"

        self.stdout.write(
            self.style.WARNING(
                f"[{modo}] Reset total de partes — base={base}, fechas={fechas_es}"
                + (f", host={host}:{port or 3306}" if host else "")
            )
        )
        if aplicar:
            self.stdout.write(
                self.style.ERROR(
                    "Se anularán OPP-parte, se ajustará stock_deposito y se "
                    "ELIMINARÁN todos los mpr_parte de la(s) fecha(s).\n"
                )
            )
        else:
            self.stdout.write(
                "Modo: solo lectura. Cutover previsto: ELIMINAR TODOS los mpr_parte "
                "de la(s) fecha(s) + revertir OPP/stock.\n"
            )

        if host:
            self._correr_host_directo(
                base, fechas_iso, host, port or 3306, aplicar=aplicar
            )
        else:
            with mysql_cursor(base, dict_cursor=True) as cursor:
                for fecha_iso in fechas_iso:
                    self._inventariar(cursor, base, fecha_iso, _fmt_fecha_es(fecha_iso))
                    if aplicar:
                        self._aplicar_fecha(cursor, base, fecha_iso, _fmt_fecha_es(fecha_iso))
                    if len(fechas_iso) > 1:
                        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Apply' if aplicar else 'Inventario dry-run'} completado — "
                f"{base}, {fechas_es}."
            )
        )

    def _correr_host_directo(
        self,
        base: str,
        fechas_iso: List[str],
        host: str,
        port: int,
        *,
        aplicar: bool,
    ) -> None:
        """Dry-run/apply contra host explícito. Credenciales DB_USER/DB_PASSWORD."""
        import os

        import MySQLdb

        user = os.environ.get("DB_USER") or ""
        passwd = os.environ.get("DB_PASSWORD") or ""
        if not user:
            raise CommandError("Falta DB_USER en el entorno para --host.")
        conn = MySQLdb.connect(
            host=host,
            port=int(port),
            user=user,
            passwd=passwd,
            db=base,
            charset="utf8mb4",
            connect_timeout=12,
        )
        try:
            conn.autocommit(False)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            for fecha_iso in fechas_iso:
                self._inventariar(cursor, base, fecha_iso, _fmt_fecha_es(fecha_iso))
                if aplicar:
                    self._aplicar_fecha(
                        cursor, base, fecha_iso, _fmt_fecha_es(fecha_iso), conn=conn
                    )
                else:
                    conn.rollback()
                if len(fechas_iso) > 1:
                    self.stdout.write("")
        finally:
            conn.close()

    def _inventariar_host_directo(
        self,
        base: str,
        fechas_iso: List[str],
        host: str,
        port: int,
    ) -> None:
        """Compat: dry-run contra host explícito."""
        self._correr_host_directo(base, fechas_iso, host, port, aplicar=False)

    def _inventariar(self, cursor, base: str, fecha_iso: str, fecha_es: str) -> None:
        tbl_parte = _nombre_tabla(cursor, "mpr_parte")
        tbl_linea = _nombre_tabla(cursor, "mpr_parte_linea")
        tbl_ajuste = _nombre_tabla(cursor, "mpr_parte_ajuste")
        tbl_turno = _nombre_tabla(cursor, "mpr_turno")
        tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
        tbl_stock = _nombre_tabla(cursor, "stock")
        tbl_cc = _nombre_tabla(cursor, "mpr_transicion_lote")
        tbl_art = _nombre_tabla(cursor, "articulo")

        if not tbl_parte:
            raise CommandError(f"No existe mpr_parte en {base}.")

        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Fecha {fecha_es} ({fecha_iso}) ==="))
        self.stdout.write(
            "Al apply: se eliminarán TODOS los partes listados abajo (sin conservar ninguno).\n"
        )

        join_turno = ""
        col_turno = "CAST(p.id_mpr_turno AS CHAR)"
        group_turno = "p.id_mpr_turno"
        if tbl_turno:
            join_turno = f" LEFT JOIN `{tbl_turno}` t ON t.id_mpr_turno = p.id_mpr_turno"
            col_turno = "COALESCE(t.nombre, CAST(p.id_mpr_turno AS CHAR))"
            group_turno = "t.nombre, p.id_mpr_turno"

        join_linea = ""
        sum_lineas = "0"
        if tbl_linea:
            join_linea = f" LEFT JOIN `{tbl_linea}` pl ON pl.id_mpr_parte = p.id_mpr_parte"
            sum_lineas = "COALESCE(SUM(pl.cantidad), 0)"

        cursor.execute(
            f"""
            SELECT p.id_mpr_parte, p.uuid_parte, {col_turno} AS turno,
                   p.movimiento_fisico_ok,
                   {sum_lineas} AS pares_lineas
            FROM `{tbl_parte}` p
            {join_linea}
            {join_turno}
            WHERE p.fecha_produccion = %s
            GROUP BY p.id_mpr_parte, p.uuid_parte, p.movimiento_fisico_ok, {group_turno}
            ORDER BY p.id_mpr_parte
            """,
            [fecha_iso],
        )
        partes = list(cursor.fetchall() or [])

        ajustes_por_parte: dict[int, Decimal] = {}
        ids_parte: list[int] = []
        uuids: list[str] = []
        if tbl_ajuste and partes:
            ids = [to_int_or_none(_row_val(p, "id_mpr_parte")) for p in partes]
            ids = [i for i in ids if i is not None]
            if ids:
                ph = ",".join(["%s"] * len(ids))
                cursor.execute(
                    f"""
                    SELECT id_mpr_parte, COALESCE(SUM(delta), 0) AS pares_ajuste
                    FROM `{tbl_ajuste}`
                    WHERE id_mpr_parte IN ({ph})
                    GROUP BY id_mpr_parte
                    """,
                    ids,
                )
                for row in cursor.fetchall() or []:
                    pid = to_int_or_none(_row_val(row, "id_mpr_parte"))
                    if pid is not None:
                        ajustes_por_parte[pid] = to_decimal_or_none(
                            _row_val(row, "pares_ajuste")
                        ) or Decimal("0")

        self.stdout.write(self.style.MIGRATE_HEADING(f"1. Partes mpr_parte ({fecha_es}) — a ELIMINAR"))
        if not partes:
            self.stdout.write("  (sin partes en esa fecha)")
        else:
            self.stdout.write(
                f"  {'ID':>8}  {'UUID':36}  {'Turno':16}  {'Físico':6}  {'Σ pares':>10}"
            )
            total_pares = Decimal("0")
            for p in partes:
                pid = to_int_or_none(_row_val(p, "id_mpr_parte"))
                uuid_parte = str_or_blank(_row_val(p, "uuid_parte"))
                turno = str_or_blank(_row_val(p, "turno"))
                fisico = to_int_or_none(_row_val(p, "movimiento_fisico_ok")) or 0
                pares_lin = to_decimal_or_none(_row_val(p, "pares_lineas")) or Decimal("0")
                pares_aj = ajustes_por_parte.get(pid or -1, Decimal("0"))
                sigma = pares_lin + pares_aj
                total_pares += sigma
                if pid is not None:
                    ids_parte.append(pid)
                if uuid_parte:
                    uuids.append(uuid_parte)
                self.stdout.write(
                    f"  {pid or '-':>8}  {uuid_parte or '-':36}  {turno[:16]:16}  "
                    f"{'Sí' if fisico else 'No':6}  {_fmt_decimal(sigma):>10}"
                )
            self.stdout.write(
                f"  Total partes a eliminar: {len(partes)} | Σ pares global: {_fmt_decimal(total_pares)}"
            )

        # Artículos de los partes
        arts: set[int] = set()
        if tbl_linea and ids_parte:
            ph = ",".join(["%s"] * len(ids_parte))
            cursor.execute(
                f"""
                SELECT DISTINCT id_articulo FROM `{tbl_linea}`
                WHERE id_mpr_parte IN ({ph})
                """,
                ids_parte,
            )
            for row in cursor.fetchall() or []:
                aid = to_int_or_none(_row_val(row, "id_articulo"))
                if aid is not None:
                    arts.add(aid)

        # Movimientos OPP-parte ligados por UUID en detalle
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("2. movimiento_stock OPP-parte (detalle con UUID)"))
        movimientos: list[dict[str, Any]] = []
        codigos_opp: list[int] = []
        if not tbl_mov:
            self.stdout.write(self.style.WARNING("  Tabla movimiento_stock no encontrada."))
        elif not uuids:
            self.stdout.write("  (sin UUID de partes para cruzar)")
        else:
            cursor.execute(
                f"""
                SELECT codigo_movimiento, detalle, fecha, tipo_mov, motivo_movimiento, anulado
                FROM `{tbl_mov}`
                WHERE detalle LIKE %s
                  AND COALESCE(anulado, 'No') <> 'Si'
                ORDER BY codigo_movimiento
                """,
                ["%OPP-parte%"],
            )
            for row in cursor.fetchall() or []:
                detalle = str_or_blank(_row_val(row, "detalle"))
                if not any(u in detalle for u in uuids):
                    continue
                movimientos.append(
                    {
                        "codigo_movimiento": to_int_or_none(_row_val(row, "codigo_movimiento")),
                        "detalle": detalle,
                        "fecha": _row_val(row, "fecha"),
                        "tipo_mov": str_or_blank(_row_val(row, "tipo_mov")),
                        "motivo_movimiento": str_or_blank(_row_val(row, "motivo_movimiento")),
                    }
                )
                cm = to_int_or_none(_row_val(row, "codigo_movimiento"))
                if cm:
                    codigos_opp.append(cm)

            if not movimientos:
                self.stdout.write("  (sin movimientos OPP-parte ligados a los UUID del día)")
            else:
                self.stdout.write(
                    f"  {'Código':>8}  {'Fecha':12}  {'Tipo':6}  Detalle"
                )
                for m in movimientos:
                    f = m.get("fecha")
                    ftxt = str(f)[:10] if f else "-"
                    self.stdout.write(
                        f"  {m['codigo_movimiento'] or '-':>8}  {ftxt:12}  "
                        f"{(m.get('tipo_mov') or '-')[:6]:6}  {m.get('detalle', '')[:80]}"
                    )
                self.stdout.write(f"  Total movimientos OPP-parte: {len(movimientos)}")

        # Σ Entrada stock por artículo
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("3. Σ Entrada stock por artículo (OPP-parte del día)")
        )
        if not tbl_stock or not codigos_opp:
            self.stdout.write("  (sin renglones stock para los OPP-parte encontrados)")
        else:
            ph = ",".join(["%s"] * len(codigos_opp))
            join_art = ""
            cols_art = "s.IDArt AS id_articulo"
            group_art = "s.IDArt"
            if tbl_art:
                join_art = f" LEFT JOIN `{tbl_art}` a ON a.IDArt = s.IDArt"
                # Schema AdministraNET: CodigoArticulo (no CodigoManual/Descripcion en todas las bases).
                cols_art = "s.IDArt AS id_articulo, a.CodigoArticulo AS codigo_manual"
                group_art = "s.IDArt, a.CodigoArticulo"
            # Algunas bases no tienen stock.anulado; filtrar solo si la columna existe.
            where_anulado = ""
            cursor.execute(f"SHOW COLUMNS FROM `{tbl_stock}` LIKE 'anulado'")
            if cursor.fetchone():
                where_anulado = " AND COALESCE(s.anulado, 'No') <> 'Si'"
            cursor.execute(
                f"""
                SELECT {cols_art},
                       COALESCE(SUM(s.Entrada), 0) AS entrada,
                       COALESCE(SUM(s.Salida), 0) AS salida
                FROM `{tbl_stock}` s
                {join_art}
                WHERE s.CodigoMovimiento IN ({ph})
                {where_anulado}
                GROUP BY {group_art}
                ORDER BY entrada DESC, s.IDArt
                """,
                codigos_opp,
            )
            rows_stock = list(cursor.fetchall() or [])
            if not rows_stock:
                self.stdout.write("  (sin entradas en stock para esos códigos)")
            else:
                self.stdout.write(
                    f"  {'Artículo':>8}  {'Código':12}  {'Σ Entrada':>12}  {'Σ Salida':>10}"
                )
                for row in rows_stock:
                    aid = to_int_or_none(_row_val(row, "id_articulo"))
                    cod = str_or_blank(_row_val(row, "codigo_manual"))[:12]
                    ent = _fmt_decimal(_row_val(row, "entrada"))
                    sal = _fmt_decimal(_row_val(row, "salida"))
                    self.stdout.write(
                        f"  {aid or '-':>8}  {cod or '-':12}  {ent:>12}  {sal:>10}"
                    )

        # CC (mpr_transicion_lote)
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("4. mpr_transicion_lote (CC — clasificación)"))
        if not tbl_cc:
            self.stdout.write(self.style.WARNING("  Tabla mpr_transicion_lote no encontrada."))
        else:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS n, COALESCE(SUM(cantidad), 0) AS pares
                FROM `{tbl_cc}`
                WHERE fecha_produccion = %s
                """,
                [fecha_iso],
            )
            cc_fecha = cursor.fetchone()
            n_cc_fecha = to_int_or_none(_row_val(cc_fecha, "n")) or 0
            pares_cc_fecha = _fmt_decimal(_row_val(cc_fecha, "pares"))
            self.stdout.write(
                f"  CC con fecha_produccion={fecha_es}: {n_cc_fecha} filas, Σ pares={pares_cc_fecha}"
            )

            if cc_fecha and n_cc_fecha:
                cursor.execute(
                    f"""
                    SELECT id_mpr_transicion_lote, id_articulo, tipo_origen, tipo_destino,
                           cantidad, codigo_movimiento
                    FROM `{tbl_cc}`
                    WHERE fecha_produccion = %s
                    ORDER BY id_mpr_transicion_lote
                    LIMIT 50
                    """,
                    [fecha_iso],
                )
                for row in cursor.fetchall() or []:
                    self.stdout.write(
                        f"    id={_row_val(row, 'id_mpr_transicion_lote')} "
                        f"art={_row_val(row, 'id_articulo')} "
                        f"{str_or_blank(_row_val(row, 'tipo_origen'))}"
                        f"→{str_or_blank(_row_val(row, 'tipo_destino'))} "
                        f"pares={_fmt_decimal(_row_val(row, 'cantidad'))} "
                        f"cm={_row_val(row, 'codigo_movimiento') or '-'}"
                    )
                if n_cc_fecha > 50:
                    self.stdout.write(f"    … y {n_cc_fecha - 50} filas más")

            if arts:
                ph = ",".join(["%s"] * len(arts))
                cursor.execute(
                    f"""
                    SELECT COUNT(*) AS n, COALESCE(SUM(cantidad), 0) AS pares
                    FROM `{tbl_cc}`
                    WHERE id_articulo IN ({ph})
                    """,
                    list(arts),
                )
                cc_arts = cursor.fetchone()
                n_cc_arts = to_int_or_none(_row_val(cc_arts, "n")) or 0
                pares_cc_arts = _fmt_decimal(_row_val(cc_arts, "pares"))
                self.stdout.write(
                    f"  CC de artículos de estos partes (cualquier fecha): "
                    f"{n_cc_arts} filas, Σ pares={pares_cc_arts}"
                )
                cursor.execute(
                    f"""
                    SELECT fecha_produccion, COUNT(*) AS n, COALESCE(SUM(cantidad), 0) AS pares
                    FROM `{tbl_cc}`
                    WHERE id_articulo IN ({ph})
                    GROUP BY fecha_produccion
                    ORDER BY fecha_produccion
                    """,
                    list(arts),
                )
                por_fecha = list(cursor.fetchall() or [])
                if por_fecha:
                    self.stdout.write("  Desglose CC por fecha_produccion (artículos del día):")
                    for row in por_fecha:
                        f = _row_val(row, "fecha_produccion")
                        ftxt = _fmt_fecha_es(str(f)[:10]) if f else "-"
                        self.stdout.write(
                            f"    {ftxt}: {_row_val(row, 'n')} filas, "
                            f"Σ pares={_fmt_decimal(_row_val(row, 'pares'))}"
                        )
            else:
                self.stdout.write(
                    "  (sin artículos en líneas de parte — no se cruza CC histórico por artículo)"
                )

        # Advertencia CC
        self.stdout.write("")
        hay_cc = False
        if tbl_cc:
            cursor.execute(
                f"SELECT COUNT(*) AS n FROM `{tbl_cc}` WHERE fecha_produccion = %s",
                [fecha_iso],
            )
            hay_cc = (to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0) > 0
            if not hay_cc and arts:
                ph = ",".join(["%s"] * len(arts))
                cursor.execute(
                    f"SELECT COUNT(*) AS n FROM `{tbl_cc}` WHERE id_articulo IN ({ph})",
                    list(arts),
                )
                hay_cc = (to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0) > 0

        if hay_cc:
            self.stdout.write(
                self.style.WARNING(
                    "ADVERTENCIA: Hay registros CC (mpr_transicion_lote). "
                    "Un apply futuro debe revertir CC primero (anular_cc aún no está en producto)."
                )
            )
        else:
            self.stdout.write(
                "Sin CC detectada para esta fecha/artículos; apply: "
                "anular OPP + ajustar stock_deposito + borrar TODOS los partes del día."
            )

    def _aplicar_fecha(
        self,
        cursor,
        base: str,
        fecha_iso: str,
        fecha_es: str,
        conn=None,
    ) -> None:
        """Anula OPP-parte, ajusta stock_deposito y borra partes de la fecha.

        - Si hay CC en la fecha: aborta (anular_cc no implementado).
        - Por cada movimiento OPP-parte ligado a UUID del día: marca anulado='Si'
          en movimiento_stock/stock y descuenta Entrada-Salida de stock_deposito.
        - DELETE mpr_parte_ajuste / mpr_parte_linea / mpr_parte.
        """
        tbl_parte = _nombre_tabla(cursor, "mpr_parte")
        tbl_linea = _nombre_tabla(cursor, "mpr_parte_linea")
        tbl_ajuste = _nombre_tabla(cursor, "mpr_parte_ajuste")
        tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
        tbl_stock = _nombre_tabla(cursor, "stock")
        tbl_sd = _nombre_tabla(cursor, "stock_deposito")
        tbl_cc = _nombre_tabla(cursor, "mpr_transicion_lote")
        tbl_hist = _nombre_tabla(cursor, "lista_produccion_historico")

        if not tbl_parte:
            raise CommandError(f"No existe mpr_parte en {base}.")

        if tbl_cc:
            cursor.execute(
                f"SELECT COUNT(*) AS n FROM `{tbl_cc}` WHERE fecha_produccion = %s",
                [fecha_iso],
            )
            n_cc = to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0
            if n_cc > 0:
                raise CommandError(
                    f"Abortado {fecha_es}: hay {n_cc} filas CC (mpr_transicion_lote). "
                    "Revertir CC antes de apply (aún no automatizado)."
                )

        cursor.execute(
            f"""
            SELECT id_mpr_parte, uuid_parte
            FROM `{tbl_parte}`
            WHERE fecha_produccion = %s
            ORDER BY id_mpr_parte
            """,
            [fecha_iso],
        )
        partes = list(cursor.fetchall() or [])
        ids_parte = [
            pid
            for pid in (to_int_or_none(_row_val(p, "id_mpr_parte")) for p in partes)
            if pid is not None
        ]
        uuids = [
            u
            for u in (str_or_blank(_row_val(p, "uuid_parte")) for p in partes)
            if u
        ]

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"APPLY {fecha_es}: {len(ids_parte)} partes")
        )
        if not ids_parte:
            self.stdout.write("  (nada que borrar)")
            if conn is not None:
                conn.commit()
            return

        # OPP-parte por UUID
        codigos_opp: list[int] = []
        if tbl_mov and uuids:
            cursor.execute(
                f"""
                SELECT codigo_movimiento, detalle
                FROM `{tbl_mov}`
                WHERE detalle LIKE %s
                  AND COALESCE(anulado, 'No') <> 'Si'
                """,
                ["%OPP-parte%"],
            )
            for row in cursor.fetchall() or []:
                detalle = str_or_blank(_row_val(row, "detalle"))
                if not any(u in detalle for u in uuids):
                    continue
                cm = to_int_or_none(_row_val(row, "codigo_movimiento"))
                if cm and cm not in codigos_opp:
                    codigos_opp.append(cm)

        stock_tiene_anulado = False
        if tbl_stock:
            cursor.execute(f"SHOW COLUMNS FROM `{tbl_stock}` LIKE 'anulado'")
            stock_tiene_anulado = bool(cursor.fetchone())

        n_sd = 0
        n_stock_anulado = 0
        n_mov_anulado = 0
        saldos_negativos: list[str] = []

        if tbl_stock and tbl_sd and codigos_opp:
            ph = ",".join(["%s"] * len(codigos_opp))
            where_anulado = (
                " AND COALESCE(anulado, 'No') <> 'Si'" if stock_tiene_anulado else ""
            )
            cursor.execute(
                f"""
                SELECT CodigoMovimiento, IDArt, CodDeposito, Entrada, Salida
                FROM `{tbl_stock}`
                WHERE CodigoMovimiento IN ({ph})
                {where_anulado}
                """,
                codigos_opp,
            )
            stock_rows = list(cursor.fetchall() or [])
            for sr in stock_rows:
                id_art = to_int_or_none(_row_val(sr, "IDArt", "idart"))
                id_dep = to_int_or_none(_row_val(sr, "CodDeposito", "coddeposito"))
                entrada = to_decimal_or_none(_row_val(sr, "Entrada", "entrada")) or Decimal(
                    "0"
                )
                salida = to_decimal_or_none(_row_val(sr, "Salida", "salida")) or Decimal(
                    "0"
                )
                if id_art is None or id_dep is None:
                    continue
                # Revertir efecto neto del renglón: sd += Salida - Entrada
                delta = salida - entrada
                if delta == 0:
                    continue
                cursor.execute(
                    f"""
                    SELECT id_stock_deposito, saldo
                    FROM `{tbl_sd}`
                    WHERE id_articulo = %s AND id_deposito = %s
                    FOR UPDATE
                    """,
                    [id_art, id_dep],
                )
                sd_row = cursor.fetchone()
                if sd_row:
                    sid = to_int_or_none(
                        _row_val(sd_row, "id_stock_deposito", "id_stock_deposito")
                    )
                    saldo_actual = to_decimal_or_none(
                        _row_val(sd_row, "saldo")
                    ) or Decimal("0")
                    nuevo = saldo_actual + delta
                    cursor.execute(
                        f"UPDATE `{tbl_sd}` SET saldo = %s WHERE id_stock_deposito = %s",
                        [nuevo, sid],
                    )
                    n_sd += 1
                    if nuevo < 0:
                        saldos_negativos.append(
                            f"art={id_art} dep={id_dep} saldo={_fmt_decimal(nuevo)}"
                        )
                elif delta > 0:
                    cursor.execute(
                        f"""
                        INSERT INTO `{tbl_sd}` (id_articulo, id_deposito, saldo)
                        VALUES (%s, %s, %s)
                        """,
                        [id_art, id_dep, delta],
                    )
                    n_sd += 1

            if stock_tiene_anulado:
                cursor.execute(
                    f"""
                    UPDATE `{tbl_stock}`
                    SET anulado = 'Si'
                    WHERE CodigoMovimiento IN ({ph})
                      AND COALESCE(anulado, 'No') <> 'Si'
                    """,
                    codigos_opp,
                )
                n_stock_anulado = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
            else:
                cursor.execute(
                    f"DELETE FROM `{tbl_stock}` WHERE CodigoMovimiento IN ({ph})",
                    codigos_opp,
                )
                n_stock_anulado = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        if tbl_mov and codigos_opp:
            ph = ",".join(["%s"] * len(codigos_opp))
            cursor.execute(
                f"""
                UPDATE `{tbl_mov}`
                SET anulado = 'Si'
                WHERE codigo_movimiento IN ({ph})
                  AND COALESCE(anulado, 'No') <> 'Si'
                """,
                codigos_opp,
            )
            n_mov_anulado = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        # Histórico best-effort (columna real: codigo_movimiento_mstock)
        n_hist = 0
        if tbl_hist and codigos_opp:
            cursor.execute(f"SHOW COLUMNS FROM `{tbl_hist}`")
            hist_cols = {
                str(_row_val(r, "Field", "field") or "").lower()
                for r in (cursor.fetchall() or [])
            }
            col_hist = None
            for cand in ("codigo_movimiento_mstock", "codigo_movimiento"):
                if cand in hist_cols:
                    col_hist = cand
                    break
            if not col_hist:
                self.stdout.write(
                    "  Histórico: sin columna codigo_movimiento_mstock "
                    "(ni codigo_movimiento); se omite limpieza."
                )
            else:
                ph = ",".join(["%s"] * len(codigos_opp))
                cursor.execute(
                    f"DELETE FROM `{tbl_hist}` WHERE `{col_hist}` IN ({ph})",
                    codigos_opp,
                )
                n_hist = (
                    cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
                )

        ph_partes = ",".join(["%s"] * len(ids_parte))
        n_aj = 0
        n_lin = 0
        if tbl_ajuste:
            cursor.execute(
                f"DELETE FROM `{tbl_ajuste}` WHERE id_mpr_parte IN ({ph_partes})",
                ids_parte,
            )
            n_aj = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        if tbl_linea:
            cursor.execute(
                f"DELETE FROM `{tbl_linea}` WHERE id_mpr_parte IN ({ph_partes})",
                ids_parte,
            )
            n_lin = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        cursor.execute(
            f"DELETE FROM `{tbl_parte}` WHERE id_mpr_parte IN ({ph_partes})",
            ids_parte,
        )
        n_partes = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

        if conn is not None:
            conn.commit()
        # mysql_cursor del pool suele commitear al salir del with

        self.stdout.write(
            f"  OPP anulados: {n_mov_anulado} mov / {n_stock_anulado} stock | "
            f"sd ajustes: {n_sd} | hist: {n_hist} | "
            f"borrados: partes={n_partes} líneas={n_lin} ajustes={n_aj}"
        )
        if saldos_negativos:
            self.stdout.write(
                self.style.WARNING(
                    "  Aviso: saldos stock_deposito negativos tras revertir "
                    f"(ajustes posteriores pueden explicarlos): "
                    + "; ".join(saldos_negativos[:8])
                    + (" …" if len(saldos_negativos) > 8 else "")
                )
            )

        # Verificación
        cursor.execute(
            f"SELECT COUNT(*) AS n FROM `{tbl_parte}` WHERE fecha_produccion = %s",
            [fecha_iso],
        )
        quedan = to_int_or_none(_row_val(cursor.fetchone(), "n")) or 0
        if quedan:
            raise CommandError(
                f"Post-apply {fecha_es}: aún quedan {quedan} partes (rollback manual requerido)."
            )
        self.stdout.write(self.style.SUCCESS(f"  OK {fecha_es}: 0 partes residuales."))


def str_or_blank(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()
