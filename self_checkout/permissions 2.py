"""
Permisos Self-Checkout basados en modelo AdministraNET (MySQL).
usuarios → puestos → permiso_sistema / permiso_sistema_puesto
"""
import logging
from typing import Optional, Union, Any

from django.conf import settings

logger = logging.getLogger(__name__)

# Constantes (reutilizar de core para single source of truth)
try:
    from core.constantes_permisos import SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN, SCO_PERMISSIONS
except ImportError:
    SCO_KIOSK = 'self_checkout.kiosk'
    SCO_SUPERVISOR = 'self_checkout.supervisor'
    SCO_ADMIN = 'self_checkout.admin'
    SCO_PERMISSIONS = (SCO_KIOSK, SCO_SUPERVISOR, SCO_ADMIN)

# Jerarquía: admin implica supervisor y kiosk; supervisor implica kiosk
# Al verificar perm X, si tiene Y en esta lista también pasa
SCO_HIERARCHY = {
    SCO_KIOSK: [SCO_SUPERVISOR, SCO_ADMIN],
    SCO_SUPERVISOR: [SCO_ADMIN],
    SCO_ADMIN: [],
}


def has_permission(
    user: Any,
    perm_key: str,
    base_empresa: str,
) -> bool:
    """
    Verifica si el usuario tiene el permiso en AdministraNET MySQL.

    Consulta permiso_sistema + permiso_sistema_puesto por id_puesto.
    Usuario supervisor (cod_usuario) tiene todos los permisos.

    Args:
        user: Objeto con id_puesto, o dict con 'id_puesto'. Si tiene is_admin()=True, retorna True.
        perm_key: key_permiso (ej: 'self_checkout.kiosk')
        base_empresa: Base de datos de la empresa

    Returns:
        True si tiene permiso, False en caso contrario.
    """
    if not user:
        return False

    # Admin / supervisor (cod_usuario) tiene acceso total
    if hasattr(user, 'is_admin') and callable(user.is_admin) and user.is_admin():
        return True

    id_puesto = None
    if hasattr(user, 'id_puesto'):
        id_puesto = user.id_puesto
    elif isinstance(user, dict):
        id_puesto = user.get('id_puesto')

    if not id_puesto or not base_empresa:
        return False

    try:
        import MySQLdb
        mysql_config = settings.DATABASES['mysql']
        conn = MySQLdb.connect(
            host=mysql_config['HOST'],
            port=int(mysql_config.get('PORT', 3306)),
            user=mysql_config['USER'],
            passwd=mysql_config['PASSWORD'],
            db=base_empresa,
            charset='latin1',
        )
        cursor = conn.cursor()
        # Usar valor más reciente por id_permiso_sistema_puesto (mismo criterio que base_middleware)
        perms_to_check = [perm_key] + SCO_HIERARCHY.get(perm_key, [])

        placeholders = ','.join(['%s'] * len(perms_to_check))
        cursor.execute(f"""
            SELECT 1
            FROM permiso_sistema ps
            INNER JOIN (
                SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                FROM permiso_sistema_puesto psp1
                INNER JOIN (
                    SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) as max_id
                    FROM permiso_sistema_puesto
                    WHERE id_puesto = %s
                    GROUP BY id_permiso_sistema
                ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema
                       AND psp1.id_permiso_sistema_puesto = psp2.max_id
                WHERE psp1.id_puesto = %s AND psp1.valor_permiso = 'Si'
            ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
            WHERE ps.key_permiso IN ({placeholders})
            LIMIT 1
        """, [id_puesto, id_puesto] + list(perms_to_check))
        has = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return has
    except Exception as e:
        logger.warning('Error verificando permiso %s para puesto %s: %s', perm_key, id_puesto, e)
        return False


def has_sc_permission(user: Any, perm_code: str, base_empresa: str) -> bool:
    """
    Alias de has_permission para permisos Self-Checkout.
    perm_code: 'kiosk' | 'supervisor' | 'admin' (o key completo 'self_checkout.kiosk').
    """
    key = perm_code if perm_code.startswith('self_checkout.') else f'self_checkout.{perm_code}'
    return has_permission(user, key, base_empresa)


def has_any_self_checkout_permission(user: Any, base_empresa: str) -> bool:
    """True si tiene al menos uno de kiosk, supervisor o admin."""
    return any(has_permission(user, p, base_empresa) for p in SCO_PERMISSIONS)
