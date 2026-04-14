"""
Permisos de usuario según AdministraNET (MySQL).
Fuentes: permiso_sistema + permiso_sistema_puesto; y tabla permisos (Clavemenu) mapeada a key_permiso.
Usado por middleware (request.user.get_permisos_totales) y self_checkout (has_permission).
"""
import logging
from typing import Optional, Set

from core.constantes_permisos import MAPEO_MENU_A_PERMISO
from core.mysql_pool import mysql_cursor

logger = logging.getLogger(__name__)

# Permisos Reports que se agregan a usuario/puesto "Supervisor" (nombre o cod_usuario)
REPORTS_PERMISSIONS_FOR_SUPERVISOR = {
    "reports.ver",
    "reports.*",
    "reports.view_operational",
    "reports.view_managerial",
    "reports.dashboard",
    "reports.exportar",
    "reports.builder",
    "reports.programar",
}


def get_permisos_totales_administranet(
    base_empresa: str,
    id_puesto: Optional[int],
    cod_usuario: Optional[str] = None,
    nombre_puesto: Optional[str] = None,
) -> Set[str]:
    """
    Obtiene el set de key_permiso (valor_permiso = 'Si') para el puesto en MySQL.
    Reglas AdministraNET:
    - Usuario con cod_usuario == 'supervisor' tiene todos los permisos ("*").
    - Puesto/usuario con nombre_puesto == 'Supervisor' o cod_usuario == 'supervisor'
      recibe además los permisos de Reports (reports.ver, reports.*, etc.).
    - Resto: solo los key_permiso con valor_permiso = 'Si' en permiso_sistema_puesto
      (valor más reciente por id_permiso_sistema_puesto por permiso).
    """
    cod_usuario_lower = (cod_usuario or "").strip().lower()
    nombre_puesto_lower = (nombre_puesto or "").strip().lower()

    if cod_usuario_lower == "supervisor":
        return {"*"}

    permisos = set()

    if base_empresa and id_puesto:
        try:
            with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
                cursor.execute(
                    """
                    SELECT ps.key_permiso, psp.valor_permiso
                    FROM permiso_sistema ps
                    INNER JOIN (
                        SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                        FROM permiso_sistema_puesto psp1
                        INNER JOIN (
                            SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) AS max_id
                            FROM permiso_sistema_puesto
                            WHERE id_puesto = %s
                            GROUP BY id_permiso_sistema
                        ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema
                               AND psp1.id_permiso_sistema_puesto = psp2.max_id
                        WHERE psp1.id_puesto = %s
                    ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
                    WHERE psp.valor_permiso = 'Si'
                    """,
                    [id_puesto, id_puesto],
                )
                for row in cursor.fetchall():
                    key_permiso = row[0] if row else None
                    if key_permiso:
                        permisos.add(key_permiso)

                # Incluir permisos mapeados desde tabla permisos (Clavemenu VB6)
                # para que keyCompStock etc. otorguen stock.crear_movimiento en Synap
                try:
                    cursor.execute(
                        """
                        SELECT Clavemenu FROM permisos
                        WHERE IDpuesto = %s AND (Permiso = '1' OR Permiso = 'Si')
                        """,
                        [str(id_puesto)],
                    )
                    for row in cursor.fetchall():
                        clavemenu = row[0] if row else None
                        if clavemenu and clavemenu in MAPEO_MENU_A_PERMISO:
                            permisos.add(MAPEO_MENU_A_PERMISO[clavemenu])
                except Exception as e_permisos:
                    logger.debug(
                        "No se pudo leer tabla permisos para puesto %s (puede no existir): %s",
                        id_puesto,
                        e_permisos,
                    )
        except Exception as e:
            logger.warning(
                "Error al obtener permisos desde MySQL para puesto %s: %s",
                id_puesto,
                e,
            )

    if cod_usuario_lower == "supervisor" or nombre_puesto_lower == "supervisor":
        permisos.update(REPORTS_PERMISSIONS_FOR_SUPERVISOR)
        logger.debug(
            "Permisos Reports agregados para cod_usuario=%s nombre_puesto=%s",
            cod_usuario_lower,
            nombre_puesto_lower,
        )

    return permisos


def tiene_permiso_administranet(
    base_empresa: str,
    id_puesto: Optional[int],
    codigo: str,
    cod_usuario: Optional[str] = None,
    nombre_puesto: Optional[str] = None,
) -> bool:
    """
    Verifica si el puesto/usuario tiene el permiso (o wildcard).
    codigo puede ser un key_permiso (ej: 'reports.ver') o se acepta 'modulo.*'.
    """
    permisos = get_permisos_totales_administranet(
        base_empresa, id_puesto, cod_usuario=cod_usuario, nombre_puesto=nombre_puesto
    )
    if "*" in permisos:
        return True
    if codigo in permisos:
        return True
    for perm in permisos:
        if perm.endswith(".*"):
            modulo = perm[:-2]
            if codigo.startswith(modulo + "."):
                return True
            if codigo.startswith(modulo + "_"):
                return True
    return False
