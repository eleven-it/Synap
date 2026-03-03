"""
KioskSessionService: valida kiosco, resuelve id_pv, id_deposito, codSucursal
desde sesión / config. Asegura que un kiosco opere solo con su config asignada.
"""
import logging
from typing import Optional, Dict, Any, Tuple

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)


class KioskSessionService:
    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa

    def get_kiosk_config(self, kiosk_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene configuración del kiosco (activo). Incluye cod_viajante, enviar_factura_email y modo_tpv si existen."""
        with mysql_cursor(self.base_empresa, dict_cursor=True) as cursor:
            try:
                cursor.execute("""
                    SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo,
                           COALESCE(enviar_factura_email, 1) AS enviar_factura_email,
                           COALESCE(modo_tpv, 0) AS modo_tpv
                    FROM self_checkout_kiosk WHERE kiosk_id = %s AND activo = 1
                """, [kiosk_id])
            except Exception:
                try:
                    cursor.execute("""
                        SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo,
                               COALESCE(enviar_factura_email, 1) AS enviar_factura_email
                        FROM self_checkout_kiosk WHERE kiosk_id = %s AND activo = 1
                    """, [kiosk_id])
                except Exception:
                    try:
                        cursor.execute("""
                            SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, activo
                            FROM self_checkout_kiosk WHERE kiosk_id = %s AND activo = 1
                        """, [kiosk_id])
                    except Exception:
                        cursor.execute("""
                            SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, modo_rfid, activo
                            FROM self_checkout_kiosk WHERE kiosk_id = %s AND activo = 1
                        """, [kiosk_id])
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if 'cod_viajante' not in d:
                d['cod_viajante'] = None
            if 'enviar_factura_email' not in d:
                d['enviar_factura_email'] = 1
            if 'modo_tpv' not in d:
                d['modo_tpv'] = 0
            return d

    def resolve_context(
        self,
        kiosk_id: str,
        session_user: dict,
        es_admin: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Resuelve id_sucursal, id_punto_venta, id_deposito (codSucursal = id_sucursal para VB6).
        Prioridad: config kiosco > sesión usuario.
        Returns: (context_dict, error_msg) - context tiene id_sucursal, id_punto_venta, id_deposito, cod_sucursal
        """
        config = self.get_kiosk_config(kiosk_id)
        if config:
            id_sucursal = config['id_sucursal']
            id_punto_venta = config['id_punto_venta']
            id_deposito = config['id_deposito']
            # Validar alcance si no es admin
            if not es_admin:
                ok, err = self.validar_alcance_usuario(
                    kiosk_id,
                    session_user.get('id_sucursal'),
                    session_user.get('id_punto_venta'),
                    session_user.get('id_deposito'),
                    es_admin=False,
                )
                if not ok:
                    return None, err
        else:
            id_sucursal = session_user.get('id_sucursal')
            id_punto_venta = session_user.get('id_punto_venta')
            id_deposito = session_user.get('id_deposito')
            if not all([id_sucursal is not None, id_punto_venta is not None, id_deposito is not None]):
                return None, 'Kiosco no configurado y sesión sin sucursal/pv/depósito'

        return {
            'id_sucursal': int(id_sucursal),
            'id_punto_venta': int(id_punto_venta),
            'id_deposito': int(id_deposito),
            'cod_sucursal': int(id_sucursal),  # VB6 cuentacliente.CodSucursal
        }, None

    def validar_alcance_usuario(
        self,
        kiosk_id: str,
        id_sucursal: Optional[int],
        id_punto_venta: Optional[int],
        id_deposito: Optional[int],
        es_admin: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que el usuario pueda operar este kiosco.
        es_admin: si tiene self_checkout.admin, no restringe por sucursal.
        Returns: (ok, mensaje_error)
        """
        config = self.get_kiosk_config(kiosk_id)
        if not config:
            return False, 'Kiosco no configurado o inactivo'

        if es_admin:
            return True, None

        if id_sucursal is not None and config['id_sucursal'] != id_sucursal:
            return False, 'No tiene acceso a esta sucursal'
        if id_punto_venta is not None and config['id_punto_venta'] != id_punto_venta:
            return False, 'No tiene acceso a este punto de venta'
        if id_deposito is not None and config['id_deposito'] != id_deposito:
            return False, 'No tiene acceso a este depósito'

        return True, None
