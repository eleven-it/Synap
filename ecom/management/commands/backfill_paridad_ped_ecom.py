"""
Backfill de paridad AdministraNET en PED e-commerce ya confirmados.

Corrige gaps previos del checkout Synap que impedían ver renglones en
Visualiza_Pedido (stockp.Alicuota = id de iva, no el %) y alinea cabecera
(ImporteVenta bruto / SubtotalDesc neto, CotiDolar, ImporteVentaL, autorreferencia).

Ejemplo (pedido masivo draft #3 en administranet1):

  docker exec Synap_app python manage.py backfill_paridad_ped_ecom \\
      --base administranet1 --detalle-like 'Pedido masivo Synap%'

  docker exec Synap_app python manage.py backfill_paridad_ped_ecom \\
      --base administranet1 --detalle-like 'Pedido masivo Synap%' --dry-run
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from ecom.services.numero_a_letras import numero_a_letras


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


class Command(BaseCommand):
    help = (
        "Backfill paridad PED ecom: stockp (Alicuota id/IIBB/saldo/coti) y "
        "comp_ped (ImporteVenta/SubtotalDesc/CotiDolar/ImporteVentaL)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base",
            required=True,
            help="Nombre de la base MySQL AdministraNET (ej. administranet1).",
        )
        parser.add_argument(
            "--detalle-like",
            default="Pedido masivo Synap%",
            help="Filtro LIKE sobre comp_ped.Detalle (default: Pedido masivo Synap%%).",
        )
        parser.add_argument(
            "--codigos",
            default="",
            help="Lista opcional de CodigoMovimiento separados por coma (acota el filtro).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra qué se corregiría, sin escribir.",
        )

    def handle(self, *args, **options):
        base = str(options["base"]).strip()
        detalle_like = str(options["detalle_like"] or "").strip()
        dry = bool(options["dry_run"])
        codigos = self._parse_codigos(options.get("codigos") or "")

        if not base:
            raise CommandError("Debe indicar --base.")
        if not detalle_like and not codigos:
            raise CommandError("Indique --detalle-like y/o --codigos.")

        pool = get_mysql_pool()
        with pool.get_connection(base) as conn:
            cur = conn.cursor()
            try:
                conn.autocommit(False)
                peds = self._listar_peds(cur, detalle_like, codigos)
                if not peds:
                    self.stdout.write(self.style.WARNING("No se encontraron PED a corregir."))
                    conn.rollback()
                    return

                coti_dolar, id_cotizacion = self._cotizacion(cur)
                self.stdout.write(
                    f"Base={base} dry_run={dry} PED={len(peds)} "
                    f"coti={coti_dolar} id_cotizacion={id_cotizacion}"
                )

                n_stockp = 0
                n_comp = 0
                for ped in peds:
                    cod = int(ped["CodigoMovimiento"])
                    n_stockp += self._backfill_stockp(
                        cur, cod, coti_dolar, id_cotizacion, dry=dry
                    )
                    if self._backfill_comp_ped(cur, ped, coti_dolar, dry=dry):
                        n_comp += 1

                if dry:
                    conn.rollback()
                    self.stdout.write(
                        self.style.WARNING(
                            f"[dry-run] stockp filas tocadas≈{n_stockp}, "
                            f"comp_ped cabeceras≈{n_comp} (sin commit)."
                        )
                    )
                else:
                    conn.commit()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"OK: stockp actualizadas={n_stockp}, "
                            f"comp_ped actualizadas={n_comp}."
                        )
                    )
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
            finally:
                try:
                    conn.autocommit(True)
                except Exception:
                    pass

    @staticmethod
    def _parse_codigos(raw: str) -> List[int]:
        out: List[int] = []
        for part in (raw or "").split(","):
            part = part.strip()
            if not part:
                continue
            v = to_int_or_none(part)
            if v is not None:
                out.append(int(v))
        return out

    def _listar_peds(
        self, cur, detalle_like: str, codigos: List[int]
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                CodigoMovimiento, NroComprobante, ImporteVenta, SubtotalDesc,
                SubTotalGral, CotiDolar, ImporteVentaL, cod_mov_ped_orginal,
                Nro_Comp_PED_orginal, Detalle, total_percep
            FROM comp_ped
            WHERE TipoComprobante = 'PED' AND Anulado = 'No'
        """
        params: List[Any] = []
        if detalle_like:
            sql += " AND Detalle LIKE %s"
            params.append(detalle_like)
        if codigos:
            ph = ",".join(["%s"] * len(codigos))
            sql += f" AND CodigoMovimiento IN ({ph})"
            params.extend(codigos)
        sql += " ORDER BY CodigoMovimiento"
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def _cotizacion(self, cur) -> Tuple[Decimal, int]:
        cur.execute(
            "SELECT ValorPesos, id_cotizacion FROM cotizacion ORDER BY id_cotizacion LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            return Decimal("1"), 1
        return _dec(row[0], "1"), to_int_or_none(row[1]) or 1

    def _backfill_stockp(
        self,
        cur,
        codigo_movimiento: int,
        coti_dolar: Decimal,
        id_cotizacion: int,
        *,
        dry: bool,
    ) -> int:
        cur.execute(
            """
            SELECT COUNT(*) FROM stockp WHERE CodigoMovimiento = %s
            """,
            [codigo_movimiento],
        )
        n = int(cur.fetchone()[0] or 0)
        if n == 0:
            self.stdout.write(
                self.style.WARNING(f"  PED {codigo_movimiento}: sin renglones stockp")
            )
            return 0

        if dry:
            cur.execute(
                """
                SELECT sp.id_stock, sp.IDArt, sp.Alicuota, a.Alicuota AS alic_ok,
                       sp.AlicuotaIB, a.AlicuotaIB AS ib_ok
                FROM stockp sp
                INNER JOIN articulo a ON a.IDArt = sp.IDArt
                WHERE sp.CodigoMovimiento = %s
                """,
                [codigo_movimiento],
            )
            for r in cur.fetchall():
                self.stdout.write(
                    f"  [dry] stockp id={r[0]} art={r[1]} "
                    f"Alicuota {r[2]}→{r[3]} AlicuotaIB {r[4]}→{r[5]}"
                )
            return n

        cur.execute(
            """
            UPDATE stockp sp
            INNER JOIN articulo a ON a.IDArt = sp.IDArt
            LEFT JOIN activ_iibb ai ON ai.id = a.AlicuotaIB
            LEFT JOIN iva i ON i.id = a.Alicuota
            LEFT JOIN stock_deposito sd
                   ON sd.id_articulo = sp.IDArt
                  AND sd.id_deposito = sp.CodDeposito
            SET
                sp.Alicuota = a.Alicuota,
                sp.imp_alicuota_iva = COALESCE(i.Alicuota, sp.imp_alicuota_iva, 0),
                sp.AlicuotaIB = a.AlicuotaIB,
                sp.imp_alicuota_iibb = COALESCE(ai.alicuota, 0),
                sp.saldo = COALESCE(sd.saldo_pedido_cliente, 0),
                sp.coti_dolar = %s,
                sp.id_cotizacion = %s,
                sp.cantidad_pendiente_opt = sp.Cantidad,
                sp.cantidad_fab_pendiente_opt = sp.Cantidad,
                sp.promocion_tipo = IF(COALESCE(sp.promocion, 'No') = 'Si',
                                      COALESCE(sp.promocion_tipo, ''), ''),
                sp.promocion_cant = IF(COALESCE(sp.promocion, 'No') = 'Si',
                                      COALESCE(sp.promocion_cant, 0), 0),
                sp.promocion_por = IF(COALESCE(sp.promocion, 'No') = 'Si',
                                     COALESCE(sp.promocion_por, 0), 0)
            WHERE sp.CodigoMovimiento = %s
            """,
            [coti_dolar, id_cotizacion, codigo_movimiento],
        )
        return int(cur.rowcount or 0)

    def _backfill_comp_ped(
        self,
        cur,
        ped: Dict[str, Any],
        coti_dolar: Decimal,
        *,
        dry: bool,
    ) -> bool:
        cod = int(ped["CodigoMovimiento"])
        nro = str(ped.get("NroComprobante") or "")
        importe = _dec(ped.get("ImporteVenta"))
        sub_desc = _dec(ped.get("SubtotalDesc"))
        sub_gral = _dec(ped.get("SubTotalGral"))
        total_percep = _dec(ped.get("total_percep"))

        # Patrón Synap previo: ImporteVenta=neto, SubtotalDesc=bruto (invertido).
        # Se detecta cuando SubtotalDesc > ImporteVenta y SubTotalGral ≈ ImporteVenta.
        invertido = sub_desc > importe and abs(sub_gral - importe) <= Decimal("0.05")
        if invertido:
            nuevo_importe = sub_desc
            nuevo_sub = importe
        else:
            # Ya corregido o legacy: asegurar ImporteVenta >= neto
            nuevo_importe = max(importe, sub_desc)
            nuevo_sub = sub_gral if sub_gral > 0 else min(importe, sub_desc)

        # Si el total todavía no incluye percep y total_percep > 0 y coincide neto+iva
        if total_percep > 0 and nuevo_importe == (sub_desc if invertido else importe):
            # no sumar dos veces; el SubtotalDesc bruto de Synap viejo ya era total c/IVA sin percep típico
            pass

        letras = numero_a_letras(float(nuevo_importe))
        if dry:
            self.stdout.write(
                f"  [dry] comp_ped {cod} {nro}: "
                f"ImporteVenta {importe}→{nuevo_importe} "
                f"SubtotalDesc {sub_desc}→{nuevo_sub} "
                f"CotiDolar→{coti_dolar}"
            )
            return True

        cur.execute(
            """
            UPDATE comp_ped SET
                ImporteVenta = %s,
                SubtotalDesc = %s,
                CotiDolar = %s,
                ImporteVentaL = %s,
                cod_mov_ped_orginal = %s,
                Nro_Comp_PED_orginal = %s
            WHERE CodigoMovimiento = %s
            """,
            [
                nuevo_importe,
                nuevo_sub,
                coti_dolar,
                letras,
                cod,
                nro,
                cod,
            ],
        )
        return int(cur.rowcount or 0) > 0
