"""
Obtiene opciones para el formulario de configuración de kioscos:
sucursales, puntos de venta (PV asociados a AFIP), depósitos.
"""
import logging
from typing import List, Dict, Any

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


def listar_puntos_venta(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista puntos de venta (PV) de la base. PV se asocia con AFIP/talonarios."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute("""
                SELECT id_punto_venta, nro_punto_venta, id_sucursal
                FROM punto_venta
                ORDER BY nro_punto_venta
            """)
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        logger.warning("listar_puntos_venta failed: %s", e)
        return []


def listar_depositos(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista depósitos (desde stock_deposito o tabla deposito)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute("""
                SELECT DISTINCT id_deposito FROM stock_deposito
                ORDER BY id_deposito
            """)
            rows = c.fetchall()
            if rows:
                return [{'id_deposito': r['id_deposito']} for r in rows]
            c.execute("SELECT CodDeposito as id_deposito FROM deposito ORDER BY CodDeposito")
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        logger.warning("listar_depositos failed: %s", e)
        return []


def listar_listas_precio(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista listas de precio para TPV. Si existe tabla lista_precio la usa; si no, devuelve Lista Oficial + Lista 1..5.
    Incluye descripcion cuando la tabla tiene esa columna, para mostrar "Lista 1 - Distribuidora"."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            try:
                c.execute("""
                    SELECT id_lista,
                           COALESCE(nombre, CONCAT('Lista ', id_lista)) AS nombre,
                           COALESCE(descripcion, '') AS descripcion
                    FROM lista_precio
                    ORDER BY id_lista
                """)
            except Exception:
                c.execute("""
                    SELECT id_lista, COALESCE(nombre, CONCAT('Lista ', id_lista)) AS nombre
                    FROM lista_precio
                    ORDER BY id_lista
                """)
            rows = c.fetchall()
            if rows:
                out = []
                for r in rows:
                    nombre = (r.get('nombre') or '').strip() or f"Lista {r['id_lista']}"
                    desc = (r.get('descripcion') or '').strip()
                    if desc:
                        nombre_display = f"{nombre} - {desc}"
                    else:
                        nombre_display = nombre
                    out.append({'id_lista': r['id_lista'], 'nombre': nombre_display})
                return out
    except Exception as e:
        logger.debug("listar_listas_precio (tabla lista_precio): %s", e)
    return [
        {'id_lista': 0, 'nombre': 'Lista Oficial'},
        {'id_lista': 1, 'nombre': 'Lista 1'},
        {'id_lista': 2, 'nombre': 'Lista 2'},
        {'id_lista': 3, 'nombre': 'Lista 3'},
        {'id_lista': 4, 'nombre': 'Lista 4'},
        {'id_lista': 5, 'nombre': 'Lista 5'},
    ]


def listar_viajantes(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista vendedores (viajantes) no anulados para asignar al kiosco."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute("""
                SELECT CodViajante, Nombre
                FROM viajantes
                WHERE anulado = 'No'
                ORDER BY Nombre
            """)
            return [dict(r) for r in c.fetchall()]
    except Exception as e:
        logger.warning("listar_viajantes failed: %s", e)
        return []


def listar_kiosks(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista todos los kioscos configurados (para admin). Incluye cod_viajante y enviar_factura_email si existen."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            try:
                c.execute("""
                    SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo,
                           COALESCE(enviar_factura_email, 1) AS enviar_factura_email,
                           COALESCE(modo_tpv, 0) AS modo_tpv, created_at, updated_at
                    FROM self_checkout_kiosk ORDER BY kiosk_id
                """)
            except Exception:
                try:
                    c.execute("""
                        SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo,
                               COALESCE(enviar_factura_email, 1) AS enviar_factura_email, created_at, updated_at
                        FROM self_checkout_kiosk ORDER BY kiosk_id
                    """)
                except Exception:
                    try:
                        c.execute("""
                            SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo, created_at, updated_at
                            FROM self_checkout_kiosk ORDER BY kiosk_id
                        """)
                    except Exception:
                        c.execute("""
                            SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, modo_rfid, activo, created_at, updated_at
                            FROM self_checkout_kiosk ORDER BY kiosk_id
                        """)
            rows = c.fetchall()
            out = [dict(r) for r in rows]
            for d in out:
                if 'cod_viajante' not in d:
                    d['cod_viajante'] = None
                if 'enviar_factura_email' not in d:
                    d['enviar_factura_email'] = 1
                if 'modo_tpv' not in d:
                    d['modo_tpv'] = 0
            return out
    except Exception as e:
        logger.warning("listar_kiosks failed: %s", e)
        return []
